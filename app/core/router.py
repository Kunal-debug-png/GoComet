import json
from pathlib import Path
from typing import Dict, Tuple

class Router:
    def __init__(self, capability_index_path: str = "./config/capability_index.json"):
        self.index = self._load_index(capability_index_path)
    
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
        Classify query and return flow type
        Returns: (flow_type, context)
        """
        query_lower = query.lower()
        
        # Flow 1: Plot/Chart/Visualization
        if any(kw in query_lower for kw in ["plot", "chart", "visualize", "graph"]):
            # Extract outlet number if present
            outlet = None
            if "outlet" in query_lower:
                words = query.split()
                for i, word in enumerate(words):
                    if word.lower() == "outlet" and i + 1 < len(words):
                        try:
                            outlet = int(words[i + 1])
                        except ValueError:
                            pass
            
            return "flow_plot", {"outlet": outlet}
        
        # Flow 2: PDF + Tracking
        elif file_path and any(kw in query_lower for kw in ["upload", "invoice", "tracking", "update"]):
            return "flow_pdf_tracking", {"file_path": file_path}
        
        # Default to search-based routing
        else:
            return "flow_custom", {}
    
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