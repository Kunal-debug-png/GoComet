"""MCP Protocol - JSON-RPC 2.0 implementation for stdio communication"""
import json
import sys
import os
from typing import Dict, Any, Optional


class MCPProtocol:
    """Handle MCP JSON-RPC 2.0 protocol"""
    
    @staticmethod
    def setup_stdio_mode():
        """Setup stdio mode - redirect all print statements to stderr"""
        # Save original stdout
        original_stdout = sys.stdout
        
        # Redirect stdout to stderr for debug prints
        # This ensures only JSON-RPC responses go to stdout
        sys.stdout = sys.stderr
        
        return original_stdout
    
    @staticmethod
    def read_request() -> Optional[Dict]:
        """Read JSON-RPC request from stdin"""
        try:
            line = sys.stdin.readline()
            if not line:
                return None
            return json.loads(line.strip())
        except json.JSONDecodeError as e:
            MCPProtocol.write_error(None, -32700, f"Parse error: {str(e)}")
            return None
        except Exception as e:
            MCPProtocol.write_error(None, -32603, f"Internal error: {str(e)}")
            return None
    
    @staticmethod
    def write_response(request_id: Any, result: Any, stdout_handle=None):
        """Write JSON-RPC success response to stdout"""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        # Use provided stdout handle or get the real stdout
        out = stdout_handle if stdout_handle else sys.__stdout__
        out.write(json.dumps(response) + "\n")
        out.flush()
    
    @staticmethod
    def write_error(request_id: Any, code: int, message: str, data: Any = None, stdout_handle=None):
        """Write JSON-RPC error response to stdout"""
        error = {
            "code": code,
            "message": message
        }
        if data is not None:
            error["data"] = data
        
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
        # Use provided stdout handle or get the real stdout
        out = stdout_handle if stdout_handle else sys.__stdout__
        out.write(json.dumps(response) + "\n")
        out.flush()
    
    @staticmethod
    def write_manifest(manifest: Dict):
        """Write manifest to stdout (for --manifest flag)"""
        # For manifest, use real stdout directly
        sys.__stdout__.write(json.dumps(manifest, indent=2) + "\n")
        sys.__stdout__.flush()
