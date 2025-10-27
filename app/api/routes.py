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
        print(f"\n{'#'*70}")
        print(f"[API.route] NEW REQUEST RECEIVED")
        print(f"{'#'*70}")
        print(f"[API.route] Query: '{req.query}'")
        print(f"[API.route] File path: {req.file_path}")
        print(f"[API.route] Starting routing process...")
        
        # Route query
        print(f"\n[API.route] Step 1: Calling Router...")
        flow_type, context = route_classifier.route(req.query, req.file_path)
        print(f"[API.route] Router completed")
        print(f"[API.route] Flow type: {flow_type}")
        print(f"[API.route] Context: {context}")
        
        # Build plan
        print(f"\n[API.route] Step 2: Calling Planner...")
        plan = planner.plan(flow_type, req.query, context)
        print(f"[API.route] Planner completed")
        print(f"[API.route] Plan ID: {plan['plan_id']}")
        print(f"[API.route] Plan nodes: {len(plan['nodes'])}")
        
        # Show SQL node details if present
        sql_node = next((n for n in plan['nodes'] if n.get('tool') == 'sql.query'), None)
        if sql_node:
            print(f"[API.route] SQL WHERE clause: {sql_node['args']['sql']}")
        
        # Create run
        print(f"\n[API.route] Step 3: Creating run in database...")
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        db.create_run(run_id, plan["plan_id"], {
            "query": req.query,
            "file_path": req.file_path
        })
        print(f"[API.route] Run created: {run_id}")
        print(f"[API.route] Request processing complete")
        print(f"{'#'*70}\n")
        
        return RouteResponse(
            plan_id=plan["plan_id"],
            run_id=run_id,
            plan=plan
        )
    
    except Exception as e:
        print(f"[API.route] ERROR occurred!")
        print(f"[API.route] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'#'*70}\n")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/runs/{run_id}/start")
async def start_run(run_id: str, background_tasks: BackgroundTasks):
    """Start execution of a run"""
    try:
        print(f"\n{'#'*70}")
        print(f"[API.start] START RUN REQUEST")
        print(f"{'#'*70}")
        print(f"[API.start] Run ID: {run_id}")
        
        # Get run
        print(f"[API.start] Fetching run from database...")
        run = db.get_run(run_id)
        if not run:
            print(f"[API.start] ERROR: Run not found!")
            raise HTTPException(status_code=404, detail="Run not found")
        
        print(f"[API.start] Run found, status: {run['status']}")
        
        if run["status"] != "pending":
            print(f"[API.start] ERROR: Run already {run['status']}")
            raise HTTPException(status_code=400, detail=f"Run already {run['status']}")
        
        print(f"[API.start] Run details:")
        print(f"  Plan ID: {run['plan_id']}")
        print(f"  Query: {run['input_query']['query']}")
        
        # Get plan (need to reconstruct with proper routing)
        print(f"\n[API.start] Reconstructing plan...")
        print(f"[API.start] Original query: '{run['input_query']['query']}'")
        
        # Re-route to get proper flow_type and context
        query = run["input_query"]["query"]
        file_path = run["input_query"].get("file_path")
        
        # Filter out placeholder file_path values
        if file_path in ["string", "", None]:
            file_path = None
            print(f"[API.start] Ignoring placeholder file_path")
        
        print(f"[API.start] Re-routing query to extract context...")
        flow_type, context = route_classifier.route(query, file_path)
        print(f"[API.start] Re-routing complete")
        print(f"[API.start] Flow type: {flow_type}")
        print(f"[API.start] Context: {context}")
        
        plan = planner.plan(flow_type, query, context)
        print(f"[API.start] Plan reconstructed: {plan['plan_id']}")
        print(f"[API.start] Plan has {len(plan['nodes'])} nodes")
        
        # Execute in background
        print(f"[API.start] Adding execution task to background...")
        background_tasks.add_task(execute_run, run_id, plan)
        print(f"[API.start] Background task added, returning response")
        print(f"{'#'*70}\n")
        
        return {"status": "started", "run_id": run_id}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API.start] ERROR occurred!")
        print(f"[API.start] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'#'*70}\n")
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