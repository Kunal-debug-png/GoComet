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
            print(f"\n{'='*70}")
            print(f"[SQL_SERVER.sql_query] STARTING SQL EXECUTION")
            print(f"{'='*70}")
            print(f"[SQL_SERVER.sql_query] Input WHERE clause: {sql}")
            print(f"[SQL_SERVER.sql_query] CSV path: {self.csv_path}")
            
            # Check if CSV exists
            from pathlib import Path
            csv_exists = Path(self.csv_path).exists()
            print(f"[SQL_SERVER.sql_query] CSV file exists: {csv_exists}")
            
            # Read CSV and execute query
            full_query = f"""
                SELECT * FROM read_csv_auto('{self.csv_path}')
                WHERE {sql}
            """
            print(f"[SQL_SERVER.sql_query] Full SQL query:")
            print(f"  {full_query.strip()}")
            
            print(f"[SQL_SERVER.sql_query] Executing query...")
            result = self.conn.execute(full_query).df()
            
            print(f"[SQL_SERVER.sql_query] Query executed successfully")
            print(f"[SQL_SERVER.sql_query] Rows returned: {len(result)}")
            
            if len(result) > 0:
                print(f"[SQL_SERVER.sql_query] Result columns: {list(result.columns)}")
                weeks = sorted(result['week'].unique()) if 'week' in result.columns else []
                print(f"[SQL_SERVER.sql_query] Unique weeks in result: {weeks}")
                print(f"[SQL_SERVER.sql_query] Week range: {weeks[0] if weeks else 'N/A'} to {weeks[-1] if weeks else 'N/A'}")
                
                if 'sales' in result.columns:
                    total_sales = result['sales'].sum()
                    print(f"[SQL_SERVER.sql_query] Total sales: ${total_sales:,.2f}")
                
                print(f"[SQL_SERVER.sql_query] First 3 rows:")
                for idx, row in result.head(3).iterrows():
                    print(f"  {dict(row)}")
            else:
                print(f"[SQL_SERVER.sql_query] WARNING: No rows returned!")
            
            result_dict = {
                "rows": result.to_dict('records'),
                "row_count": len(result)
            }
            print(f"[SQL_SERVER.sql_query] Returning result with {len(result_dict['rows'])} rows")
            print(f"{'='*70}\n")
            
            return result_dict
            
        except Exception as e:
            print(f"[SQL_SERVER.sql_query] ERROR occurred!")
            print(f"[SQL_SERVER.sql_query] Error type: {type(e).__name__}")
            print(f"[SQL_SERVER.sql_query] Error message: {str(e)}")
            import traceback
            print(f"[SQL_SERVER.sql_query] Traceback:")
            traceback.print_exc()
            print(f"{'='*70}\n")
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