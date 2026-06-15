import structlog
import logging
from structlog.stdlib import BoundLogger
from src.config import config
import os

def setup_logger() -> BoundLogger:
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    logging.basicConfig(
        filename="logs/app.log",
        format="%(message)s",
        level=getattr(logging, config.log_level.upper(), logging.INFO)
    )
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=BoundLogger,
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()

logger = setup_logger()
