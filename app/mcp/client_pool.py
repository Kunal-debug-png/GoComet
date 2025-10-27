import os
import base64
from typing import Dict, Any
from pathlib import Path
from app.mcp.servers.srv_sql import SQLServer
from app.mcp.servers.srv_pandas import PandasServer
from app.mcp.servers.srv_plotly import PlotlyServer
from app.mcp.servers.srv_fs import FileSystemServer
from app.mcp.servers.srv_tracking import TrackingServer
from app.mcp.stdio_client import MCPStdioClient


class MCPClientPool:
    def __init__(self, use_stdio: bool = None):
        """
        Initialize MCP client pool
        
        Args:
            use_stdio: If True, use stdio-based MCP servers. If False, use direct class instances.
                      If None, check environment variable MCP_USE_STDIO (defaults to False)
        """
        # Determine mode from environment or parameter
        if use_stdio is None:
            use_stdio = os.getenv("MCP_USE_STDIO", "false").lower() == "true"
        
        self.use_stdio = use_stdio
        
        if self.use_stdio:
            # Initialize stdio clients
            servers_dir = Path(__file__).parent / "servers"
            self.stdio_clients = {
                "srv_sql": MCPStdioClient(servers_dir / "srv_sql_stdio.py"),
                "srv_pandas": MCPStdioClient(servers_dir / "srv_pandas_stdio.py"),
                "srv_plotly": MCPStdioClient(servers_dir / "srv_plotly_stdio.py"),
                "srv_fs": MCPStdioClient(servers_dir / "srv_fs_stdio.py"),
                "srv_tracking": MCPStdioClient(servers_dir / "srv_tracking_stdio.py")
            }
            self.servers = None
        else:
            # Initialize direct server instances (legacy mode)
            self.servers = {
                "srv_sql": SQLServer(),
                "srv_pandas": PandasServer(),
                "srv_plotly": PlotlyServer(),
                "srv_fs": FileSystemServer(),
                "srv_tracking": TrackingServer()
            }
            self.stdio_clients = None
    
    def call_tool(self, server: str, tool: str, args: Dict[str, Any]) -> Any:
        """Call a tool on a specific server"""
        if self.use_stdio:
            return self._call_tool_stdio(server, tool, args)
        else:
            return self._call_tool_direct(server, tool, args)
    
    def _call_tool_direct(self, server: str, tool: str, args: Dict[str, Any]) -> Any:
        """Call tool using direct class instance (legacy mode)"""
        if server not in self.servers:
            raise ValueError(f"Unknown server: {server}")
        
        server_instance = self.servers[server]
        tool_method = tool.replace('.', '_')  # sql.query -> sql_query
        
        if not hasattr(server_instance, tool_method):
            raise ValueError(f"Tool {tool} not found on {server}")
        
        method = getattr(server_instance, tool_method)
        result = method(**args)
        
        # Handle plotly special case - convert bytes to expected format
        if server == "srv_plotly" and isinstance(result, bytes):
            # Keep as bytes for backward compatibility
            return result
        
        return result
    
    def _call_tool_stdio(self, server: str, tool: str, args: Dict[str, Any]) -> Any:
        """Call tool using stdio MCP client"""
        if server not in self.stdio_clients:
            raise ValueError(f"Unknown server: {server}")
        
        client = self.stdio_clients[server]
        result = client.call_tool(tool, args)
        
        # Handle plotly special case - convert base64 back to bytes
        if server == "srv_plotly" and isinstance(result, dict) and "image_base64" in result:
            return base64.b64decode(result["image_base64"])
        
        return result
    
    def get_manifest(self, server: str) -> Dict:
        """Get tool manifest for a server"""
        if self.use_stdio:
            if server not in self.stdio_clients:
                raise ValueError(f"Unknown server: {server}")
            return self.stdio_clients[server].get_manifest()
        else:
            if server not in self.servers:
                raise ValueError(f"Unknown server: {server}")
            return self.servers[server].manifest()