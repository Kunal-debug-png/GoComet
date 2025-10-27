import pandas as pd
from typing import Dict

class PandasServer:
    def dataframe_transform(self, script: str, dataframe_data: Dict) -> dict:
        """Transform dataframe using pandas operations"""
        try:
            df = pd.DataFrame(dataframe_data['rows'])
            
            # Handle empty dataframe
            if df.empty:
                return {
                    "rows": [],
                    "shape": [0, 0],
                    "columns": []
                }
            
            # Parse and execute script
            if 'rolling' in script:
                window = int(script.split('(')[1].split(')')[0])
                result = df.rolling(window=window).mean()
            elif 'groupby' in script:
                col = script.split("'")[1]
                result = df.groupby(col).sum().reset_index()
            elif 'tail' in script:
                # Extract number from tail(n)
                n = int(script.split('(')[1].split(')')[0])
                result = df.tail(n)
            elif 'head' in script:
                # Extract number from head(n)
                n = int(script.split('(')[1].split(')')[0])
                result = df.head(n)
            elif 'sort_values' in script:
                # Handle sort_values with parameters
                result = eval(f"df.{script}")
            else:
                result = eval(f"df.{script}")
            
            return {
                "rows": result.to_dict('records'),
                "shape": list(result.shape),
                "columns": list(result.columns)
            }
            
        except Exception as e:
            return {"error": str(e), "rows": [], "shape": [0, 0], "columns": []}
    
    def manifest(self) -> dict:
        return {
            "server": "srv_pandas",
            "tools": [{
                "name": "dataframe.transform",
                "description": "Transform dataframes with pandas",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "script": {"type": "string"},
                        "dataframe_data": {"type": "object"}
                    },
                    "required": ["script", "dataframe_data"]
                }
            }]
        }