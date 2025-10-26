from fastapi import FastAPI
from app.api.routes import router
from app.observability.logger import logger
import uvicorn
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Agent Orchestrator",
    description="MCP + DAG Orchestration System",
    version="1.0.0"
)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logger.info("application_started")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_stopped")

@app.get("/")
async def root():
    return {
        "service": "Agent Orchestrator",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )