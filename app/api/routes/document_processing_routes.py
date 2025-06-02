"""
Document Processing API Routes.
Simplified endpoint for the single-worker 4-step document processing pipeline.
"""
import os
import uuid
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger
from app.services.object_storage_service import ObjectStorageService
from app.core.config import settings

# Configure logging
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/document-processing", tags=["Document Processing"])

# Object storage service
object_storage_service = ObjectStorageService()


@router.post("/process")
async def process_document(
    file: UploadFile = File(...)
) -> JSONResponse:
    """
    Process a document through the complete 4-step pipeline:
    1. Document-to-Markdown conversion using Marker
    2. Metadata extraction using LlamaIndex tree summarizer
    3. Typesense indexing with embeddings and content
    4. Qdrant indexing for RAG
    
    The file is uploaded to S3 and processed by a single worker.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.htm']
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
        
        # Reset file pointer for upload
        await file.seek(0)
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Generate unique filename for S3
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        clean_filename = f"{timestamp}_{document_id}_{file.filename}"
        
        # Upload to S3 in documents folder
        s3_path = f"documents/{clean_filename}"
        
        logger.info(f"Uploading file to S3: {file.filename} -> {s3_path}")
        
        # Upload file to S3
        object_storage_service.s3_client.put_object(
            Bucket=object_storage_service.bucket,
            Key=s3_path,
            Body=file_content,
            ContentType=file.content_type or 'application/octet-stream'
        )
        
        logger.info(f"✅ File uploaded to S3: {s3_path}")
        
        # Queue the job
        from bullmq import Queue
        import redis
        
        # Create Redis connection
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Create BullMQ queue
        queue = Queue(
            "document_processing",
            {"connection": {"host": settings.redis_host, "port": settings.redis_port}}
        )
        
        # Job data
        job_data = {
            "document_id": document_id,
            "s3_file_path": s3_path,
            "file_name": file.filename,
            "original_filename": file.filename,
            "file_size": len(file_content),
            "content_type": file.content_type,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add job to queue
        job = await queue.add("process_document", job_data)
        
        # Initialize job status in Redis
        status_key = f"document_processing:{document_id}"
        redis_client.hset(status_key, mapping={
            "document_id": document_id,
            "file_name": file.filename,
            "s3_file_path": s3_path,
            "status": "queued",
            "overall_progress": 0,
            "step_1_status": "queued",
            "step_1_progress": 0,
            "step_2_status": "queued", 
            "step_2_progress": 0,
            "step_3_status": "queued",
            "step_3_progress": 0,
            "step_4_status": "queued",
            "step_4_progress": 0,
            "created_at": datetime.utcnow().isoformat(),
            "job_id": job.id
        })
        
        # Set expiration for status (7 days)
        redis_client.expire(status_key, 7 * 24 * 60 * 60)
        
        logger.info(
            "Document processing pipeline started",
            document_id=document_id,
            filename=file.filename,
            s3_path=s3_path,
            job_id=job.id
        )
        
        result = {
            "document_id": document_id,
            "job_id": job.id,
            "status": "queued",
            "file_name": file.filename,
            "s3_file_path": s3_path,
            "created_at": datetime.utcnow().isoformat(),
            "steps": {
                "convert_document": {"status": "queued", "progress": 0},
                "extract_metadata": {"status": "queued", "progress": 0},
                "index_typesense": {"status": "queued", "progress": 0},
                "index_qdrant": {"status": "queued", "progress": 0}
            }
        }
        
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
async def get_processing_status(document_id: str) -> JSONResponse:
    """
    Get the status of a document processing pipeline.
    """
    try:
        import redis
        
        # Create Redis connection
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Get job status from Redis
        status_key = f"document_processing:{document_id}"
        job_data = redis_client.hgetall(status_key)
        
        if not job_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document processing job not found"
            )
        
        # Parse status data
        status_info = {
            "document_id": document_id,
            "job_id": job_data.get("job_id"),
            "file_name": job_data.get("file_name"),
            "s3_file_path": job_data.get("s3_file_path"),
            "status": job_data.get("status", "unknown"),
            "overall_progress": int(job_data.get("overall_progress", 0)),
            "created_at": job_data.get("created_at"),
            "last_updated": job_data.get("last_updated"),
            "steps": {
                "convert_document": {
                    "status": job_data.get("step_1_status", "queued"),
                    "progress": int(job_data.get("step_1_progress", 0))
                },
                "extract_metadata": {
                    "status": job_data.get("step_2_status", "queued"),
                    "progress": int(job_data.get("step_2_progress", 0))
                },
                "index_typesense": {
                    "status": job_data.get("step_3_status", "queued"),
                    "progress": int(job_data.get("step_3_progress", 0))
                },
                "index_qdrant": {
                    "status": job_data.get("step_4_status", "queued"),
                    "progress": int(job_data.get("step_4_progress", 0))
                }
            }
        }
        
        # Calculate overall progress
        step_progresses = [
            int(job_data.get("step_1_progress", 0)),
            int(job_data.get("step_2_progress", 0)),
            int(job_data.get("step_3_progress", 0)),
            int(job_data.get("step_4_progress", 0))
        ]
        overall_progress = sum(step_progresses) // 4
        status_info["overall_progress"] = overall_progress
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Pipeline status retrieved successfully",
                "data": status_info
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get pipeline status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pipeline status: {str(e)}"
        )


@router.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for document processing service.
    """
    try:
        import redis
        
        # Test Redis connection
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        redis_client.ping()
        
        # Test S3 connection
        object_storage_service.s3_client.head_bucket(Bucket=object_storage_service.bucket)
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "services": {
                    "redis": "connected",
                    "s3": "connected"
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        ) 