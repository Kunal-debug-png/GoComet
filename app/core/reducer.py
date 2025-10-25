from typing import Dict, List

class Reducer:
    def reduce(self, run_id: str, node_outputs: Dict, output_type: str) -> Dict:
        """Produce final typed output"""
        
        if output_type == "plot":
            return {
                "type": "plot",
                "image_uri": node_outputs.get("render", {}).get("uri"),
                "spec_uri": node_outputs.get("spec", {}).get("uri"),
                "data_uri": node_outputs.get("tfm", {}).get("uri"),
                "status": "success"
            }
        
        elif output_type == "file_update":
            upsert_result = node_outputs.get("upsert", {})
            return {
                "type": "file_update",
                "tracking_id": upsert_result.get("tracking_id"),
                "status": upsert_result.get("status"),
                "artifacts": []
            }
        
        else:
            return {
                "type": output_type,
                "status": "completed"
            }