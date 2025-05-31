"""
Logging configuration for the application.
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from rich.console import Console
from rich.logging import RichHandler

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""
    
    # Ensure log directory exists
    log_file_path = Path(settings.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
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
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Add rich handler for better console output in development
    if settings.debug:
        console = Console()
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        rich_handler.setLevel(getattr(logging, settings.log_level.upper()))
        
        # Get root logger and add rich handler
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(rich_handler)
    
    # Add file handler
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setLevel(getattr(logging, settings.log_level.upper()))
    
    if settings.log_format == "json":
        file_formatter = logging.Formatter('%(message)s')
    else:
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    file_handler.setFormatter(file_formatter)
    logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_request_response(
    method: str,
    url: str,
    status_code: int,
    duration: float,
    request_id: str = None,
    **kwargs: Any
) -> None:
    """Log HTTP request/response information."""
    logger = get_logger("http")
    
    log_data = {
        "method": method,
        "url": url,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2),
        **kwargs
    }
    
    if request_id:
        log_data["request_id"] = request_id
    
    if status_code >= 400:
        logger.error("HTTP request failed", **log_data)
    else:
        logger.info("HTTP request completed", **log_data)


def log_job_event(
    job_id: str,
    queue_name: str,
    event_type: str,
    **kwargs: Any
) -> None:
    """Log job processing events."""
    logger = get_logger("jobs")
    
    log_data = {
        "job_id": job_id,
        "queue_name": queue_name,
        "event_type": event_type,
        **kwargs
    }
    
    if event_type in ["failed", "error"]:
        logger.error("Job event", **log_data)
    else:
        logger.info("Job event", **log_data) 