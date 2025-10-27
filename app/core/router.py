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
        
        # Extract tags from top candidates
        all_tags = set()
        for candidate in candidates:
            all_tags.update(candidate.get("tags", []))
        
        # Extract context from query
        context = self._extract_context(query, file_path)
        
        # Determine flow type based on capability tags (order matters)
        if self._has_document_processing_intent(all_tags, file_path):
            return "flow_pdf_tracking", context
        elif self._has_visualization_intent(all_tags):
            return "flow_plot", context
        else:
            # Dynamic flow based on capabilities
            return "flow_dynamic", {"candidates": candidates, **context}
    
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