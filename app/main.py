"""
FastAPI application entry point.
"""
# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_request_response
from app.api.routes.document_routes import router as document_router
from app.api.routes.file_routes import upload_router
from app.api.routes.file_manager import router as file_manager_router
from app.api.routes.document_processing_routes import router as document_processing_router
from app.api.routes.test_routes import router as test_router
from app.api.routes.chat_routes import router as chat_router
from app.api.v1.uac_auth import router as uac_auth_router
from app.utils.queue_manager import queue_manager
from app.models.responses.document_responses import HealthCheckResponse, ErrorResponse
from app.db.session import init_db, close_db, test_connection
from app import __version__


# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Document Processing API", version=__version__)
    
    # Initialize PostgreSQL database
    try:
        await init_db()
        logger.info("✅ PostgreSQL database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL database: {e}")
        # Continue startup but log the error
    
    # Initialize Redis connection
    try:
        await queue_manager.get_redis_client()
        logger.info("✅ Redis connection initialized successfully")
    except Exception as e:
        logger.error("❌ Failed to initialize Redis connection", error=str(e))
        # Don't fail startup, let the app handle connection errors gracefully
    
    # Store startup time
    app.state.startup_time = time.time()
    
    logger.info("🚀 Document Processing API started successfully")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Document Processing API")
    
    # Close PostgreSQL connections
    try:
        await close_db()
        logger.info("✅ PostgreSQL database connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing PostgreSQL connections: {e}")
    
    # Close Redis connection
    try:
        await queue_manager.close()
        logger.info("✅ Redis connection closed successfully")
    except Exception as e:
        logger.error("❌ Error closing Redis connection", error=str(e))
    
    logger.info("✅ Document Processing API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Document Processing API",
    description="A FastAPI-based document processing service with Redis queue management using BullMQ",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log HTTP requests and responses."""
    start_time = time.time()
    
    # Generate request ID
    request_id = f"{int(start_time * 1000)}-{hash(str(request.url)) % 10000}"
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log request/response
    log_request_response(
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration=duration,
        request_id=request_id,
        user_agent=request.headers.get("user-agent"),
        content_length=response.headers.get("content-length"),
    )
    
    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    logger.error(
        "Validation error",
        url=str(request.url),
        method=request.method,
        errors=exc.errors()
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "timestamp": time.time(),
            "error_code": "VALIDATION_ERROR",
            "details": {
                "errors": exc.errors(),
                "body": exc.body if hasattr(exc, 'body') else None
            }
        }
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    logger.error(
        "HTTP exception",
        url=str(request.url),
        method=request.method,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "timestamp": time.time(),
            "error_code": f"HTTP_{exc.status_code}",
            "details": None
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        url=str(request.url),
        method=request.method,
        exception=str(exc),
        exception_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": time.time(),
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {
                "exception_type": type(exc).__name__,
                "exception_message": str(exc)
            }
        }
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health check",
    description="Check the health status of the API and its dependencies"
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint that returns the status of the API and its dependencies.
    """
    uptime = time.time() - app.state.startup_time if hasattr(app.state, 'startup_time') else 0
    
    # Test database connection
    db_status = "healthy"
    try:
        connection_successful = await test_connection()
        if not connection_successful:
            db_status = "unhealthy"
    except Exception as e:
        db_status = "unhealthy" 
    
    # Test Redis connection
    redis_status = "healthy"
    try:
        redis_client = await queue_manager.get_redis_client()
        await redis_client.ping()
    except Exception as e:
        redis_status = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    
    return HealthCheckResponse(
        success=True,
        message=f"Document Processing API is {overall_status}",
        service="document-processing-api",
        status=overall_status,
        version=__version__,
        uptime=uptime,
        dependencies={
            "database": db_status,
            "redis": redis_status,
            "queue_manager": "healthy" if redis_status == "healthy" else "unhealthy"
        }
    )


@app.get(
    "/health/redis",
    tags=["health"],
    summary="Redis health check",
    description="Check the health status of Redis connection"
)
async def redis_health_check() -> Dict[str, Any]:
    """
    Redis-specific health check endpoint.
    """
    try:
        redis_client = await queue_manager.get_redis_client()
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = str(time.time())
        
        # Set test value
        await redis_client.set(test_key, test_value, ex=10)  # Expire in 10 seconds
        
        # Get test value
        retrieved_value = await redis_client.get(test_key)
        
        # Clean up
        await redis_client.delete(test_key)
        
        # Check if values match
        if retrieved_value and retrieved_value.decode() == test_value:
            return {
                "status": "healthy",
                "message": "Redis connection and operations successful",
                "timestamp": time.time(),
                "details": {
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "db": settings.redis_db,
                    "connection_pool_size": redis_client.connection_pool.max_connections,
                    "test_passed": True
                }
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis test operation failed",
                "timestamp": time.time(),
                "details": {
                    "host": settings.redis_host,
                    "port": settings.redis_port,
                    "db": settings.redis_db,
                    "test_passed": False,
                    "error": "Value mismatch in test operation"
                }
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Redis health check failed: {str(e)}",
            "timestamp": time.time(),
            "error": str(e),
            "details": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db
            }
        }


