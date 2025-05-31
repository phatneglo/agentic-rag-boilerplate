"""
File upload and management API routes.
"""
import time
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
import io

from app.core.logging_config import get_logger
from app.models.requests.file_requests import (
    SignedUrlRequest,
    FileListRequest,
    FileDeleteRequest,
    FileCopyRequest,
)
from app.models.responses.file_responses import (
    FileUploadResponse,
    MultipleFileUploadResponse,
    SignedUrlResponse,
    FileListResponse,
    FileDeleteResponse,
    FileCopyResponse,
    FileInfoResponse,
    FileInfo,
)
from app.services.object_storage_service import object_storage_service
from app.utils.exceptions import (
    ObjectStorageError,
    FileUploadError,
    FileNotFoundError,
    InvalidFileTypeError,
)


# Create separate routers for different functionalities
upload_router = APIRouter(prefix="/files", tags=["File Upload"])
manager_router = APIRouter(prefix="/file-manager", tags=["File Manager"])

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
        
        # Upload files using default settings - no custom metadata or folder structure
        results = await object_storage_service.upload_multiple_files(
            files=files,
            folder_structure=None,  # Use default from settings
            file_metadata=None  # No custom metadata
        )
        
        # Convert results to FileInfo models
        file_infos = [FileInfo(**result) for result in results]
        
        successful_uploads = len(file_infos)
        failed_uploads = len(files) - successful_uploads
        
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
        # Generate signed URL
        signed_url = object_storage_service.get_signed_url(
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


@manager_router.get(
    "/download/{file_path:path}",
    summary="Download a file",
    description="Download a file from object storage"
)
async def download_file(
    file_path: str
) -> StreamingResponse:
    """Download a file from object storage."""
    try:
        # Download file content
        content = await object_storage_service.download_file(file_path)
        
        # Get file info for content type
        file_info = await object_storage_service.get_file_info(file_path)
        
        # Extract filename from path
        filename = file_path.split('/')[-1]
        
        logger.info(
            "File downloaded successfully",
            file_path=file_path,
            size=len(content)
        )
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=file_info.get('content_type', 'application/octet-stream'),
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(content))
            }
        )
        
    except FileNotFoundError as e:
        logger.error("File not found for download", file_path=file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ObjectStorageError as e:
        logger.error("Object storage error during file download", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during file download", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file download"
        )


@manager_router.get(
    "/list",
    response_model=FileListResponse,
    summary="List files",
    description="List files in object storage with optional prefix filtering"
)
async def list_files(
    prefix: str = "",
    max_files: int = 100
) -> FileListResponse:
    """List files in object storage."""
    try:
        # List files
        files = await object_storage_service.list_files(
            prefix=prefix,
            max_files=max_files
        )
        
        # Convert to FileInfo models
        file_infos = [FileInfo(**file_data) for file_data in files]
        
        logger.info(
            "Files listed successfully",
            prefix=prefix,
            count=len(file_infos),
            max_files=max_files
        )
        
        return FileListResponse(
            files=file_infos,
            total_files=len(file_infos),
            prefix=prefix,
            max_files=max_files,
            timestamp=time.time()
        )
        
    except ObjectStorageError as e:
        logger.error("Object storage error during file listing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during file listing", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file listing"
        )


@manager_router.delete(
    "/{file_path:path}",
    response_model=FileDeleteResponse,
    summary="Delete a file",
    description="Delete a file from object storage"
)
async def delete_file(
    file_path: str
) -> FileDeleteResponse:
    """Delete a file from object storage."""
    try:
        # Delete file
        success = await object_storage_service.delete_file(file_path)
        
        if success:
            logger.info("File deleted successfully", file_path=file_path)
            return FileDeleteResponse(
                message="File deleted successfully",
                file_path=file_path,
                success=True,
                timestamp=time.time()
            )
        else:
            logger.warning("File deletion failed", file_path=file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete file"
            )
        
    except FileNotFoundError as e:
        logger.error("File not found for deletion", file_path=file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ObjectStorageError as e:
        logger.error("Object storage error during file deletion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during file deletion", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file deletion"
        )


@manager_router.post(
    "/copy",
    response_model=FileCopyResponse,
    summary="Copy a file",
    description="Copy a file within object storage"
)
async def copy_file(
    request: FileCopyRequest
) -> FileCopyResponse:
    """Copy a file within object storage."""
    try:
        # Copy file
        success = await object_storage_service.copy_file(
            source_path=request.source_path,
            destination_path=request.destination_path,
            overwrite=request.overwrite
        )
        
        if success:
            logger.info(
                "File copied successfully",
                source_path=request.source_path,
                destination_path=request.destination_path
            )
            return FileCopyResponse(
                message="File copied successfully",
                source_path=request.source_path,
                destination_path=request.destination_path,
                success=True,
                timestamp=time.time()
            )
        else:
            logger.warning(
                "File copy failed",
                source_path=request.source_path,
                destination_path=request.destination_path
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to copy file"
            )
        
    except FileNotFoundError as e:
        logger.error("Source file not found for copy", source_path=request.source_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ObjectStorageError as e:
        logger.error("Object storage error during file copy", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during file copy", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file copy"
        )


@manager_router.get(
    "/info/{file_path:path}",
    response_model=FileInfoResponse,
    summary="Get file information",
    description="Get detailed information about a file in object storage"
)
async def get_file_info(
    file_path: str
) -> FileInfoResponse:
    """Get detailed information about a file."""
    try:
        # Get file info
        file_info = await object_storage_service.get_file_info(file_path)
        
        # Convert to FileInfo model
        file_info_model = FileInfo(**file_info)
        
        logger.info("File info retrieved successfully", file_path=file_path)
        
        return FileInfoResponse(
            file_info=file_info_model,
            timestamp=time.time()
        )
        
    except FileNotFoundError as e:
        logger.error("File not found for info retrieval", file_path=file_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ObjectStorageError as e:
        logger.error("Object storage error during file info retrieval", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: {str(e)}"
        )
    except Exception as e:
        logger.error("Unexpected error during file info retrieval", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during file info retrieval"
        ) 