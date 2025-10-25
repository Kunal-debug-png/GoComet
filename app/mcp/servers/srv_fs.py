"""FileSystem Server - File operations"""
from pathlib import Path
import base64

class FileSystemServer:
    def file_read(self, path: str) -> dict:
        """Read file and return base64-encoded bytes"""
        try:
            # Handle relative paths
            if path.startswith('./'):
                path = path[2:]  # Remove './' prefix
            
            filepath = Path(path)
            if not filepath.exists():
                # Try with absolute path from project root
                filepath = Path(__file__).parent.parent.parent / path
                if not filepath.exists():
                    return {"error": f"File not found: {path}"}
            
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # ✅ Base64 encode for JSON serialization
            return {
                "bytes_base64": base64.b64encode(data).decode('utf-8'),
                "size": len(data),
                "path": str(filepath),
                "format": filepath.suffix[1:]  # e.g., "pdf"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def manifest(self) -> dict:
        return {
            "server": "srv_fs",
            "tools": [{
                "name": "file.read",
                "description": "Read file from disk",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }]
        }