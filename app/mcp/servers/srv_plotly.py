import plotly.graph_objects as go
import plotly.io as pio
from typing import Dict

class PlotlyServer:
    def plotly_render(self, spec: Dict, format: str = "png") -> bytes:
        """Render plot from spec to image"""
        try:
            print(f"\n{'='*70}")
            print(f"[PLOTLY_SERVER.plotly_render] STARTING RENDER")
            print(f"{'='*70}")
            print(f"[PLOTLY_SERVER.plotly_render] Format: {format}")
            print(f"[PLOTLY_SERVER.plotly_render] Spec keys: {list(spec.keys())}")
            
            # Extract spec details
            encoding = spec.get('encoding', {})
            data = spec.get('data', [])
            
            print(f"[PLOTLY_SERVER.plotly_render] Data points: {len(data)}")
            print(f"[PLOTLY_SERVER.plotly_render] Encoding: {encoding}")
            print(f"[PLOTLY_SERVER.plotly_render] Title: {spec.get('title', 'Chart')}")
            
            # Create figure
            fig = go.Figure()
            
            # Add trace based on mark type
            mark = encoding.get('mark', 'line')
            print(f"[PLOTLY_SERVER.plotly_render] Chart type (mark): {mark}")
            
            if mark == 'line':
                x_data = [row[encoding['x']] for row in data]
                y_data = [row[encoding['y']] for row in data]
                print(f"[PLOTLY_SERVER.plotly_render] X axis ({encoding['x']}): {len(x_data)} points")
                print(f"[PLOTLY_SERVER.plotly_render] Y axis ({encoding['y']}): {len(y_data)} points")
                print(f"[PLOTLY_SERVER.plotly_render] X range: {x_data[0] if x_data else 'N/A'} to {x_data[-1] if x_data else 'N/A'}")
                print(f"[PLOTLY_SERVER.plotly_render] Y range: {min(y_data) if y_data else 'N/A'} to {max(y_data) if y_data else 'N/A'}")
                
                fig.add_trace(go.Scatter(
                    x=x_data,
                    y=y_data,
                    mode='lines+markers',
                    name=encoding.get('y', 'Value')
                ))
            elif mark == 'bar':
                x_data = [row[encoding['x']] for row in data]
                y_data = [row[encoding['y']] for row in data]
                print(f"[PLOTLY_SERVER.plotly_render] Bar chart - X: {len(x_data)} bars, Y range: {min(y_data) if y_data else 'N/A'} to {max(y_data) if y_data else 'N/A'}")
                
                fig.add_trace(go.Bar(
                    x=x_data,
                    y=y_data,
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
            
            print(f"[PLOTLY_SERVER.plotly_render] Rendering to {format}...")
            # Render to PNG
            img_bytes = pio.to_image(fig, format=format)
            print(f"[PLOTLY_SERVER.plotly_render] Render complete, image size: {len(img_bytes)} bytes")
            print(f"{'='*70}\n")
            
            return img_bytes
            
        except Exception as e:
            print(f"[PLOTLY_SERVER.plotly_render] ERROR occurred!")
            print(f"[PLOTLY_SERVER.plotly_render] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'='*70}\n")
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