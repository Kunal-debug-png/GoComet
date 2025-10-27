#!/usr/bin/env python3
"""Generate a line chart of weekly sales"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.mcp.stdio_client import MCPStdioClient
import base64

# Use absolute path to server script
server_path = project_root / "app" / "mcp" / "servers" / "srv_plotly_stdio.py"
client = MCPStdioClient(str(server_path))

spec = {
    "encoding": {"x": "week", "y": "sales", "mark": "line"},
    "data": [
        {"week": "W49", "sales": 1950.3},
        {"week": "W50", "sales": 2850.45},
        {"week": "W51", "sales": 2050.9},
        {"week": "W52", "sales": 3000.25}
    ],
    "title": "Weekly Sales - Line Chart"
}

print("Generating line chart...")
result = client.call_tool("plotly.render", {"spec": spec, "format": "png"})

image_bytes = base64.b64decode(result["image_base64"])
output_file = os.path.join(os.path.dirname(__file__), "line_chart.png")

with open(output_file, "wb") as f:
    f.write(image_bytes)

print(f"✓ Chart saved: {output_file}")
print(f"✓ Size: {len(image_bytes):,} bytes")
