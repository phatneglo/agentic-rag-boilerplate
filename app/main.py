"""
FastAPI application entry point.
"""
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, status, WebSocket
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
from app.api.routes.chat_routes import router as chat_router
from app.utils.queue_manager import queue_manager
from app.models.responses.document_responses import HealthCheckResponse, ErrorResponse
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
    
    # Initialize Redis connection
    try:
        await queue_manager.get_redis_client()
        logger.info("Redis connection initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Redis connection", error=str(e))
        # Don't fail startup, let the app handle connection errors gracefully
    
    # Store startup time
    app.state.startup_time = time.time()
    
    logger.info("Document Processing API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Document Processing API")
    
    # Close Redis connection
    try:
        await queue_manager.close()
        logger.info("Redis connection closed successfully")
    except Exception as e:
        logger.error("Error closing Redis connection", error=str(e))
    
    logger.info("Document Processing API shutdown complete")


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
            "details": {
                "status_code": exc.status_code,
                "url": str(request.url),
                "method": request.method
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        url=str(request.url),
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "timestamp": time.time(),
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {
                "url": str(request.url),
                "method": request.method
            }
        }
    )


# Health check endpoints
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["health"],
    summary="Health check",
    description="Check the health status of the API and its dependencies"
)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Returns the health status of the API and its dependencies.
    """
    try:
        # Calculate uptime
        uptime = time.time() - app.state.startup_time
        
        # Check Redis connection
        dependencies = {}
        try:
            redis_client = await queue_manager.get_redis_client()
            await redis_client.ping()
            dependencies["redis"] = "connected"
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            dependencies["redis"] = "disconnected"
        
        # Check file storage
        try:
            storage_path = Path(settings.file_storage_path)
            storage_path.mkdir(parents=True, exist_ok=True)
            dependencies["storage"] = "accessible"
        except Exception as e:
            logger.warning("Storage health check failed", error=str(e))
            dependencies["storage"] = "inaccessible"
        
        # Get file storage metrics
        file_count = 0
        storage_used = 0
        try:
            storage_path = Path(settings.file_storage_path)
            if storage_path.exists():
                for file_path in storage_path.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        storage_used += file_path.stat().st_size
        except Exception as e:
            logger.warning("Failed to get storage metrics", error=str(e))
        
        # Determine overall status
        overall_status = "healthy"
        if dependencies["redis"] != "connected":
            overall_status = "degraded"
        if dependencies["storage"] != "accessible":
            overall_status = "degraded"
        
        return HealthCheckResponse(
            success=True,
            message="Service is healthy" if overall_status == "healthy" else "Service is degraded",
            service="document-processing-api",
            status=overall_status,
            version=__version__,
            uptime=uptime,
            dependencies=dependencies,
            # Additional fields for dashboard
            **{
                "file_count": file_count,
                "storage_used": storage_used,
                "storage_status": dependencies["storage"],
                "database_status": dependencies["redis"]  # Using Redis as our primary data store
            }
        )
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheckResponse(
            success=False,
            message="Health check failed",
            service="document-processing-api",
            status="unhealthy",
            version=__version__,
            uptime=0.0,
            dependencies={"redis": "unknown", "storage": "unknown"},
            **{
                "file_count": 0,
                "storage_used": 0,
                "storage_status": "unknown",
                "database_status": "unknown"
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
    
    Returns the health status of the Redis connection.
    """
    try:
        redis_client = await queue_manager.get_redis_client()
        await redis_client.ping()
        
        return {
            "success": True,
            "message": "Redis is healthy",
            "timestamp": time.time(),
            "status": "connected",
            "details": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db
            }
        }
        
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {
            "success": False,
            "message": "Redis is unhealthy",
            "timestamp": time.time(),
            "status": "disconnected",
            "error": str(e),
            "details": {
                "host": settings.redis_host,
                "port": settings.redis_port,
                "db": settings.redis_db
            }
        }


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

app.include_router(
    chat_router,
    prefix=f"/api/{settings.api_version}/chat",
    tags=["chat"]
)

# Include WebSocket directly since it needs to be at root level
from app.api.routes.chat_routes import manager

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle WebSocket data - delegated to chat routes
            import json
            import asyncio
            from app.api.routes.chat_routes import generate_ai_response
            
            try:
                message_data = json.loads(data)
                logger.info("Received WebSocket message", message_type=message_data.get("type"))
                
                if message_data.get("type") == "chat_message":
                    # Process chat message and generate AI response
                    response = await generate_ai_response(message_data.get("content", ""))
                    await manager.send_personal_message(json.dumps(response), websocket)
                elif message_data.get("type") == "ping":
                    # Respond to ping with pong
                    import time
                    pong_response = {"type": "pong", "timestamp": time.time()}
                    await manager.send_personal_message(json.dumps(pong_response), websocket)
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON received from WebSocket")
            except Exception as e:
                logger.error("Error processing WebSocket message", error=str(e))
                
    except Exception:  # WebSocketDisconnect
        manager.disconnect(websocket)

# Mount static files for file manager UI
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    summary="AI Chat Interface",
    description="Serve the AI chat web interface"
)
async def chat_ui():
    """Serve the AI chat web interface."""
    return FileResponse("static/modules/chat/chat.html")

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
        "description": "A FastAPI-based document processing service with Redis queue management using BullMQ",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "health_url": "/health",
        "dashboard_url": "/",
        "file_manager_url": "/file-manager",
        "api_prefix": f"/api/{settings.api_version}",
        "endpoints": {
            "convert_document": f"/api/{settings.api_version}/documents/convert",
            "index_typesense": f"/api/{settings.api_version}/documents/index/typesense",
            "index_qdrant": f"/api/{settings.api_version}/documents/index/qdrant",
            "sync_document": f"/api/{settings.api_version}/documents/sync",
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
            "chat": {
                "ui": "/chat",
                "api": f"/api/{settings.api_version}/chat"
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