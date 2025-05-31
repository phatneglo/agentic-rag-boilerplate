"""
File Manager API Routes

Provides REST endpoints for file and folder management operations.
All routes require JWT authentication and operate within user-scoped directories.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Form
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.security import HTTPBearer
import tempfile
import os
from pathlib import Path
import io

from app.services.file_manager_service import file_manager_service
from app.core.logging_config import get_logger
from app.core.jwt_auth import get_current_user, get_user_directory, TokenData
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
router = APIRouter(prefix="/file-manager", tags=["File Manager - Protected"])


@router.get("/", response_model=DirectoryListingResponse)
async def list_directory(
    path: str = Query("", description="Directory path to list"),
    search: str = Query("", description="Search query to filter files"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    List directory contents with optional search filtering.
    
    - **path**: Directory path relative to user's root (empty for user root)
    - **search**: Optional search query to filter files by name
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} listing directory: {path}")
        
        result = await file_manager_service.list_directory(
            user_base_path=user_base_path, 
            relative_path=path, 
            search=search
        )
        return DirectoryListingResponse(
            success=True,
            message="Directory listed successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing directory {path} for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list directory")


@router.post("/folder", response_model=FileOperationResponse)
async def create_folder(
    request: CreateFolderRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new folder.
    
    - **path**: Parent directory path (relative to user's root)
    - **folder_name**: Name of the new folder
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} creating folder: {request.folder_name} in {request.path}")
        
        result = await file_manager_service.create_folder(
            user_base_path=user_base_path,
            relative_path=request.path,
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
        logger.error(f"Error creating folder for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create folder")


@router.post("/upload", response_model=FileOperationResponse)
async def upload_file(
    path: str = Form("", description="Upload directory path"),
    file: UploadFile = File(..., description="File to upload"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Upload a file to the specified directory.
    
    - **path**: Directory path where file should be uploaded (relative to user's root)
    - **file**: File to upload
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} uploading file: {file.filename} to {path}")
        
        result = await file_manager_service.upload_file(
            user_base_path=user_base_path, 
            relative_path=path, 
            file=file
        )
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file")


@router.delete("/item")
async def delete_item(
    path: str = Query(..., description="Path of item to delete"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a file or folder.
    
    - **path**: Path of the item to delete (relative to user's root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} deleting item: {path}")
        
        result = await file_manager_service.delete_item(
            user_base_path=user_base_path, 
            relative_path=path
        )
        return FileOperationResponse(
            success=True,
            message=result["message"],
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting item for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item")


@router.put("/rename", response_model=FileOperationResponse)
async def rename_item(
    request: RenameItemRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Rename a file or folder.
    
    - **path**: Current path of the item (relative to user's root)
    - **new_name**: New name for the item
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} renaming item: {request.path} to {request.new_name}")
        
        result = await file_manager_service.rename_item(
            user_base_path=user_base_path,
            relative_path=request.path,
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
        logger.error(f"Error renaming item for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to rename item")


@router.put("/move", response_model=FileOperationResponse)
async def move_item(
    request: MoveItemRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Move a file or folder to a new location.
    
    - **source_path**: Current path of the item (relative to user's root)
    - **destination_path**: Destination directory path (relative to user's root)
    - **new_name**: Optional new name for the item
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} moving item: {request.source_path} to {request.destination_path}")
        
        result = await file_manager_service.move_item(
            user_base_path=user_base_path,
            source_relative_path=request.source_path,
            destination_relative_path=request.destination_path,
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
        logger.error(f"Error moving item for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to move item")


@router.get("/download/file")
async def download_file(
    path: str = Query(..., description="File path to download"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Download a single file.
    
    - **path**: File path to download (relative to user's root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} downloading file: {path}")
        
        download_url, mime_type = await file_manager_service.download_file(
            user_base_path=user_base_path, 
            relative_path=path
        )
        
        # For object storage, redirect to the presigned URL
        return RedirectResponse(url=download_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.get("/download/folder")
async def download_folder(
    path: str = Query(..., description="Folder path to download as zip"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Download a folder as a zip archive.
    
    - **path**: Folder path to download (relative to user's root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} downloading folder: {path}")
        
        # Create zip file for the folder
        zip_buffer, zip_filename = await file_manager_service.create_folder_zip(
            user_base_path=user_base_path, 
            relative_path=path
        )
        
        # Return the zip file as a streaming response
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading folder for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download folder")


@router.get("/search", response_model=SearchResponse)
async def search_files(
    query: str = Query(..., description="Search query", min_length=2),
    path: str = Query("", description="Directory path to search in"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Search for files and folders.
    
    - **query**: Search query (minimum 2 characters)
    - **path**: Directory path to search in (relative to user's root, empty for user root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} searching for '{query}' in {path}")
        
        result = await file_manager_service.search_files(
            user_base_path=user_base_path, 
            query=query, 
            relative_path=path
        )
        return SearchResponse(
            success=True,
            message="Search completed successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching files for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/info", response_model=FileInfoResponse)
async def get_file_info(
    path: str = Query(..., description="Path of item to get info for"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get detailed information about a file or folder.
    
    - **path**: Path of the item (relative to user's root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} getting info for: {path}")
        
        result = await file_manager_service.get_file_info(
            user_base_path=user_base_path, 
            relative_path=path
        )
        return FileInfoResponse(
            success=True,
            message="File information retrieved successfully",
            data=result
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting file info for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file information")


@router.get("/preview")
async def preview_file(
    path: str = Query(..., description="File path to preview"),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Preview a file (for images, text files, etc.).
    
    - **path**: Path of the file to preview (relative to user's root)
    
    Requires: Bearer JWT token
    """
    try:
        # Get user's base directory
        user_base_path = get_user_directory(current_user)
        
        logger.info(f"User {current_user.username} previewing file: {path}")
        
        file_path, mime_type = await file_manager_service.download_file(
            user_base_path=user_base_path, 
            relative_path=path
        )
        
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
        logger.error(f"Error previewing file for user {current_user.username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to preview file")


# Health check endpoint - no authentication required
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