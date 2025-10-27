import duckdb
from pathlib import Path
from app.config import Config

class SQLServer:
    def __init__(self, csv_path: str = None):
        self.csv_path = csv_path or Config.ORDERS_CSV_PATH
        self.conn = duckdb.connect(':memory:')
    
    def sql_query(self, sql: str) -> dict:
        """Execute SQL query on orders CSV"""
        try:
            full_query = f"""
                SELECT * FROM read_csv_auto('{self.csv_path}')
                WHERE {sql}
            """
            result = self.conn.execute(full_query).df()
            
            return {
                "rows": result.to_dict('records'),
                "row_count": len(result)
            }
            
        except Exception as e:
            return {"error": str(e), "rows": []}
    
    def manifest(self) -> dict:
        """Return tool manifest"""
        return {
            "server": "srv_sql",
            "tools": [{
                "name": "sql.query",
                "description": "Execute SQL query on CSV data",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL WHERE clause"}
                    },
                    "required": ["sql"]
                }
            }]
        }