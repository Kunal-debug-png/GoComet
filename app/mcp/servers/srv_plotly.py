import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict

class PlotlyServer:
    def plotly_render(self, spec: Dict, format: str = "png") -> bytes:
        """Render plot from spec to image"""
        try:
            # Extract spec details
            encoding = spec.get('encoding', {})
            data = spec.get('data', [])
            
            # Create figure
            fig = go.Figure()
            
            # Add trace based on mark type
            mark = encoding.get('mark', 'line')
            
            if mark == 'line':
                fig.add_trace(go.Scatter(
                    x=[row[encoding['x']] for row in data],
                    y=[row[encoding['y']] for row in data],
                    mode='lines+markers',
                    name=encoding.get('y', 'Value')
                ))
            elif mark == 'bar':
                fig.add_trace(go.Bar(
                    x=[row[encoding['x']] for row in data],
                    y=[row[encoding['y']] for row in data],
                    name=encoding.get('y', 'Value')
                ))
            
            # Update layout
            fig.update_layout(
                title=spec.get('title', 'Chart'),
                xaxis_title=encoding.get('x', 'X'),
                yaxis_title=encoding.get('y', 'Y'),
                width=1600,
                height=900
            )
            
            # Render to PNG
            img_bytes = pio.to_image(fig, format=format)
            return img_bytes
            
        except Exception as e:
            # Return error as text image
            return str(e).encode()
    
    def manifest(self) -> dict:
        return {
            "server": "srv_plotly",
            "tools": [{
                "name": "plotly.render",
                "description": "Render plotly chart to image",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "spec": {"type": "object"},
                        "format": {"type": "string", "default": "png"}
                    },
                    "required": ["spec"]
                }
            }]
        }