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
            print(f"\n{'='*70}")
            print(f"[TRACKING_SERVER.tracking_upsert] STARTING UPSERT")
            print(f"{'='*70}")
            print(f"[TRACKING_SERVER.tracking_upsert] Input tracking_id: {tracking_id}")
            print(f"[TRACKING_SERVER.tracking_upsert] Input fields keys: {list(fields.keys()) if fields else []}")
            
            # Load existing records
            with open(self.db_path, 'r') as f:
                records = json.load(f)
            
            print(f"[TRACKING_SERVER.tracking_upsert] Loaded {len(records)} existing records")
            
            # Find existing record by tracking_id OR invoice_number
            existing = None
            invoice_number = fields.get('invoice_number') if fields else None
            
            if tracking_id:
                # First try to find by tracking_id
                existing = next((r for r in records if r['tracking_id'] == tracking_id), None)
                if existing:
                    print(f"[TRACKING_SERVER.tracking_upsert] Found existing record by tracking_id: {tracking_id}")
            
            if not existing and invoice_number:
                # If not found by tracking_id, try to find by invoice_number
                existing = next((r for r in records if r.get('invoice_number') == invoice_number), None)
                if existing:
                    print(f"[TRACKING_SERVER.tracking_upsert] Found existing record by invoice_number: {invoice_number}")
                    print(f"[TRACKING_SERVER.tracking_upsert] Existing tracking_id: {existing['tracking_id']}")
                    tracking_id = existing['tracking_id']  # Use existing tracking_id
            
            if not existing and not tracking_id:
                # Generate new tracking_id if not found and not provided
                tracking_id = f"trk_{uuid.uuid4().hex[:8]}"
                print(f"[TRACKING_SERVER.tracking_upsert] Generated new tracking_id: {tracking_id}")
            
            # Update or create
            if existing:
                print(f"[TRACKING_SERVER.tracking_upsert] Updating existing record")
                print(f"[TRACKING_SERVER.tracking_upsert] Old values: {existing}")
                existing.update(fields or {})
                existing['updated_at'] = datetime.utcnow().isoformat()
                print(f"[TRACKING_SERVER.tracking_upsert] New values: {existing}")
                status = "updated"
            else:
                print(f"[TRACKING_SERVER.tracking_upsert] Creating new record")
                new_record = {
                    "tracking_id": tracking_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    **(fields or {})
                }
                print(f"[TRACKING_SERVER.tracking_upsert] New record: {new_record}")
                records.append(new_record)
                status = "created"
            
            # Save back
            print(f"[TRACKING_SERVER.tracking_upsert] Saving {len(records)} records to {self.db_path}")
            with open(self.db_path, 'w') as f:
                json.dump(records, f, indent=2)
            
            result = {
                "tracking_id": tracking_id,
                "status": status,
                "invoice_number": invoice_number
            }
            print(f"[TRACKING_SERVER.tracking_upsert] Result: {result}")
            print(f"{'='*70}\n")
            
            return result
            
        except Exception as e:
            print(f"[TRACKING_SERVER.tracking_upsert] ERROR occurred!")
            print(f"[TRACKING_SERVER.tracking_upsert] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"{'='*70}\n")
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