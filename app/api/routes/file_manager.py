"""
File Manager API Routes

Provides REST endpoints for file and folder management operations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.security import HTTPBearer
import tempfile
import os
from pathlib import Path

from app.services.file_manager_service import file_manager_service
from app.core.logging_config import get_logger
from app.models.requests.file_manager_requests import (
    CreateFolderRequest,
    RenameItemRequest,
    MoveItemRequest,
    SearchRequest
)
from app.models.responses.file_manager_responses import (
    DirectoryListingResponse,
    FileOperationResponse,
    SearchResponse,
    FileInfoResponse
)

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)

# Create router with prefix and tags
router = APIRouter(prefix="/file-manager", tags=["File Manager"])


@router.get("/", response_model=DirectoryListingResponse)
async def list_directory(
    path: str = Query("", description="Directory path to list"),
    search: str = Query("", description="Search query to filter files")
):
    """
    List directory contents with optional search filtering.
    
    - **path**: Directory path relative to storage root (empty for root)
    - **search**: Optional search query to filter files by name
    """
    try:
        result = await file_manager_service.list_directory(path=path, search=search)
        return DirectoryListingResponse(
            success=True,
            message="Directory listed successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list directory")


@router.post("/folder", response_model=FileOperationResponse)
async def create_folder(request: CreateFolderRequest):
    """
    Create a new folder.
    
    - **path**: Parent directory path
    - **folder_name**: Name of the new folder
    """
    try:
        result = await file_manager_service.create_folder(
            path=request.path,
            folder_name=request.folder_name
        )
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to create folder")


@router.post("/upload", response_model=FileOperationResponse)
async def upload_file(
    path: str = Form("", description="Upload directory path"),
    file: UploadFile = File(..., description="File to upload")
):
    """
    Upload a file to the specified directory.
    
    - **path**: Directory path where file should be uploaded
    - **file**: File to upload
    """
    try:
        result = await file_manager_service.upload_file(path=path, file=file)
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.delete("/item")
async def delete_item(path: str = Query(..., description="Path of item to delete")):
    """
    Delete a file or folder.
    
    - **path**: Path of the item to delete
    """
    try:
        result = await file_manager_service.delete_item(path=path)
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item")


@router.put("/rename", response_model=FileOperationResponse)
async def rename_item(request: RenameItemRequest):
    """
    Rename a file or folder.
    
    - **path**: Current path of the item
    - **new_name**: New name for the item
    """
    try:
        result = await file_manager_service.rename_item(
            path=request.path,
            new_name=request.new_name
        )
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error renaming item: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename item")


@router.put("/move", response_model=FileOperationResponse)
async def move_item(request: MoveItemRequest):
    """
    Move a file or folder to a new location.
    
    - **source_path**: Current path of the item
    - **destination_path**: Destination directory path
    - **new_name**: Optional new name for the item
    """
    try:
        result = await file_manager_service.move_item(
            source_path=request.source_path,
            destination_path=request.destination_path,
            new_name=request.new_name
        )
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error moving item: {e}")
        raise HTTPException(status_code=500, detail="Failed to move item")


@router.get("/download/file")
async def download_file(path: str = Query(..., description="File path to download")):
    """Download a single file."""
    try:
        download_url, mime_type = await file_manager_service.download_file(path)
        
        # For object storage, redirect to the presigned URL
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.get("/download/folder")
async def download_folder(path: str = Query(..., description="Folder path to download as zip")):
    """Download a folder as a zip archive."""
    try:
        # For now, return an error as folder download is not implemented for object storage
        raise HTTPException(status_code=501, detail="Folder download not yet implemented for object storage")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading folder: {e}")
        raise HTTPException(status_code=500, detail="Failed to download folder")


@router.get("/search", response_model=SearchResponse)
async def search_files(
    query: str = Query(..., description="Search query", min_length=2),
    path: str = Query("", description="Directory path to search in")
):
    """
    Search for files and folders.
    
    - **query**: Search query (minimum 2 characters)
    - **path**: Directory path to search in (empty for root)
    """
    try:
        result = await file_manager_service.search_files(query=query, path=path)
        return SearchResponse(
            success=True,
            message="Search completed successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/info", response_model=FileInfoResponse)
async def get_file_info(path: str = Query(..., description="Path of item to get info for")):
    """
    Get detailed information about a file or folder.
    
    - **path**: Path of the item
    """
    try:
        result = await file_manager_service.get_file_info(path=path)
        return FileInfoResponse(
            success=True,
            message="File information retrieved successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file information")


@router.get("/preview")
async def preview_file(path: str = Query(..., description="File path to preview")):
    """
    Preview a file (for images, text files, etc.).
    
    - **path**: Path of the file to preview
    """
    try:
        file_path, mime_type = await file_manager_service.download_file(path=path)
        
        # Check if file is previewable
        previewable_types = [
            "image/", "text/", "application/json", "application/xml",
            "application/pdf"
        ]
        
        if not any(mime_type.startswith(ptype) for ptype in previewable_types):
            raise HTTPException(status_code=400, detail="File type not previewable")
        
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename={file_path.name}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview file")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check endpoint for file manager service."""
    try:
        # Check if storage directory is accessible
        storage_path = Path(file_manager_service.base_path)
        if not storage_path.exists():
            storage_path.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = storage_path / ".health_check"
        test_file.write_text("health_check")
        test_file.unlink()
        
        return {
            "status": "healthy",
            "service": "file_manager",
            "storage_path": str(storage_path),
            "storage_accessible": True
        }
    except Exception as e:
        logger.error(f"File manager health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"File manager service unhealthy: {str(e)}"
        ) 