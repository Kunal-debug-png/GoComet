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
executor = Executor(artifacts, mcp_pool)

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
        # Route query
        flow_type, context = route_classifier.route(req.query, req.file_path)
        
        # Build plan
        plan = planner.plan(flow_type, req.query, context)
        
        # Create run
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
        # Get run
        run = db.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        if run["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Run already {run['status']}")
        
        # Get plan (stored in router response, need to reconstruct)
        flow_type = "flow_plot" if "plot" in run["input_query"]["query"] else "flow_pdf_tracking"
        context = {}
        plan = planner.plan(flow_type, run["input_query"]["query"], context)
        
        # Execute in background
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
        
        # Get result from in-memory storage
        if run_id not in run_results:
            return RunStatusResponse(
                id=run_id,
                status="running",
                result=None,
                artifacts=[],
                metrics={"total_duration_ms": 0, "node_count": 0, "success_count": 0},
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
            metrics={"total_duration_ms": 0, "node_count": 0, "success_count": 0},
            error=result_data.get("error")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    return {
        "runs_total": 0, 
        "nodes_total": {"success": 0, "failed": 0}
    }