from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.api.models import RouteRequest, RouteResponse, RunStatusResponse
from app.core.router import Router
from app.core.planner import Planner
from app.core.executor_simple import Executor
from app.storage.database import Database
from app.storage.artifacts import ArtifactManager
from app.mcp.client_pool import MCPClientPool
from typing import Dict
import uuid

router = APIRouter(prefix="/v1")

# Initialize components
db = Database()
artifacts = ArtifactManager()
mcp_pool = MCPClientPool()
route_classifier = Router()
planner = Planner()
executor = Executor(db, artifacts, mcp_pool)

# Store run results in memory (simple CSV-based approach)
run_results = {}

async def execute_run(run_id: str, plan: Dict):
    """Execute run and store result"""
    try:
        result = await executor.execute(run_id, plan)
        run_results[run_id] = {
            "status": "success",
            "result": result,
            "artifacts": []  # Will be populated from artifacts directory
        }
    except Exception as e:
        run_results[run_id] = {
            "status": "failed",
            "result": None,
            "error": str(e),
            "artifacts": []
        }

@router.post("/route", response_model=RouteResponse)
async def route_request(req: RouteRequest):
    """Route request and create execution plan"""
    try:
        flow_type, context = route_classifier.route(req.query, req.file_path)
        plan = planner.plan(flow_type, req.query, context)
        
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        db.create_run(run_id, plan["plan_id"], {
            "query": req.query,
            "file_path": req.file_path
        })
        
        return RouteResponse(
            plan_id=plan["plan_id"],
            run_id=run_id,
            plan=plan
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/runs/{run_id}/start")
async def start_run(run_id: str, background_tasks: BackgroundTasks):
    """Start execution of a run"""
    try:
        run = db.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        if run["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Run already {run['status']}")
        
        query = run["input_query"]["query"]
        file_path = run["input_query"].get("file_path")
        
        if file_path in ["string", "", None]:
            file_path = None
        
        flow_type, context = route_classifier.route(query, file_path)
        plan = planner.plan(flow_type, query, context)
        
        background_tasks.add_task(execute_run, run_id, plan)
        
        return {"status": "started", "run_id": run_id}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/runs/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: str):
    """Get run status and results"""
    try:
        # Check if run exists in database
        run = db.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        # Calculate real metrics from database
        def calculate_run_metrics(run_id: str) -> dict:
            nodes = db.get_run_nodes(run_id)
            if not nodes:
                return {"total_duration_ms": 0, "node_count": 0, "success_count": 0}
            
            total_duration = 0
            success_count = 0
            
            for node in nodes:
                if node.get("status") == "success":
                    success_count += 1
                
                start_ms = node.get("start_ms")
                end_ms = node.get("end_ms")
                if start_ms and end_ms:
                    total_duration += (end_ms - start_ms)
            
            return {
                "total_duration_ms": total_duration,
                "node_count": len(nodes),
                "success_count": success_count
            }
        
        # Get result from in-memory storage
        if run_id not in run_results:
            return RunStatusResponse(
                id=run_id,
                status="running",
                result=None,
                artifacts=[],
                metrics=calculate_run_metrics(run_id),
                error=None
            )
        
        result_data = run_results[run_id]
        
        # Get artifacts from filesystem
        import os
        artifacts_dir = f"./artifacts/{run_id}"
        artifact_uris = []
        if os.path.exists(artifacts_dir):
            for node_dir in os.listdir(artifacts_dir):
                node_path = os.path.join(artifacts_dir, node_dir)
                if os.path.isdir(node_path):
                    for file in os.listdir(node_path):
                        artifact_uris.append(f"artifact://{node_dir}/{file}")
        
        return RunStatusResponse(
            id=run_id,
            status=result_data["status"],
            result=result_data["result"],
            artifacts=artifact_uris,
            metrics=calculate_run_metrics(run_id),
            error=result_data.get("error")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        return db.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")