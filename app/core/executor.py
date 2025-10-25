import asyncio
import hashlib
import json
import time
import base64
import re
from datetime import datetime
from typing import Dict, Any, Optional
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
            
            # Skip cache for now to avoid cross-run artifact issues
            # TODO: Implement proper cache with run_id isolation
            
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
        
        # Simple heuristic: first column as x, second as y
        x_col = cols[0] if len(cols) > 0 else "x"
        y_col = cols[1] if len(cols) > 1 else "y"
        
        return {
            "type": "plotspec",
            "grammar": "plotly",
            "encoding": {
                "x": x_col,
                "y": y_col,
                "mark": "line"
            },
            "data": rows,
            "title": f"{y_col} over {x_col}"
        }
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
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
        """Extract tables from PDF content"""
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
        """Parse invoice data from extracted text and tables"""
        result = {
            "invoice_number": "Not found",
            "date": "Not found",
            "total_amount": None,
            "vendor": "Not found",
            "line_items": [],
            "raw_text": text[:1000] + "..." if len(text) > 1000 else text
        }
        
        # Simple pattern matching for common invoice fields
        # Look for invoice number patterns
        invoice_num_match = re.search(r'(?:invoice|bill)[^\d]*(\d{4,})', text, re.IGNORECASE)
        if invoice_num_match:
            result["invoice_number"] = f"INV-{invoice_num_match.group(1)}"
        
        # Look for date patterns
        date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # MM/DD/YYYY or DD/MM/YYYY
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'     # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, text)
            if date_match:
                try:
                    date_str = date_match.group(1)
                    # Try to parse the date to ensure it's valid
                    datetime.strptime(date_str, '%Y-%m-%d')
                    result["date"] = date_str
                    break
                except (ValueError, AttributeError):
                    continue
        
        # Look for total amount
        total_matches = re.findall(r'total.*?\$?\s*(\d{1,3}(?:[,\.]\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
        if total_matches:
            try:
                amount_str = total_matches[-1].replace(',', '')
                result["total_amount"] = float(amount_str)
            except (ValueError, IndexError):
                pass
        
        # Look for vendor name
        vendor_matches = re.search(r'(?:from|vendor|supplier)[:;\s]+([A-Z][a-zA-Z\s\.&,]+(?:Inc|Ltd|LLC|GmbH|Pvt|LLP|Corp|Company)?\b)', text, re.IGNORECASE)
        if vendor_matches:
            result["vendor"] = vendor_matches.group(1).strip()
        
        # Process tables to find line items
        for table in tables:
            if len(table) > 1:  # At least header + one row
                headers = [str(cell or '').lower().strip() for cell in table[0]]
                
                # Try to identify columns of interest
                item_col = next((i for i, h in enumerate(headers) 
                               if any(term in h for term in ['item', 'description'])), -1)
                qty_col = next((i for i, h in enumerate(headers) 
                              if 'qty' in h or 'quantity' in h), -1)
                price_col = next((i for i, h in enumerate(headers) 
                                if 'price' in h and 'total' not in h), -1)
                total_col = next((i for i, h in enumerate(headers) 
                                if 'total' in h and 'price' not in h), -1)
                
                # If we found relevant columns, extract line items
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
                    
                    # If we found line items, no need to process more tables
                    if result["line_items"]:
                        break
        
        return result
    
    def _extraction_agent(self, inputs: Dict) -> Dict:
        """Extract structured data from PDF content"""
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
            
            # Extract text and tables from PDF
            text = self._extract_text_from_pdf(pdf_content)
            tables = self._extract_tables_from_pdf(pdf_content)
            
            # Parse the extracted data
            result = self._parse_invoice_data(text, tables)
            
            # Add metadata
            result.update({
                "extraction_status": "success",
                "pages_processed": len(text.split("\f")),
                "tables_found": len(tables),
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
        elif isinstance(result, dict) and "rows" in result:
            format = "json"
        else:
            format = "json"
        
        return self.artifacts.write(run_id, node_id, result, format=format)