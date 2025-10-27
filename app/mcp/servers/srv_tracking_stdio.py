#!/usr/bin/env python3
"""Tracking Server - MCP stdio implementation"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.mcp.protocol import MCPProtocol
from app.mcp.servers.srv_tracking import TrackingServer


def main():
    """Main entry point for stdio server"""
    # Check for --manifest flag
    if len(sys.argv) > 1 and sys.argv[1] == "--manifest":
        server = TrackingServer()
        MCPProtocol.write_manifest(server.manifest())
        return
    
    # Setup stdio mode - redirect debug prints to stderr
    original_stdout = MCPProtocol.setup_stdio_mode()
    
    # Initialize server
    server = TrackingServer()
    
    # Read and process requests
    while True:
        request = MCPProtocol.read_request()
        if request is None:
            break
        
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            # Route to appropriate method
            if method == "tracking.upsert":
                result = server.tracking_upsert(**params)
                MCPProtocol.write_response(request_id, result, original_stdout)
            else:
                MCPProtocol.write_error(
                    request_id,
                    -32601,
                    f"Method not found: {method}",
                    stdout_handle=original_stdout
                )
        except Exception as e:
            MCPProtocol.write_error(
                request_id,
                -32603,
                f"Internal error: {str(e)}",
                stdout_handle=original_stdout
            )


if __name__ == "__main__":
    main()
