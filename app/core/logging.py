import sys
import logging
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    from pythonjsonlogger.json import JsonFormatter as _JsonFormatter
    # Shim to match v2 API
    class _Module:
        JsonFormatter = _JsonFormatter
    jsonlogger = _Module()

def setup_logging() -> logging.Logger:
    """Sets up a structured JSON logging format on stdout."""
    root_logger = logging.getLogger("finaudit")
    root_logger.setLevel(logging.INFO)
    
    # Avoid duplicate handlers in dev reload environments
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        # Configures JSON formatter with key audit fields
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
            rename_fields={"asctime": "timestamp"}
        )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
    return root_logger

# Shared application-wide logger
logger = setup_logging()
