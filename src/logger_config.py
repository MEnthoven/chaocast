import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

def setup_logging(log_file: str = None, level=logging.INFO):
    """
    Set up basic logging configuration for the entire application.
    
    Args:
        log_file: Optional path to log file. If None, logs only to console
        level: Logging level, defaults to INFO
    """
    # Create logs directory if logging to file
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
    # Basic configuration with formatting
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(name)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        # handlers=[
        #     logging.StreamHandler(sys.stdout),
        #     RotatingFileHandler(
        #         log_file,
        #         maxBytes=10*1024*1024,  # 10MB
        #         backupCount=5
        #     ) if log_file else None
        # ]
    )

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Name of the logger, typically __name__ from the calling module
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
