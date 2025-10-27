import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict

class PlotlyServer:
    def plotly_render(self, spec: Dict, format: str = "png") -> bytes:
        """Render plot from spec to image"""
        try:
            encoding = spec.get('encoding', {})
            data = spec.get('data', [])
            
            # Handle empty data
            if not data:
                raise ValueError("No data provided for plotting")
            
            fig = go.Figure()
            
            mark = encoding.get('mark', 'line')
            x_field = encoding.get('x')
            y_field = encoding.get('y')
            
            if not x_field or not y_field:
                raise ValueError("Missing x or y field in encoding")
            
            if mark == 'line':
                x_data = [row.get(x_field) for row in data]
                y_data = [row.get(y_field) for row in data]
                
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=y_data,
                    mode='lines+markers',
                    name=y_field,
                    line=dict(width=2),
                    marker=dict(size=8)
                ))
            elif mark == 'bar':
                x_data = [row.get(x_field) for row in data]
                y_data = [row.get(y_field) for row in data]
                
                fig.add_trace(go.Bar(
                    x=x_data,
                    y=y_data,
                    name=y_field
                ))
            
            # Enhanced layout
            fig.update_layout(
                title=dict(
                    text=spec.get('title', 'Chart'),
                    font=dict(size=20)
                ),
                xaxis_title=x_field,
                yaxis_title=y_field,
                width=1600,
                height=900,
                template='plotly_white',
                showlegend=True
            )
            
            img_bytes = pio.to_image(fig, format=format)
            return img_bytes
            
        except Exception as e:
            # Return error as bytes
            error_msg = f"Plotly render error: {str(e)}"
            return error_msg.encode()
    
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