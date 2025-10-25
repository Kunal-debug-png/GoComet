from pydantic import BaseModel
from typing import Optional, Dict, List

class RouteRequest(BaseModel):
    query: str
    file_path: Optional[str] = None

class RouteResponse(BaseModel):
    plan_id: str
    run_id: str
    plan: Dict

class RunStatusResponse(BaseModel):
    id: str
    status: str
    result: Optional[Dict] = None
    artifacts: List[str] = []
    metrics: Optional[Dict] = None
    error: Optional[str] = None