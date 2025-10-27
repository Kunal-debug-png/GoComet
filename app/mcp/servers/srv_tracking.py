import json
from pathlib import Path
from datetime import datetime
import uuid
from app.config import Config

class TrackingServer:
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or Config.TRACKING_JSON_PATH)
        self._ensure_db()
    
    def _ensure_db(self):
        """Create tracking DB if not exists"""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump([], f)
    
    def tracking_upsert(self, tracking_id: str = None, fields: dict = None) -> dict:
        """Upsert tracking record"""
        try:
            with open(self.db_path, 'r') as f:
                records = json.load(f)
            
            existing = None
            invoice_number = fields.get('invoice_number') if fields else None
            
            if tracking_id:
                existing = next((r for r in records if r['tracking_id'] == tracking_id), None)
            
            if not existing and invoice_number:
                existing = next((r for r in records if r.get('invoice_number') == invoice_number), None)
                if existing:
                    tracking_id = existing['tracking_id']
            
            if not existing and not tracking_id:
                tracking_id = f"trk_{uuid.uuid4().hex[:8]}"
            
            if existing:
                existing.update(fields or {})
                existing['updated_at'] = datetime.utcnow().isoformat()
                status = "updated"
            else:
                new_record = {
                    "tracking_id": tracking_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    **(fields or {})
                }
                records.append(new_record)
                status = "created"
            
            with open(self.db_path, 'w') as f:
                json.dump(records, f, indent=2)
            
            return {
                "tracking_id": tracking_id,
                "status": status,
                "invoice_number": invoice_number
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def manifest(self) -> dict:
        return {
            "server": "srv_tracking",
            "tools": [{
                "name": "tracking.upsert",
                "description": "Create or update tracking record",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "tracking_id": {"type": "string"},
                        "fields": {"type": "object"}
                    }
                }
            }]
        }