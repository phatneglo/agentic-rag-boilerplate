"""
File Manager Service with Object Storage

Handles all file operations using object storage (S3, DigitalOcean Spaces, MinIO)
instead of local file storage.
"""

import mimetypes
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import UploadFile, HTTPException

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.object_storage_service import object_storage_service

settings = get_settings()
logger = get_logger(__name__)


class FileManagerService:
    """Service for managing files and folders with object storage integration."""
    
    def __init__(self):
        self.storage = object_storage_service
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = settings.allowed_extensions_list
    
    def _build_breadcrumbs(self, path: str) -> List[Dict]:
        """Build breadcrumb navigation."""
        breadcrumbs = [{"name": "Home", "path": ""}]
        
        if path:
            parts = path.strip('/').split('/')
            current_path = ""
            
            for part in parts:
                if part:
                    current_path = f"{current_path}/{part}" if current_path else part
                    breadcrumbs.append({
                        "name": part,
                        "path": current_path
                    })
        
        return breadcrumbs
    
    async def list_directory(self, path: str = "", search: str = "") -> Dict:
        """List directory contents with optional search."""
        try:
            items = await self.storage.list_objects(prefix=path, search=search)
            
            # Sort: directories first, then files, both alphabetically
            items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
            
            # Build breadcrumb navigation
            breadcrumbs = self._build_breadcrumbs(path)
            
            return {
                "current_path": path,
                "items": items,
                "breadcrumbs": breadcrumbs,
                "total_items": len(items),
                "search_query": search
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to list directory")
    
    async def create_folder(self, path: str, folder_name: str) -> Dict:
        """Create a new folder."""
        try:
            return await self.storage.create_folder(path, folder_name)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating folder {folder_name} in {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder")
    
    async def upload_file(self, path: str, file: UploadFile) -> Dict:
        """Upload a file to the specified path."""
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No file provided")
            
            return await self.storage.upload_file(file, path)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file {file.filename} to {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    async def delete_item(self, path: str) -> Dict:
        """Delete a file or folder."""
        try:
            return await self.storage.delete_object(path)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting item {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete item")
    
    async def rename_item(self, path: str, new_name: str) -> Dict:
        """Rename a file or folder."""
        try:
            if not new_name or new_name.strip() == "":
                raise HTTPException(status_code=400, detail="New name cannot be empty")
            
            if any(char in new_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise HTTPException(status_code=400, detail="Invalid characters in name")
            
            # For object storage, we need to copy the object to new location and delete old one
            # This is a simplified implementation - in production you might want to handle this differently
            
            # Get the parent path
            path_parts = path.split('/')
            parent_path = '/'.join(path_parts[:-1]) if len(path_parts) > 1 else ""
            new_path = f"{parent_path}/{new_name}" if parent_path else new_name
            
            # For now, return an error as rename is complex in object storage
            # In a full implementation, you would copy the object and delete the original
            raise HTTPException(status_code=501, detail="Rename operation not yet implemented for object storage")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error renaming item {path} to {new_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to rename item")
    
    async def move_item(self, source_path: str, destination_path: str) -> Dict:
        """Move a file or folder to a new location."""
        try:
            # For object storage, this would involve copying and deleting
            # This is a simplified implementation
            raise HTTPException(status_code=501, detail="Move operation not yet implemented for object storage")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error moving item {source_path} to {destination_path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to move item")
    
    async def download_file(self, path: str) -> Tuple[str, str]:
        """Get download URL for file."""
        try:
            # Generate presigned URL for download
            download_url = await self.storage.get_download_url(path)
            mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
            
            return download_url, mime_type
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error preparing download for {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to prepare download")
    
    async def download_folder(self, path: str) -> Tuple[Path, str]:
        """Create zip archive of folder for download."""
        try:
            # This is complex for object storage as we need to download all files first
            # For now, return an error
            raise HTTPException(status_code=501, detail="Folder download not yet implemented for object storage")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating zip for folder {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder archive")
    
    async def search_files(self, query: str, path: str = "") -> Dict:
        """Search for files and folders."""
        try:
            if not query or len(query.strip()) < 2:
                raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
            
            # Use the list_objects method with search
            items = await self.storage.list_objects(prefix=path, search=query.strip())
            
            # Filter results that match the search query
            query_lower = query.lower().strip()
            results = []
            
            for item in items:
                if query_lower in item["name"].lower():
                    # Add relative path from search root
                    item["relative_path"] = item["path"]
                    results.append(item)
            
            # Sort results: exact matches first, then directories, then files
            def sort_key(item):
                exact_match = item["name"].lower() == query_lower
                return (not exact_match, not item["is_directory"], item["name"].lower())
            
            results.sort(key=sort_key)
            
            return {
                "query": query,
                "search_path": path,
                "results": results,
                "total_results": len(results)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error searching for '{query}' in {path}: {e}")
            raise HTTPException(status_code=500, detail="Search failed")
    
    async def get_file_info(self, path: str) -> Dict:
        """Get detailed information about a file or folder."""
        try:
            return await self.storage.get_object_info(path)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get file information")


# Service instance
file_manager_service = FileManagerService() 