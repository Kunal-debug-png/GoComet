import json
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

class ArtifactManager:
    def __init__(self, base_path: str = "./artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def write(self, run_id: str, node_id: str, data: Any, 
              format: str = "json", filename: str = "output") -> str:
        """Write artifact to disk and return URI"""
        node_dir = self.base_path / run_id / node_id
        node_dir.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            filepath = node_dir / f"{filename}.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
        
        elif format == "parquet":
            filepath = node_dir / f"{filename}.parquet"
            if isinstance(data, pd.DataFrame):
                data.to_parquet(filepath, index=False)
            else:
                raise ValueError("Parquet format requires DataFrame")
        
        elif format == "csv":
            filepath = node_dir / f"{filename}.csv"
            if isinstance(data, pd.DataFrame):
                data.to_csv(filepath, index=False)
            else:
                raise ValueError("CSV format requires DataFrame")
        
        elif format == "png":
            filepath = node_dir / f"{filename}.png"
            with open(filepath, 'wb') as f:
                f.write(data)
        
        elif format == "pdf":
            filepath = node_dir / f"{filename}.pdf"
            with open(filepath, 'wb') as f:
                f.write(data)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Return URI
        return f"artifact://{node_id}/{filename}.{format}"
    
    def read(self, uri: str, run_id: str) -> Any:
        """Read artifact from URI"""
        # Parse URI: artifact://node_id/filename.ext
        parts = uri.replace("artifact://", "").split("/")
        node_id = parts[0]
        filename = parts[1]
        
        filepath = self.base_path / run_id / node_id / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Artifact not found: {uri}")
        
        ext = filepath.suffix[1:]  # Remove dot
        
        if ext == "json":
            with open(filepath, 'r') as f:
                return json.load(f)
        elif ext == "parquet":
            return pd.read_parquet(filepath)
        elif ext == "csv":
            return pd.read_csv(filepath)
        elif ext in ["png", "pdf"]:
            with open(filepath, 'rb') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported format: {ext}")
    
    def compute_hash(self, data: Any) -> str:
        """Compute SHA256 hash of data"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, pd.DataFrame):
            data_str = data.to_json()
        else:
            data_str = str(data)
        
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def get_artifact_path(self, run_id: str, node_id: str) -> Path:
        """Get directory path for node artifacts"""
        return self.base_path / run_id / node_id