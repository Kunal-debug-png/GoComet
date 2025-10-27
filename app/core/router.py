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
        # Use capability index to find matching tools/agents
        candidates = self.search_capabilities(query, top_k=10)
        
        if not candidates:
            return "flow_custom", {}
        
        # Build context with capability metadata
        context = self._build_context(query, file_path, candidates)
        
        # Classify flow type based on candidates and query intent
        flow_type = self._classify_flow_from_candidates(candidates, query, file_path)
        
        # Add candidates to context for dynamic flows
        if flow_type == "flow_dynamic":
            context["candidates"] = candidates
        
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
        context = {}
        
        # Extract outlet number
        if "outlet" in query.lower():
            words = query.split()
            for i, word in enumerate(words):
                if word.lower() == "outlet" and i + 1 < len(words):
                    try:
                        context["outlet"] = int(words[i + 1])
                    except ValueError:
                        pass
        
        # Add file path if provided
        if file_path:
            context["file_path"] = file_path
        
        # Extract time periods
        if "week" in query.lower():
            context["time_period"] = "weekly"
        elif "month" in query.lower():
            context["time_period"] = "monthly"
        elif "day" in query.lower():
            context["time_period"] = "daily"
        
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