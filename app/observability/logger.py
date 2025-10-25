import structlog
import logging
import sys
from datetime import datetime

def setup_logging():
    """Configure structlog for JSON output"""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    return structlog.get_logger()

logger = setup_logging()

def log_node_execution(run_id: str, node_id: str, node_type: str, 
                       status: str, start_ms: int, end_ms: int, 
                       error: str = None, artifact_uri: str = None):
    """Log structured node execution event"""
    logger.info(
        "node_execution",
        run_id=run_id,
        node_id=node_id,
        type=node_type,
        start_ms=start_ms,
        end_ms=end_ms,
        duration_ms=end_ms - start_ms,
        status=status,
        error=error,
        artifact_uri=artifact_uri
    )