"""
Document Processing API Routes.
Endpoints for the 4-step document processing pipeline.
"""
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger
from app.services.document_processing_pipeline import get_pipeline_service, DocumentProcessingPipeline
from app.core.config import settings


# Configure logging
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/document-processing", tags=["Document Processing"])


@router.post("/process")
async def process_document(
    file: UploadFile = File(...),
    processing_options: Optional[str] = Form(None),
    pipeline_service: DocumentProcessingPipeline = Depends(get_pipeline_service)
) -> JSONResponse:
    """
    Process a document through the complete 4-step pipeline:
    1. Document-to-Markdown conversion using Marker
    2. Metadata extraction using LlamaIndex  
    3. Typesense indexing with embeddings
    4. Qdrant indexing for RAG
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.htm', '.pptx', '.ppt', '.xlsx', '.xls', '.epub']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file_extension}. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (e.g., 50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
        
        # Save uploaded file temporarily
        upload_dir = settings.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        
        temp_file_path = os.path.join(upload_dir, file.filename)
        
        with open(temp_file_path, 'wb') as f:
            f.write(file_content)
        
        # Parse processing options if provided
        options = {}
        if processing_options:
            import json
            try:
                options = json.loads(processing_options)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid processing_options JSON format"
                )
        
        logger.info(
            "Starting document processing pipeline",
            filename=file.filename,
            file_size=len(file_content),
            options=options
        )
        
        # Start the processing pipeline
        result = await pipeline_service.process_document(
            source_file_path=temp_file_path,
            processing_options=options
        )
        
        logger.info(
            "Document processing pipeline started",
            document_id=result["document_id"],
            filename=file.filename
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Document processing started successfully",
                "data": result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get("/status/{document_id}")
async def get_processing_status(
    document_id: str,
    pipeline_service: DocumentProcessingPipeline = Depends(get_pipeline_service)
) -> JSONResponse:
    """
    Get the status of a document processing pipeline.
    """
    try:
        status_info = await pipeline_service.get_pipeline_status(document_id)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Pipeline status retrieved successfully",
                "data": status_info
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline status: {str(e)}"
        )


@router.post("/process-file-path")
async def process_document_by_path(
    request_data: Dict[str, Any],
    pipeline_service: DocumentProcessingPipeline = Depends(get_pipeline_service)
) -> JSONResponse:
    """
    Process a document by file path (for internal use).
    
    Request body:
    {
        "file_path": "/path/to/document.pdf",
        "processing_options": {...}
    }
    """
    try:
        file_path = request_data.get("file_path")
        processing_options = request_data.get("processing_options", {})
        
        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file_path is required"
            )
        
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        logger.info(
            "Starting document processing pipeline from file path",
            file_path=file_path,
            options=processing_options
        )
        
        # Start the processing pipeline
        result = await pipeline_service.process_document(
            source_file_path=file_path,
            processing_options=processing_options
        )
        
        logger.info(
            "Document processing pipeline started",
            document_id=result["document_id"],
            file_path=file_path
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Document processing started successfully",
                "data": result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get("/health")
async def health_check(
    pipeline_service: DocumentProcessingPipeline = Depends(get_pipeline_service)
) -> JSONResponse:
    """
    Health check endpoint for the document processing pipeline.
    """
    try:
        # Basic health check - ensure pipeline service is available
        health_status = {
            "status": "healthy",
            "service": "document_processing_pipeline",
            "timestamp": "2024-01-15T10:30:00Z",
            "components": {
                "redis": "connected" if pipeline_service.redis_connection else "disconnected",
                "queues": {
                    "document_converter": "available",
                    "metadata_extractor": "available", 
                    "typesense_indexer": "available",
                    "qdrant_indexer": "available"
                }
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "document_processing_pipeline", 
                "error": str(e),
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ) 