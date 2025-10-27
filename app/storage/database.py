import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path
from app.config import Config

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._init_db()
    
    def _init_db(self):
        """Create tables if not exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                input_query TEXT,
                result TEXT,
                error TEXT
            )
        """)
        
        # Nodes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                input_artifacts TEXT,
                output_artifact TEXT,
                error TEXT,
                idempotency_key TEXT,
                retries INTEGER DEFAULT 0,
                start_ms INTEGER,
                end_ms INTEGER,
                FOREIGN KEY (run_id) REFERENCES runs(id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_run_id ON nodes(run_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_idempotency ON nodes(idempotency_key)")
        
        conn.commit()
        conn.close()
    
    def create_run(self, run_id: str, plan_id: str, input_query: Dict):
        """Create new run"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO runs (id, plan_id, status, created_at, input_query)
            VALUES (?, ?, ?, ?, ?)
        """, (run_id, plan_id, "pending", datetime.utcnow().isoformat(), 
              json.dumps(input_query)))
        
        conn.commit()
        conn.close()
    
    def update_run_status(self, run_id: str, status: str, 
                         result: Optional[Dict] = None, 
                         error: Optional[str] = None):
        """Update run status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.utcnow().isoformat()
        
        if status == "running":
            cursor.execute("""
                UPDATE runs 
                SET status = ?, started_at = ?
                WHERE id = ?
            """, (status, now, run_id))
        elif status in ["success", "failed"]:
            cursor.execute("""
                UPDATE runs 
                SET status = ?, finished_at = ?, result = ?, error = ?
                WHERE id = ?
            """, (status, now, json.dumps(result) if result else None, 
                  error, run_id))
        
        conn.commit()
        conn.close()
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get run by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row["id"],
            "plan_id": row["plan_id"],
            "status": row["status"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "input_query": json.loads(row["input_query"]) if row["input_query"] else None,
            "result": json.loads(row["result"]) if row["result"] else None,
            "error": row["error"]
        }
    
    def create_node(self, run_id: str, node_id: str, node_type: str, 
                    idempotency_key: str):
        """Create node record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        node_pk = f"{run_id}_{node_id}"
        
        cursor.execute("""
            INSERT INTO nodes (id, run_id, node_id, type, status, idempotency_key)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (node_pk, run_id, node_id, node_type, "pending", idempotency_key))
        
        conn.commit()
        conn.close()
    
    def update_node_status(self, run_id: str, node_id: str, status: str,
                          output_artifact: Optional[str] = None,
                          error: Optional[str] = None,
                          start_ms: Optional[int] = None,
                          end_ms: Optional[int] = None):
        """Update node status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        node_pk = f"{run_id}_{node_id}"
        
        cursor.execute("""
            UPDATE nodes
            SET status = ?, output_artifact = ?, error = ?, 
                start_ms = COALESCE(?, start_ms),
                end_ms = COALESCE(?, end_ms)
            WHERE id = ?
        """, (status, output_artifact, error, start_ms, end_ms, node_pk))
        
        conn.commit()
        conn.close()
    
    def get_node_by_idempotency(self, idempotency_key: str) -> Optional[Dict]:
        """Get cached node by idempotency key"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM nodes 
            WHERE idempotency_key = ? AND status = 'success'
            ORDER BY end_ms DESC
            LIMIT 1
        """, (idempotency_key,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "node_id": row["node_id"],
            "output_artifact": row["output_artifact"],
            "status": row["status"]
        }
    
    def get_run_nodes(self, run_id: str) -> List[Dict]:
        """Get all nodes for a run"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM nodes WHERE run_id = ?", (run_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_metrics(self) -> Dict:
        """Get system metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count total runs
        cursor.execute("SELECT COUNT(*) FROM runs")
        runs_total = cursor.fetchone()[0]
        
        # Count nodes by status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM nodes 
            GROUP BY status
        """)
        nodes_by_status = dict(cursor.fetchall())
        
        # Calculate timing percentiles
        cursor.execute("""
            SELECT (end_ms - start_ms) as duration
            FROM nodes 
            WHERE start_ms IS NOT NULL AND end_ms IS NOT NULL
            AND status = 'success'
        """)
        durations = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Calculate percentiles
        if durations:
            durations.sort()
            n = len(durations)
            p50 = durations[int(n * 0.5)] if n > 0 else 0
            p95 = durations[int(n * 0.95)] if n > 0 else 0
        else:
            p50 = p95 = 0
        
        return {
            "runs_total": runs_total,
            "nodes_total": {
                "success": nodes_by_status.get("success", 0),
                "failed": nodes_by_status.get("failed", 0),
                "pending": nodes_by_status.get("pending", 0),
                "running": nodes_by_status.get("running", 0)
            },
            "latency_ms": {
                "p50": float(p50),
                "p95": float(p95),
                "count": len(durations)
            }
        }