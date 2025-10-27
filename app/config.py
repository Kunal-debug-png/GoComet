import os
from pathlib import Path

class Config:
    """Configuration management using environment variables"""
    
    # Database
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./orchestrator.db")
    
    # Artifacts storage
    ARTIFACTS_PATH = os.getenv("ARTIFACTS_PATH", "./artifacts")
    
    # Data sources
    ORDERS_CSV_PATH = os.getenv("ORDERS_CSV_PATH", "./samples/orders.csv")
    TRACKING_JSON_PATH = os.getenv("TRACKING_JSON_PATH", "./samples/tracking.json")
    
    # Configuration files
    CAPABILITY_INDEX_PATH = os.getenv("CAPABILITY_INDEX_PATH", "./config/capability_index.json")
    
    # API Keys
    LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
    
    # Server settings
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    
    @classmethod
    def ensure_directories(cls):
        """Create necessary directories"""
        for path_attr in ["DATABASE_PATH", "ARTIFACTS_PATH", "ORDERS_CSV_PATH", 
                         "TRACKING_JSON_PATH", "CAPABILITY_INDEX_PATH"]:
            path = getattr(cls, path_attr)
            Path(path).parent.mkdir(parents=True, exist_ok=True)