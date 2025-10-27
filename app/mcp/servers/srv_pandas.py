import pandas as pd
from typing import Dict

class PandasServer:
    def dataframe_transform(self, script: str, dataframe_data: Dict) -> dict:
        """Transform dataframe using pandas operations"""
        try:
            print(f"\n{'='*70}")
            print(f"[PANDAS_SERVER.dataframe_transform] STARTING TRANSFORM")
            print(f"{'='*70}")
            print(f"[PANDAS_SERVER.dataframe_transform] Script: {script}")
            print(f"[PANDAS_SERVER.dataframe_transform] Input data rows: {len(dataframe_data.get('rows', []))}")
            
            # Reconstruct dataframe from dict
            df = pd.DataFrame(dataframe_data['rows'])
            print(f"[PANDAS_SERVER.dataframe_transform] DataFrame created with shape: {df.shape}")
            print(f"[PANDAS_SERVER.dataframe_transform] DataFrame columns: {list(df.columns)}")
            
            # Execute transform (safe subset)
            if 'rolling' in script:
                # Example: rolling(7).mean()
                window = int(script.split('(')[1].split(')')[0])
                print(f"[PANDAS_SERVER.dataframe_transform] Applying rolling window: {window}")
                result = df.rolling(window=window).mean()
            elif 'groupby' in script:
                # Example: groupby('week').sum()
                col = script.split("'")[1]
                print(f"[PANDAS_SERVER.dataframe_transform] Applying groupby on column: {col}")
                result = df.groupby(col).sum().reset_index()
            else:
                # Direct eval for simple operations
                print(f"[PANDAS_SERVER.dataframe_transform] Applying script: df.{script}")
                result = eval(f"df.{script}")
            
            print(f"[PANDAS_SERVER.dataframe_transform] Transform complete")
            print(f"[PANDAS_SERVER.dataframe_transform] Result shape: {result.shape}")
            print(f"[PANDAS_SERVER.dataframe_transform] Result columns: {list(result.columns)}")
            print(f"[PANDAS_SERVER.dataframe_transform] First 3 rows of result:")
            for idx, row in result.head(3).iterrows():
                print(f"  {dict(row)}")
            
            result_dict = {
                "rows": result.to_dict('records'),
                "shape": list(result.shape),
                "columns": list(result.columns)
            }
            print(f"[PANDAS_SERVER.dataframe_transform] Returning {len(result_dict['rows'])} rows")
            print(f"{'='*70}\n")
            
            return result_dict
            
        except Exception as e:
            print(f"[PANDAS_SERVER.dataframe_transform] ERROR occurred!")
            print(f"[PANDAS_SERVER.dataframe_transform] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'='*70}\n")
            return {"error": str(e), "rows": []}
    
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