# Include chat router for WebSocket functionality
app.include_router(
    chat_router,
    tags=["chat"]
)

# Include routers
app.include_router(
    document_router,
    prefix=f"/api/{settings.api_version}",
    tags=["documents"]
)

# Include upload router for file upload functionality
app.include_router(
    upload_router,
    prefix=f"/api/{settings.api_version}"
)

app.include_router(
    file_manager_router,
    prefix=f"/api/{settings.api_version}"
)

# Include document processing pipeline router
app.include_router(
    document_processing_router,
    tags=["Document Processing Pipeline"]
)

# Include test router
app.include_router(
    test_router,
    prefix=f"/api/{settings.api_version}",
    tags=["Test Workers"]
)

# Include UAC authentication router
app.include_router(
    uac_auth_router,
    prefix=f"/api/{settings.api_version}/uac-auth",
    tags=["UAC Authentication"]
)

# Mount static files for file manager UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Favicon endpoint
@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    # Return a simple response or redirect to an icon
    return JSONResponse(content={"status": "no favicon"}, status_code=204)

@app.head("/favicon.ico") 
async def favicon_head():
    """Handle HEAD requests for favicon."""
    return Response(status_code=204)

# Dashboard UI endpoint - Main landing page
@app.get(
    "/",
    tags=["dashboard"],
    summary="Dashboard UI", 
    description="Serve the main dashboard interface"
)
async def dashboard_ui():
    """Serve the main dashboard interface."""
    return FileResponse("static/modules/dashboard/dashboard.html")

# File Manager UI endpoint
@app.get(
    "/file-manager",
    tags=["file-manager"],
    summary="File Manager UI",
    description="Serve the file manager web interface"
)
async def file_manager_ui():
    """Serve the file manager web interface."""
    return FileResponse("static/modules/file-manager/index.html")

# Chat UI endpoint
@app.get(
    "/chat",
    tags=["chat"],
    summary="Chat Interface", 
    description="Serve the standalone multi-agent chat interface"
)
async def chat_ui():
    """Serve the standalone multi-agent chat interface."""
    return FileResponse("static/modules/chat/index.html")

@app.get(
    "/file-browser",
    tags=["file-browser"],
    summary="File Browser Interface",
    description="Serve the Typesense-powered knowledge base file browser"
)
async def file_browser_ui():
    """Serve the File Browser interface."""
    return FileResponse("static/modules/file-browser/file-browser.html")

# API Information endpoint
@app.get(
    "/api",
    tags=["root"],
    summary="API Information",
    description="Get basic information about the API"
)
async def api_info() -> Dict[str, Any]:
    """
    API information endpoint providing basic API information.
    """
    return {
        "name": "Document Processing API",
        "version": __version__,
        "description": "A FastAPI-based document processing service with Redis queue management using BullMQ and multi-agent chat",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "dashboard_url": "/",
        "file_manager_url": "/file-manager",
        "chat_demo_url": "/chat/demo",
        "chat_ui_url": "/chat",
        "api_prefix": f"/api/{settings.api_version}",
        "endpoints": {
            "convert_document": f"/api/{settings.api_version}/documents/convert",
            "index_typesense": f"/api/{settings.api_version}/documents/index/typesense",
            "index_qdrant": f"/api/{settings.api_version}/documents/index/qdrant",
            "sync_document": f"/api/{settings.api_version}/documents/sync",
            "chat": {
                "websocket": "/chat/ws/{session_id}",
                "demo": "/chat/demo", 
                "health": "/chat/health",
                "sessions": "/chat/sessions"
            },
            "document_processing": {
                "process": f"/api/{settings.api_version}/document-processing/process",
                "status": f"/api/{settings.api_version}/document-processing/status/{{document_id}}",
                "process_file_path": f"/api/{settings.api_version}/document-processing/process-file-path",
                "health": f"/api/{settings.api_version}/document-processing/health"
            },
            "files": {
                "upload": f"/api/{settings.api_version}/files/upload",
                "get_signed_url": f"/api/{settings.api_version}/files/get-signed-url"
            },
            "file_manager": {
                "ui": "/file-manager",
                "api": f"/api/{settings.api_version}/file-manager",
                "list": f"/api/{settings.api_version}/file-manager/",
                "upload": f"/api/{settings.api_version}/file-manager/upload",
                "create_folder": f"/api/{settings.api_version}/file-manager/folder",
                "download_file": f"/api/{settings.api_version}/file-manager/download/file",
                "download_folder": f"/api/{settings.api_version}/file-manager/download/folder",
                "delete": f"/api/{settings.api_version}/file-manager/item",
                "rename": f"/api/{settings.api_version}/file-manager/rename",
                "move": f"/api/{settings.api_version}/file-manager/move",
                "search": f"/api/{settings.api_version}/file-manager/search",
                "info": f"/api/{settings.api_version}/file-manager/info"
            },
            "test": {
                "worker": f"/api/{settings.api_version}/test/worker",
                "worker_status": f"/api/{settings.api_version}/test/worker/status",
                "health": f"/api/{settings.api_version}/test/health"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
    )