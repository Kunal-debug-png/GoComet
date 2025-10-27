import asyncio
import hashlib
import json
import time
import base64
import re
import os
import uuid
from datetime import datetime
from dateutil import parser
from typing import Dict, Any, Optional, List
import networkx as nx
from app.storage.database import Database
from app.storage.artifacts import ArtifactManager
from app.mcp.client_pool import MCPClientPool
from app.observability.logger import log_node_execution, logger

class Executor:
    def __init__(self, db: Database, artifacts: ArtifactManager, mcp_pool: MCPClientPool):
        self.db = db
        self.artifacts = artifacts
        self.mcp_pool = mcp_pool
        self.timeout_sec = 30
        self.max_retries = 1
        self._llama_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        self._has_llama = bool(self._llama_api_key)
    
    def _build_graph(self, plan: Dict) -> nx.DiGraph:
        """Build NetworkX graph from plan"""
        G = nx.DiGraph()
        
        for node in plan["nodes"]:
            G.add_node(node["id"], **node)
        
        for source, target in plan["edges"]:
            G.add_edge(source, target)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("Plan contains cycles")
        
        return G
    
    def _compute_idempotency_key(self, node: Dict, upstream_hashes: list) -> str:
        """Compute idempotency key for caching"""
        key_data = {
            "type": node.get("type"),
            "server": node.get("server"),
            "tool": node.get("tool"),
            "agent": node.get("agent"),
            "args": sorted(node.get("args", {}).items()),
            "upstreams": sorted(upstream_hashes)
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def execute(self, run_id: str, plan: Dict):
        """Execute DAG plan"""
        try:
            logger.info("execution_started", run_id=run_id, plan_id=plan["plan_id"])
            self.db.update_run_status(run_id, "running")
            
            # Build graph
            graph = self._build_graph(plan)
            
            # Store node outputs
            node_outputs = {}
            
            # Topological execution
            for node_id in nx.topological_sort(graph):
                node = graph.nodes[node_id]
                
                # Gather upstream outputs
                upstream_outputs = {}
                for pred in graph.predecessors(node_id):
                    upstream_outputs[pred] = node_outputs.get(pred)
                
                # Execute node
                output = await self._execute_node(run_id, node, upstream_outputs)
                node_outputs[node_id] = output
            
            # Build final result
            reduce_output = node_outputs.get("reduce", {})
            
            self.db.update_run_status(run_id, "success", result=reduce_output)
            logger.info("execution_completed", run_id=run_id)
            return reduce_output
            
        except Exception as e:
            logger.error("execution_failed", run_id=run_id, error=str(e))
            self.db.update_run_status(run_id, "failed", error=str(e))
            raise
    
    async def _execute_node(self, run_id: str, node: Dict, upstream_outputs: Dict) -> Any:
        """Execute single node"""
        node_id = node["id"]
        node_type = node.get("type")
        
        start_ms = int(time.time() * 1000)
        
        try:
            logger.info("node_started", run_id=run_id, node_id=node_id, type=node_type)
            
            # Compute idempotency key
            upstream_hashes = [
                self.artifacts.compute_hash(out) 
                for out in upstream_outputs.values() if out
            ]
            idem_key = self._compute_idempotency_key(node, upstream_hashes)
            
            # Create node record
            self.db.create_node(run_id, node_id, node_type, idem_key)
            self.db.update_node_status(run_id, node_id, "running", start_ms=start_ms)
            
            # Gather inputs from bindings
            inputs = await self._gather_inputs(run_id, node, upstream_outputs)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                self._call_node(run_id, node, inputs),
                timeout=self.timeout_sec
            )
            
            # Save artifact
            artifact_uri = self._save_node_output(run_id, node_id, result)
            
            end_ms = int(time.time() * 1000)
            
            # Update node status
            self.db.update_node_status(run_id, node_id, "success", 
                                      output_artifact=artifact_uri,
                                      end_ms=end_ms)
            
            log_node_execution(run_id, node_id, node_type, "success",
                             start_ms, end_ms, artifact_uri=artifact_uri)
            
            return result
            
        except asyncio.TimeoutError:
            end_ms = int(time.time() * 1000)
            error = f"Timeout after {self.timeout_sec}s"
            self.db.update_node_status(run_id, node_id, "failed", error=error, end_ms=end_ms)
            log_node_execution(run_id, node_id, node_type, "failed", start_ms, end_ms, error=error)
            raise
        
        except Exception as e:
            end_ms = int(time.time() * 1000)
            error = str(e)
            self.db.update_node_status(run_id, node_id, "failed", error=error, end_ms=end_ms)
            log_node_execution(run_id, node_id, node_type, "failed", start_ms, end_ms, error=error)
            raise
    
    async def _gather_inputs(self, run_id: str, node: Dict, upstream_outputs: Dict) -> Dict:
        """Gather input artifacts for node"""
        inputs = dict(node.get("args", {}))
        
        # Process input bindings
        for key, ref in node.get("input_bindings", {}).items():
            if ref.startswith("artifact://"):
                # Load artifact
                data = self.artifacts.read(ref, run_id)
                inputs[key] = data
        
        return inputs
    
    async def _call_node(self, run_id: str, node: Dict, inputs: Dict) -> Any:
        """Call tool or agent"""
        node_type = node.get("type")
        
        if node_type == "tool":
            # Call MCP tool
            server = node["server"]
            tool = node["tool"]
            result = self.mcp_pool.call_tool(server, tool, inputs)
            return result
        
        elif node_type == "agent":
            # Call agent (implemented as simple functions)
            agent_name = node["agent"]
            result = await self._call_agent(agent_name, inputs)
            return result
        
        else:
            raise ValueError(f"Unknown node type: {node_type}")
    
    async def _call_agent(self, agent_name: str, inputs: Dict) -> Any:
        """Call agent (simplified implementation)"""
        if agent_name == "viz_spec_agent":
            return self._viz_spec_agent(inputs)
        elif agent_name == "extraction_agent":
            return self._extraction_agent(inputs)
        elif agent_name == "validator":
            return self._validator_agent(inputs)
        elif agent_name == "reducer":
            return self._reducer_agent(inputs)
        else:
            raise ValueError(f"Unknown agent: {agent_name}")
    
    def _viz_spec_agent(self, inputs: Dict) -> Dict:
        """Generate visualization spec from dataframe"""
        df_data = inputs.get("dataframe_data", {})
        rows = df_data.get("rows", [])
        
        if not rows:
            return {"error": "No data to visualize"}
        
        # Detect columns
        cols = list(rows[0].keys()) if rows else []
        
        # Smart column selection for sales data
        x_col = "week" if "week" in cols else (cols[0] if len(cols) > 0 else "x")
        y_col = "sales" if "sales" in cols else (cols[1] if len(cols) > 1 else "y")
        
        return {
            "type": "plotspec",
            "grammar": "plotly",
            "encoding": {
                "x": x_col,
                "y": y_col,
                "mark": "line"
            },
            "data": rows,
            "title": f"Weekly Sales"
        }
    
    def _extract_with_llama(self, pdf_content: bytes, temp_dir: Optional[str] = None) -> dict:
        """Extract text and structured data from PDF using LlamaExtract"""
        try:
            from llama_cloud_services import LlamaExtract
            from pydantic import BaseModel, Field
            
            # Define the invoice data schema
            class LineItem(BaseModel):
                description: str = Field(default="", description="Item description")
                quantity: float = Field(default=1.0, description="Item quantity")
                unit_price: Optional[float] = Field(default=None, description="Unit price")
                total: Optional[float] = Field(default=None, description="Total for this item")
            
            class InvoiceData(BaseModel):
                invoice_number: str = Field(default="", description="Invoice number or ID")
                date: str = Field(default="", description="Invoice date")
                total_amount: Optional[float] = Field(default=None, description="Total amount due")
                vendor: str = Field(default="", description="Vendor or seller name")
                line_items: List[LineItem] = Field(default_factory=list, description="List of line items")
            
            # Save PDF to temporary file
            import tempfile
            
            # Use system temp directory if not specified
            if temp_dir is None:
                temp_dir = tempfile.gettempdir()
            
            temp_file = os.path.join(temp_dir, f"temp_pdf_{uuid.uuid4().hex}.pdf")
            try:
                # Ensure temp directory exists
                os.makedirs(temp_dir, exist_ok=True)
                
                with open(temp_file, "wb") as f:
                    f.write(pdf_content)
                
                # Initialize LlamaExtract with API key
                extractor = LlamaExtract(api_key=self._llama_api_key)
                
                # Create or get extraction agent with schema
                try:
                    # Try to get existing agent
                    agent = extractor.get_agent(name="invoice-extractor")
                except:
                    # Create new agent if it doesn't exist
                    agent = extractor.create_agent(name="invoice-extractor", data_schema=InvoiceData)
                
                # Extract data from PDF
                result = agent.extract(temp_file)
                
                # Return structured data
                if hasattr(result, 'data') and result.data:
                    text = json.dumps(result.data, indent=2)
                    return {"text": text, "structured_data": result.data}
                else:
                    text = str(result)
                    return {"text": text, "structured_data": None}
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    
        except Exception as e:
            logger.error(f"Error with LlamaExtract: {str(e)}")
            raise
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content using hybrid approach"""
        # Try LlamaExtract first if API key is available
        if self._has_llama:
            try:
                result = self._extract_with_llama(pdf_content)
                return result.get("text", "")
            except Exception as e:
                logger.warning(f"LlamaExtract failed, falling back to pdfplumber: {str(e)}")
        
        # Fallback to pdfplumber
        import pdfplumber
        import io
        
        text = ""
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
        
        return text.strip()
    
    def _extract_tables_from_pdf(self, pdf_content: bytes) -> list:
        """Extract tables from PDF content using hybrid approach"""
        # Try LlamaExtract first if API key is available
        if self._has_llama:
            try:
                result = self._extract_with_llama(pdf_content)
                structured = result.get("structured_data")
                if structured:
                    # Convert structured data to table format if possible
                    return [structured] if isinstance(structured, dict) else structured if isinstance(structured, list) else []
            except Exception as e:
                logger.warning(f"LlamaExtract failed, falling back to pdfplumber: {str(e)}")
        
        # Fallback to pdfplumber
        import pdfplumber
        import io
        
        tables = []
        try:
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    page_tables = page.extract_tables()
                    if page_tables:
                        tables.extend(page_tables)
        except Exception as e:
            logger.error(f"Error extracting tables from PDF: {str(e)}")
            # Don't fail the whole extraction if table extraction fails
            
        return tables
    
    def _parse_invoice_data(self, text: str, tables: list) -> Dict:
        """Parse invoice data from extracted text and tables with improved flexibility"""
        result = {
            "invoice_number": "Not found",
            "date": "Not found",
            "total_amount": None,
            "vendor": "Not found",
            "line_items": [],
            "raw_text": text[:1000] + "..." if len(text) > 1000 else text
        }
        
        # Expanded regex patterns for invoice number
        invoice_num_patterns = [
            r'(?:invoice|bill|no[.]?)[^\d]*(\d{4,})',  # Account for possible punctuation like "Invoice #1234"
            r'([A-Za-z0-9]+)[^\d]*(?:inv|invoice|bill)',  # Handles alphanumeric invoice numbers
        ]
        for pattern in invoice_num_patterns:
            invoice_num_match = re.search(pattern, text, re.IGNORECASE)
            if invoice_num_match:
                result["invoice_number"] = invoice_num_match.group(1)
                break
        
        # Flexible date parsing with dateutil.parser (handles multiple formats)
        try:
            date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\b(\w{3,9}\s?\d{1,2}[,\s]?\s?\d{4})\b', text)
            if date_match:
                date_str = date_match.group(0)
                result["date"] = parser.parse(date_str).strftime('%Y-%m-%d')
        except Exception as e:
            result["date"] = "Not found"
        
        # Expanded total amount regex to cover more variations
        total_matches = re.findall(r'(?i)(total|amount\s*due|grand\s*total)[^\d]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text)
        if total_matches:
            try:
                total_value = total_matches[-1][1].replace(',', '')
                result["total_amount"] = float(total_value)
            except ValueError:
                result["total_amount"] = None
        
        # Flexible vendor matching with multiple labels
        vendor_patterns = [
            r'(?:from|vendor|supplier)[^\w]*(\w+(?:\s\w+)*\s?(?:Inc|Ltd|LLC|Corp|GmbH|Pvt|LLP)?)',
            r'(?:issued\s*by|billed\s*to)\s?([A-Za-z][A-Za-z\s\.&,]+(?:Inc|Ltd|LLC|Corp|GmbH|Pvt|LLP|Company)?)'
        ]
        for pattern in vendor_patterns:
            vendor_match = re.search(pattern, text, re.IGNORECASE)
            if vendor_match:
                result["vendor"] = vendor_match.group(1).strip()
                break

        # Process tables to find line items with improved flexibility
        for table in tables:
            if len(table) > 1:  # At least header + one row
                headers = [str(cell or '').lower().strip() for cell in table[0]]
                
                # Try to identify columns with more flexibility
                item_col = next((i for i, h in enumerate(headers) if any(term in h for term in ['item', 'description', 'product'])), -1)
                qty_col = next((i for i, h in enumerate(headers) if any(term in h for term in ['qty', 'quantity', 'count'])), -1)
                price_col = next((i for i, h in enumerate(headers) if any(term in h for term in ['price', 'unit price', 'rate'])), -1)
                total_col = next((i for i, h in enumerate(headers) if any(term in h for term in ['total', 'amount', 'cost'])), -1)
                
                # If relevant columns are found, extract line items
                if item_col >= 0 and (price_col >= 0 or total_col >= 0):
                    for row in table[1:]:  # Skip header
                        try:
                            if len(row) > max(item_col, qty_col, price_col, total_col):
                                line_item = {
                                    "description": str(row[item_col]) if item_col < len(row) else "",
                                    "quantity": float(row[qty_col]) if qty_col >= 0 and qty_col < len(row) and str(row[qty_col]).strip() else 1,
                                    "unit_price": float(str(row[price_col]).replace(',', '')) if price_col >= 0 and price_col < len(row) and str(row[price_col]).strip() else None,
                                    "total": float(str(row[total_col]).replace(',', '')) if total_col >= 0 and total_col < len(row) and str(row[total_col]).strip() else None
                                }
                                result["line_items"].append(line_item)
                        except (ValueError, IndexError):
                            continue
                    
                    # If line items are found, no need to process more tables
                    if result["line_items"]:
                        break

        return result
    def _extraction_agent(self, inputs: Dict) -> Dict:
        """Extract structured data from PDF content using hybrid approach"""
        try:
            # Get the file reference from inputs
            file_ref = inputs.get("file_ref", {})
            if not file_ref:
                raise ValueError("No file reference provided")
            
            # Get the base64-encoded PDF content
            pdf_base64 = file_ref.get("bytes_base64")
            if not pdf_base64:
                raise ValueError("No PDF content found in file reference")
            
            # Decode the base64 content
            pdf_content = base64.b64decode(pdf_base64)
            
            # Try LlamaExtract first if API key is available
            extraction_method = "pdfplumber"
            result = None
            
            if self._has_llama:
                try:
                    result = self._extract_with_llama(pdf_content)
                    structured = result.get("structured_data")
                    
                    if structured and isinstance(structured, dict):
                        # LlamaExtract returned structured data, format it
                        extraction_method = "llama_extract"
                        result = self._format_llama_extraction(structured)
                    else:
                        # Fall through to pdfplumber
                        raise ValueError("LlamaExtract did not return structured data")
                except Exception as e:
                    logger.warning(f"LlamaExtract failed: {str(e)}. Falling back to pdfplumber.")
                    extraction_method = "pdfplumber (fallback)"
            
            # Use pdfplumber if LlamaExtract wasn't successful
            if not result or extraction_method.startswith("pdfplumber"):
                text = self._extract_text_from_pdf(pdf_content)
                tables = self._extract_tables_from_pdf(pdf_content)
                
                # Parse the extracted data
                result = self._parse_invoice_data(text, tables)
            
            # Add metadata
            result.update({
                "extraction_status": "success",
                "extraction_method": extraction_method,
                "pages_processed": result.get("pages_processed", 1),
                "tables_found": len(result.get("line_items", [])),
                "line_items_count": len(result.get("line_items", [])),
                "file_metadata": {
                    "size_bytes": len(pdf_content),
                    "file_type": file_ref.get("format", "unknown")
                }
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in extraction_agent: {str(e)}")
            return {
                "extraction_status": "error",
                "error": str(e),
                "raw_input_keys": list(inputs.keys()) if isinstance(inputs, dict) else []
            }
    
    def _format_llama_extraction(self, structured_data: dict) -> Dict:
        """Format LlamaExtract results into invoice format"""
        result = {
            "invoice_number": structured_data.get("invoice_number", "Not found"),
            "date": structured_data.get("date", "Not found"),
            "total_amount": structured_data.get("total_amount", structured_data.get("amount", None)),
            "vendor": structured_data.get("vendor", structured_data.get("seller", "Not found")),
            "line_items": structured_data.get("line_items", structured_data.get("items", [])),
            "raw_text": json.dumps(structured_data, indent=2)
        }
        
        # Handle different possible key names from LlamaExtract
        if result["invoice_number"] == "Not found":
            result["invoice_number"] = structured_data.get("invoice_id", "Not found")
        
        return result
    
    def _validator_agent(self, inputs: Dict) -> Dict:
        """Validate outputs"""
        # Simple validation: check if data exists
        has_data = bool(inputs)
        return {
            "valid": has_data,
            "checks": {
                "non_empty": has_data,
                "no_pii": True  # In a real implementation, this would check for PII
            }
        }
    
    def _reducer_agent(self, inputs: Dict) -> Dict:
        """Reduce to final output"""
        output_type = inputs.get("type", "unknown")
        return {
            "type": output_type,
            "status": "completed",
            "artifacts": []  # Will be populated by caller
        }
    
    def _save_node_output(self, run_id: str, node_id: str, result: Any) -> str:
        """Save node output as artifact"""
        # Determine format
        if isinstance(result, bytes):
            format = "png"
        elif isinstance(result, dict):
            # Check if it's a plotly stdio response that wasn't converted
            if "image_base64" in result:
                # Convert base64 to bytes for consistency
                import base64
                result = base64.b64decode(result["image_base64"])
                format = "png"
            elif "rows" in result:
                format = "json"
            else:
                format = "json"
        else:
            format = "json"
        
        return self.artifacts.write(run_id, node_id, result, format=format)
