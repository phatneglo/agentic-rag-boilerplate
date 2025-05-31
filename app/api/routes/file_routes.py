"""
File upload and management API routes.
"""
import time
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
import io

from app.core.logging_config import get_logger
from app.models.requests.file_requests import (
    SignedUrlRequest,
)
from app.models.responses.file_responses import (
    MultipleFileUploadResponse,
    SignedUrlResponse,
    FileInfo,
)
from app.services.simple_file_service import simple_file_service
from app.utils.exceptions import (
    ObjectStorageError,
)


# Create router for file upload functionality
upload_router = APIRouter(prefix="/files", tags=["File Upload"])

# Get logger for this module
logger = get_logger(__name__)


@upload_router.post(
    "/upload",
    response_model=MultipleFileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload files",
    description="Upload single or multiple files to object storage with automatic folder organization"
)
async def upload_files(
    files: List[UploadFile] = File(..., description="File(s) to upload")
) -> MultipleFileUploadResponse:
    """Upload single or multiple files to object storage."""
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No files provided"
            )
        
        # Upload files using the simple file service
        results, errors = await simple_file_service.upload_multiple_files(
            files=files,
            folder_structure=None,  # Use default from settings
            file_metadata=None  # No custom metadata
        )
        
        # Convert results to FileInfo models
        file_infos = [FileInfo(**result) for result in results]
        
        successful_uploads = len(file_infos)
        failed_uploads = len(errors)
        
        message = f"{successful_uploads} file{'s' if successful_uploads != 1 else ''} uploaded successfully"
        if failed_uploads > 0:
            message += f", {failed_uploads} failed"
        
        logger.info(
            "Files upload completed",
            total_files=len(files),
            successful=successful_uploads,
            failed=failed_uploads
        )
        
        return MultipleFileUploadResponse(
            message=message,
            files=file_infos,
            total_files=len(files),
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            errors=errors,  # Include error details
            timestamp=time.time()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during file upload", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file upload"
        )


@upload_router.post(
    "/get-signed-url",
    response_model=SignedUrlResponse,
    summary="Generate signed URL",
    description="Generate a signed URL for file access with expiration"
)
async def get_signed_url(
    request: SignedUrlRequest
) -> SignedUrlResponse:
    """Generate a signed URL for file access."""
    try:
        # Generate signed URL using the simple file service
        signed_url = simple_file_service.get_signed_url(
            file_path=request.file_path,
            expiration=request.expiration,
            method=request.method
        )
        
        # Calculate expiration timestamp
        expires_at = datetime.utcnow() + timedelta(seconds=request.expiration)
        
        logger.info(
            "Signed URL generated successfully",
            file_path=request.file_path,
            method=request.method,
            expiration=request.expiration
        )
        
        return SignedUrlResponse(
            file_path=request.file_path,
            signed_url=signed_url,
            method=request.method,
            expiration=request.expiration,
            expires_at=expires_at.isoformat(),
            timestamp=time.time()
        )
        
    except ObjectStorageError as e:
        logger.error("Object storage error during signed URL generation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during signed URL generation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during signed URL generation"
        ) 