import json
from pathlib import Path
from typing import Dict, Tuple
from app.config import Config

class Router:
    def __init__(self, capability_index_path: str = None):
        self.index = self._load_index(capability_index_path or Config.CAPABILITY_INDEX_PATH)
    
    def _load_index(self, path: str) -> Dict:
        """Load capability index"""
        index_path = Path(path)
        if index_path.exists():
            with open(index_path, 'r') as f:
                return json.load(f)
        
        # Default index if file doesn't exist
        return {
            "capabilities": [
                {
                    "id": "sql",
                    "type": "tool",
                    "server": "srv_sql",
                    "tool": "sql.query",
                    "tags": ["data", "query", "sql", "sales"],
                    "description": "Execute SQL queries on CSV data"
                },
                {
                    "id": "pandas",
                    "type": "tool",
                    "server": "srv_pandas",
                    "tool": "dataframe.transform",
                    "tags": ["transform", "dataframe", "rolling"],
                    "description": "Transform dataframes"
                },
                {
                    "id": "plotly",
                    "type": "tool",
                    "server": "srv_plotly",
                    "tool": "plotly.render",
                    "tags": ["plot", "chart", "visualization"],
                    "description": "Render charts"
                },
                {
                    "id": "filesystem",
                    "type": "tool",
                    "server": "srv_fs",
                    "tool": "file.read",
                    "tags": ["file", "read", "pdf", "upload"],
                    "description": "Read files"
                },
                {
                    "id": "tracking",
                    "type": "tool",
                    "server": "srv_tracking",
                    "tool": "tracking.upsert",
                    "tags": ["tracking", "update", "invoice"],
                    "description": "Update tracking records"
                }
            ]
        }
    
    def route(self, query: str, file_path: str = None) -> Tuple[str, Dict]:
        """
        Classify query using capability index and return flow type
        Returns: (flow_type, context)
        """
        print(f"[ROUTER] Input - Query: '{query}', File: {file_path}")
        
        # Use capability index to find matching tools/agents
        candidates = self.search_capabilities(query, top_k=10)
        print(f"[ROUTER] Found {len(candidates)} candidates: {[c['id'] for c in candidates[:3]]}")
        
        if not candidates:
            print("[ROUTER] No candidates found, returning flow_custom")
            return "flow_custom", {}
        
        # Extract context from query
        context = self._extract_context(query, file_path)
        print(f"[ROUTER] Extracted context: {context}")
        
        # Classify flow type based on candidates and query intent
        flow_type = self._classify_flow_from_candidates(candidates, query, file_path)
        print(f"[ROUTER] Classified as flow_type: {flow_type}")
        
        # Add candidates to context for dynamic flows
        if flow_type == "flow_dynamic":
            context["candidates"] = candidates
        
        print(f"[ROUTER] Final result - Flow: {flow_type}, Context: {context}")
        return flow_type, context
    
    def _classify_flow_from_candidates(self, candidates: list, query: str, file_path: str = None) -> str:
        """
        Classify flow type based on capability candidates and query analysis
        """
        query_lower = query.lower()
        
        # Strong indicators for specific flows
        viz_keywords = ["plot", "chart", "graph", "visualiz", "render", "show", "display"]
        doc_keywords = ["pdf", "document", "invoice", "extract", "upload", "file", "process"]
        
        # Check for explicit visualization intent in query
        has_viz_keyword = any(keyword in query_lower for keyword in viz_keywords)
        
        # Check for explicit document processing intent in query  
        has_doc_keyword = any(keyword in query_lower for keyword in doc_keywords)
        
        # Analyze candidate capabilities
        candidate_types = {"viz": 0, "data": 0, "doc": 0, "file": 0}
        
        for candidate in candidates[:5]:  # Top 5 candidates
            tags = set(candidate.get("tags", []))
            
            # Count visualization capabilities
            if tags.intersection({"plot", "chart", "visualization", "render"}):
                candidate_types["viz"] += 2
            
            # Count data processing capabilities  
            if tags.intersection({"sql", "data", "query", "dataframe", "transform"}):
                candidate_types["data"] += 2
                
            # Count document processing capabilities
            if tags.intersection({"extract", "parse", "pdf", "invoice"}):
                candidate_types["doc"] += 2
                
            # Count file operations
            if tags.intersection({"file", "read", "upload"}):
                candidate_types["file"] += 1
        
        # Decision logic with priority
        
        # 1. File provided + document keywords = PDF tracking flow
        if file_path and (has_doc_keyword or candidate_types["doc"] > 0):
            return "flow_pdf_tracking"
            
        # 2. Strong visualization intent = plot flow
        if has_viz_keyword and (candidate_types["viz"] > 0 or candidate_types["data"] > 0):
            return "flow_plot"
            
        # 3. Document processing without file = still PDF tracking (might be general doc processing)
        if has_doc_keyword and candidate_types["doc"] >= candidate_types["viz"]:
            return "flow_pdf_tracking"
            
        # 4. Data + visualization capabilities = plot flow
        if candidate_types["viz"] > 0 and candidate_types["data"] > 0:
            return "flow_plot"
            
        # 5. Strong document processing intent (keyword + capabilities)
        if has_doc_keyword and candidate_types["doc"] > 0:
            return "flow_pdf_tracking"
            
        # 6. File provided with any document capabilities
        if file_path and candidate_types["doc"] > 0:
            return "flow_pdf_tracking"
            
        # 7. Default to dynamic flow for ambiguous cases
        return "flow_dynamic"

    def _has_visualization_intent(self, tags: set) -> bool:
        """Check if tags indicate visualization intent"""
        viz_tags = {"plot", "chart", "visualization", "render", "image"}
        data_tags = {"sql", "data", "sales", "orders"}
        
        # Need both visualization AND data tags for plot flow
        return bool(viz_tags.intersection(tags)) and bool(data_tags.intersection(tags))
    
    def _has_document_processing_intent(self, tags: set, file_path: str) -> bool:
        """Check if tags indicate document processing intent"""
        doc_tags = {"pdf", "extract", "document", "invoice"}
        file_tags = {"file", "upload"}
        
        # Filter out placeholder file paths
        if file_path in ["string", "", None]:
            file_path = None
        
        # Strong document processing intent: file provided AND doc tags, OR multiple doc tags
        return (file_path is not None and bool(doc_tags.intersection(tags))) or \
               (bool(file_tags.intersection(tags)) and bool(doc_tags.intersection(tags)))
    
    def _build_context(self, query: str, file_path: str = None, candidates: list = None) -> Dict:
        """Build context information from query, file path, and capability candidates"""
        context = self._extract_context(query, file_path)
        
        # Add capability metadata to context
        if candidates:
            context["capability_metadata"] = {
                "total_candidates": len(candidates),
                "top_capabilities": [c["id"] for c in candidates[:3]],
                "capability_types": list(set(c.get("type", "unknown") for c in candidates))
            }
        
        return context
    
    def _extract_context(self, query: str, file_path: str = None) -> Dict:
        """Extract context information from query"""
        print(f"[ROUTER._extract_context] Starting context extraction")
        print(f"[ROUTER._extract_context] Query: '{query}'")
        print(f"[ROUTER._extract_context] File path: {file_path}")
        
        context = {}
        
        # Filter out placeholder file paths
        if file_path in ["string", "", None]:
            print(f"[ROUTER._extract_context] Ignoring placeholder file_path: '{file_path}'")
            file_path = None
        
        # Extract outlet number
        if "outlet" in query.lower():
            print(f"[ROUTER._extract_context] Found 'outlet' keyword in query")
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() == "outlet" and i + 1 < len(words):
                    try:
                        outlet_num = int(words[i + 1])
                        context["outlet"] = outlet_num
                        print(f"[ROUTER._extract_context] Extracted outlet: {outlet_num}")
                    except ValueError:
                        print(f"[ROUTER._extract_context] Failed to parse outlet number: {words[i + 1]}")
        
        # Add file path if provided
        if file_path:
            context["file_path"] = file_path
            print(f"[ROUTER._extract_context] Added file_path to context: {file_path}")
        
        # Extract time periods with specific counts
        import re
        query_lower = query.lower()
        
        # Look for patterns like "last 2 weeks", "past 4 weeks", "8 weeks"
        week_pattern = r'(?:last|past)?\s*(\d+)\s*weeks?'
        week_match = re.search(week_pattern, query_lower)
        
        if week_match:
            week_count = int(week_match.group(1))
            context["time_period"] = "weekly"
            context["week_count"] = week_count
            print(f"[ROUTER._extract_context] Extracted week_count: {week_count} from pattern match")
        elif "week" in query_lower:
            context["time_period"] = "weekly"
            print(f"[ROUTER._extract_context] Found 'week' keyword, set time_period='weekly'")
        elif "month" in query_lower:
            context["time_period"] = "monthly"
            print(f"[ROUTER._extract_context] Found 'month' keyword, set time_period='monthly'")
        elif "day" in query_lower:
            context["time_period"] = "daily"
            print(f"[ROUTER._extract_context] Found 'day' keyword, set time_period='daily'")
        
        print(f"[ROUTER._extract_context] Final context: {context}")
        return context
    
    def search_capabilities(self, query: str, top_k: int = 5) -> list:
        """Search capability index (simple keyword matching)"""
        query_lower = query.lower()
        scores = []
        
        for cap in self.index["capabilities"]:
            score = 0
            # Match against tags
            for tag in cap["tags"]:
                if tag in query_lower:
                    score += 2
            # Match against description
            if any(word in cap["description"].lower() for word in query_lower.split()):
                score += 1
            
            if score > 0:
                scores.append((score, cap))
        
        # Sort by score and return top k
        scores.sort(key=lambda x: x[0], reverse=True)
        return [cap for score, cap in scores[:top_k]]