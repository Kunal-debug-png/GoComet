import json
from pathlib import Path
from datetime import datetime
import uuid

class TrackingServer:
    def __init__(self, db_path: str = "./samples/tracking.json"):
        self.db_path = Path(db_path)
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
            # Load existing records
            with open(self.db_path, 'r') as f:
                records = json.load(f)
            
            # Find existing record
            if tracking_id:
                existing = next((r for r in records if r['tracking_id'] == tracking_id), None)
            else:
                existing = None
                tracking_id = f"trk_{uuid.uuid4().hex[:8]}"
            
            # Update or create
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
            
            # Save back
            with open(self.db_path, 'w') as f:
                json.dump(records, f, indent=2)
            
            return {
                "tracking_id": tracking_id,
                "status": status
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