from typing import Dict, Any
from app.mcp.servers.srv_sql import SQLServer
from app.mcp.servers.srv_pandas import PandasServer
from app.mcp.servers.srv_plotly import PlotlyServer
from app.mcp.servers.srv_fs import FileSystemServer
from app.mcp.servers.srv_tracking import TrackingServer

class MCPClientPool:
    def __init__(self):
        # Initialize all servers
        self.servers = {
            "srv_sql": SQLServer(),
            "srv_pandas": PandasServer(),
            "srv_plotly": PlotlyServer(),
            "srv_fs": FileSystemServer(),
            "srv_tracking": TrackingServer()
        }
    
    def call_tool(self, server: str, tool: str, args: Dict[str, Any]) -> Any:
        """Call a tool on a specific server"""
        if server not in self.servers:
            raise ValueError(f"Unknown server: {server}")
        
        server_instance = self.servers[server]
        tool_method = tool.replace('.', '_')  # sql.query -> sql_query
        
        if not hasattr(server_instance, tool_method):
            raise ValueError(f"Tool {tool} not found on {server}")
        
        method = getattr(server_instance, tool_method)
        return method(**args)
    
    def get_manifest(self, server: str) -> Dict:
        """Get tool manifest for a server"""
        if server not in self.servers:
            raise ValueError(f"Unknown server: {server}")
        
        return self.servers[server].manifest()