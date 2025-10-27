"""MCP stdio client - communicates with MCP servers via stdin/stdout"""
import json
import subprocess
import sys
from typing import Dict, Any, Optional
from pathlib import Path


class MCPStdioClient:
    """Client for communicating with MCP servers via stdio"""
    
    def __init__(self, server_script: str):
        """
        Initialize client for a specific server script
        
        Args:
            server_script: Path to the server script (e.g., 'srv_sql.py')
        """
        self.server_script = Path(server_script)
        if not self.server_script.exists():
            raise FileNotFoundError(f"Server script not found: {server_script}")
        
        self._request_id = 0
    
    def _get_next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    def call_tool(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server
        
        Args:
            method: Tool method name (e.g., 'sql.query')
            params: Tool parameters
            
        Returns:
            Tool result
            
        Raises:
            Exception: If the tool call fails
        """
        request_id = self._get_next_id()
        
        # Build JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        # Start server process
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.server_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send request
            stdout, stderr = process.communicate(
                input=json.dumps(request) + "\n",
                timeout=30
            )
            
            # Parse response
            if not stdout.strip():
                raise Exception(f"No response from server: {self.server_script}")
            
            response = json.loads(stdout.strip())
            
            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise Exception(f"Server error: {error.get('message', 'Unknown error')}")
            
            # Return result
            return response.get("result")
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception(f"Server timeout: {self.server_script}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from server: {e}")
        except Exception as e:
            raise Exception(f"Failed to call tool {method}: {str(e)}")
    
    def get_manifest(self) -> Dict:
        """
        Get server manifest
        
        Returns:
            Server manifest with tool definitions
        """
        try:
            process = subprocess.Popen(
                [sys.executable, str(self.server_script), "--manifest"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=5)
            
            if not stdout.strip():
                raise Exception(f"No manifest from server: {self.server_script}")
            
            return json.loads(stdout.strip())
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception(f"Manifest timeout: {self.server_script}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid manifest JSON: {e}")
        except Exception as e:
            raise Exception(f"Failed to get manifest: {str(e)}")
