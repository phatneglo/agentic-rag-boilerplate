"""
Test API Routes.
Routes for testing worker functionality with file processing.
"""
import time
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging_config import get_logger
from app.services.simple_file_service import simple_file_service
from app.utils.queue_manager import queue_manager


# Configure logging
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/test", tags=["Test Workers"])


@router.post("/worker")
async def test_worker_with_files(
    files: List[UploadFile] = File(..., description="File(s) to process with test worker")
) -> JSONResponse:
    """
    Test worker by uploading files and processing them.
    
    This endpoint:
    1. Uploads files to object storage
    2. Creates a test worker job for each file
    3. Worker downloads file locally, extracts text, and cleans up
    
    Args:
        files: List of files to upload and process
        
    Returns:
        JSONResponse with job information for each file
    """
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        logger.info(
            "Starting test worker with file upload",
            file_count=len(files),
            filenames=[file.filename for file in files]
        )
        
        # Step 1: Upload files to object storage
        results, errors = await simple_file_service.upload_multiple_files(
            files=files,
            folder_structure=None,  # Use default from settings
            file_metadata=None
        )
        
        if errors:
            logger.warning(f"Some files failed to upload: {len(errors)} errors")
        
        # Step 2: Queue test worker jobs for successfully uploaded files
        job_results = []
        
        for file_result in results:
            try:
                # Prepare job data for test worker
                job_data = {
                    "file_path": file_result["file_path"],  # Object storage path
                    "original_filename": file_result["original_filename"],
                    "content_type": file_result["content_type"],
                    "file_size": file_result["size"],
                    "public_url": file_result["public_url"],
                    "created_at": datetime.utcnow().isoformat(),
                    "job_type": "test_file_processing"
                }
                
                # Get Redis client and queue the job
                redis_client = await queue_manager.get_redis_client()
                
                # For simplicity, we'll use a basic job format
                # In a real implementation, you'd use BullMQ
                job_id = f"test_job_{int(time.time() * 1000)}"
                queue_key = f"{settings.queue_names.get('test_worker', 'test:worker')}"
                
                # Add job to Redis queue
                await redis_client.lpush(queue_key, f"{job_id}:{file_result['file_path']}")
                
                job_info = {
                    "job_id": job_id,
                    "queue": queue_key,
                    "file_path": file_result["file_path"],
                    "original_filename": file_result["original_filename"],
                    "status": "queued",
                    "created_at": job_data["created_at"]
                }
                
                job_results.append(job_info)
                
                logger.info(
                    "Queued test worker job",
                    job_id=job_id,
                    file_path=file_result["file_path"],
                    original_filename=file_result["original_filename"]
                )
                
            except Exception as e:
                logger.error(
                    "Failed to queue test worker job",
                    file_path=file_result.get("file_path", "unknown"),
                    error=str(e)
                )
                
                job_results.append({
                    "job_id": None,
                    "file_path": file_result.get("file_path", "unknown"),
                    "original_filename": file_result.get("original_filename", "unknown"),
                    "status": "failed",
                    "error": str(e),
                    "created_at": datetime.utcnow().isoformat()
                })
        
        # Step 3: Prepare response
        successful_jobs = len([job for job in job_results if job["status"] == "queued"])
        failed_jobs = len([job for job in job_results if job["status"] == "failed"])
        
        response_data = {
            "message": f"Test worker jobs created: {successful_jobs} queued, {failed_jobs} failed",
            "total_files": len(files),
            "successful_uploads": len(results),
            "failed_uploads": len(errors),
            "successful_jobs": successful_jobs,
            "failed_jobs": failed_jobs,
            "jobs": job_results,
            "upload_errors": errors,
            "timestamp": time.time()
        }
        
        logger.info(
            "Test worker job creation completed",
            total_files=len(files),
            successful_jobs=successful_jobs,
            failed_jobs=failed_jobs
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Test worker endpoint failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test worker failed: {str(e)}"
        )


@router.get("/worker/status")
async def get_test_worker_status() -> JSONResponse:
    """
    Get the status of the test worker queue.
    
    Returns:
        JSONResponse with queue status information
    """
    try:
        redis_client = await queue_manager.get_redis_client()
        queue_key = f"{settings.queue_names.get('test_worker', 'test:worker')}"
        
        # Get queue length
        queue_length = await redis_client.llen(queue_key)
        
        # Get some recent jobs (if any)
        recent_jobs = []
        if queue_length > 0:
            jobs = await redis_client.lrange(queue_key, 0, 4)  # Get up to 5 most recent
            recent_jobs = [job.decode() if isinstance(job, bytes) else job for job in jobs]
        
        status_data = {
            "queue_name": queue_key,
            "queue_length": queue_length,
            "recent_jobs": recent_jobs,
            "timestamp": time.time()
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=status_data
        )
        
    except Exception as e:
        logger.error("Failed to get test worker status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/health")
async def test_health_check() -> JSONResponse:
    """
    Health check for test endpoints.
    
    Returns:
        JSONResponse with health status
    """
    try:
        # Check Redis connection
        redis_client = await queue_manager.get_redis_client()
        await redis_client.ping()
        
        health_data = {
            "status": "healthy",
            "service": "test_worker_api",
            "redis": "connected",
            "timestamp": time.time()
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_data
        )
        
    except Exception as e:
        logger.error("Test health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "test_worker_api",
                "redis": "disconnected",
                "error": str(e),
                "timestamp": time.time()
            }
        ) 