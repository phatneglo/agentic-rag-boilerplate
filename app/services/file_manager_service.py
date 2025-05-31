"""
File Manager Service with Object Storage and User-Scoped Paths

Handles all file operations using object storage (S3, DigitalOcean Spaces, MinIO)
with user-scoped directory isolation. Frontend sees relative paths while backend 
works with user-specific absolute paths.
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
    """Service for managing files and folders with object storage integration and user-scoped paths."""
    
    def __init__(self):
        self.storage = object_storage_service
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = settings.allowed_extensions_list
    
    def _get_absolute_path(self, user_base_path: str, relative_path: str) -> str:
        """
        Convert relative path (from frontend) to absolute path (for storage).
        
        Args:
            user_base_path: User's base directory (e.g., "user-files/user123")
            relative_path: Path relative to user's directory (e.g., "folder1/file.txt")
        
        Returns:
            Absolute path for storage (e.g., "user-files/user123/folder1/file.txt")
        """
        if not relative_path or relative_path == "":
            return user_base_path
        
        # Remove leading slash if present
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]
        
        return f"{user_base_path}/{relative_path}"
    
    def _get_relative_path(self, user_base_path: str, absolute_path: str) -> str:
        """
        Convert absolute path (from storage) to relative path (for frontend).
        
        Args:
            user_base_path: User's base directory (e.g., "user-files/user123")
            absolute_path: Absolute path from storage (e.g., "user-files/user123/folder1/file.txt")
        
        Returns:
            Relative path for frontend (e.g., "folder1/file.txt")
        """
        if not absolute_path.startswith(user_base_path):
            return absolute_path
        
        # Remove user base path prefix
        relative = absolute_path[len(user_base_path):].strip('/')
        return relative
    
    def _build_breadcrumbs(self, relative_path: str) -> List[Dict]:
        """Build breadcrumb navigation using relative paths (frontend perspective)."""
        breadcrumbs = [{"name": "Home", "path": ""}]
        
        if relative_path:
            parts = relative_path.strip('/').split('/')
            current_path = ""
            
            for part in parts:
                if part:
                    current_path = f"{current_path}/{part}" if current_path else part
                    breadcrumbs.append({
                        "name": part,
                        "path": current_path
                    })
        
        return breadcrumbs
    
    def _convert_item_paths_to_relative(self, items: List[Dict], user_base_path: str) -> List[Dict]:
        """Convert item paths from absolute to relative for frontend display."""
        converted_items = []
        
        for item in items:
            converted_item = item.copy()
            # Convert the path to relative
            converted_item["path"] = self._get_relative_path(user_base_path, item["path"])
            converted_items.append(converted_item)
        
        return converted_items
    
    async def list_directory(self, user_base_path: str, relative_path: str = "", search: str = "") -> Dict:
        """
        List directory contents with optional search.
        
        Args:
            user_base_path: User's base directory (e.g., "user-files/user123")
            relative_path: Path relative to user's directory (e.g., "folder1")
            search: Optional search query
        """
        try:
            # Convert relative path to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            logger.debug(f"Listing directory: relative='{relative_path}' -> absolute='{absolute_path}'")
            
            # Get items from storage using absolute path
            items = await self.storage.list_objects(prefix=absolute_path, search=search)
            
            # Convert item paths back to relative paths for frontend
            relative_items = self._convert_item_paths_to_relative(items, user_base_path)
            
            # Sort: directories first, then files, both alphabetically
            relative_items.sort(key=lambda x: (not x["is_directory"], x["name"].lower()))
            
            # Build breadcrumb navigation using relative path
            breadcrumbs = self._build_breadcrumbs(relative_path)
            
            return {
                "current_path": relative_path,  # Return relative path to frontend
                "items": relative_items,        # Items with relative paths
                "breadcrumbs": breadcrumbs,     # Breadcrumbs with relative paths
                "total_items": len(relative_items),
                "search_query": search
            }
            
        except Exception as e:
            logger.error(f"Error listing directory {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to list directory")
    
    async def create_folder(self, user_base_path: str, relative_path: str, folder_name: str) -> Dict:
        """
        Create a new folder.
        
        Args:
            user_base_path: User's base directory
            relative_path: Path relative to user's directory where folder should be created
            folder_name: Name of the new folder
        """
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            logger.debug(f"Creating folder '{folder_name}' in: relative='{relative_path}' -> absolute='{absolute_path}'")
            
            result = await self.storage.create_folder(absolute_path, folder_name)
            
            # Convert result paths back to relative if needed
            if "path" in result:
                result["path"] = self._get_relative_path(user_base_path, result["path"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating folder {folder_name} in {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder")
    
    async def upload_file(self, user_base_path: str, relative_path: str, file: UploadFile) -> Dict:
        """
        Upload a file to the specified path.
        
        Args:
            user_base_path: User's base directory
            relative_path: Path relative to user's directory where file should be uploaded
            file: File to upload
        """
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No file provided")
            
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            logger.debug(f"Uploading file '{file.filename}' to: relative='{relative_path}' -> absolute='{absolute_path}'")
            
            result = await self.storage.upload_file(file, absolute_path)
            
            # Convert result paths back to relative if needed
            if "path" in result:
                result["path"] = self._get_relative_path(user_base_path, result["path"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file {file.filename} to {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    async def delete_item(self, user_base_path: str, relative_path: str) -> Dict:
        """
        Delete a file or folder.
        
        Args:
            user_base_path: User's base directory
            relative_path: Path relative to user's directory of item to delete
        """
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            logger.debug(f"Deleting item: relative='{relative_path}' -> absolute='{absolute_path}'")
            
            return await self.storage.delete_object(absolute_path)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting item {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to delete item")
    
    async def rename_item(self, user_base_path: str, relative_path: str, new_name: str) -> Dict:
        """Rename a file or folder by copying to new location and deleting original."""
        try:
            if not new_name or new_name.strip() == "":
                raise HTTPException(status_code=400, detail="New name cannot be empty")
            
            if any(char in new_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise HTTPException(status_code=400, detail="Invalid characters in name")
            
            # Convert to absolute paths
            absolute_source_path = self._get_absolute_path(user_base_path, relative_path)
            absolute_new_path = self._get_absolute_path(user_base_path, new_name)
            
            # Check if new name already exists
            if await self.storage._object_exists(self.storage._get_object_key(absolute_new_path)):
                raise HTTPException(status_code=409, detail="Item with this name already exists")
            
            # For files: copy and delete
            if not relative_path.endswith('/'):
                # Copy file to new location
                copy_source = {'Bucket': self.storage.bucket, 'Key': self.storage._get_object_key(absolute_source_path)}
                self.storage.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.storage.bucket,
                    Key=self.storage._get_object_key(absolute_new_path)
                )
                
                # Delete original file
                await self.storage.delete_object(absolute_source_path)
            else:
                # For folders: copy all objects with the prefix
                old_prefix = self.storage._get_object_key(absolute_source_path)
                new_prefix = self.storage._get_object_key(absolute_new_path) + '/'
                
                # List all objects with the old prefix
                paginator = self.storage.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.storage.bucket, Prefix=old_prefix)
                
                objects_to_copy = []
                for page in pages:
                    for obj in page.get('Contents', []):
                        objects_to_copy.append(obj['Key'])
                
                # Copy each object to new location
                for old_key in objects_to_copy:
                    new_key = old_key.replace(old_prefix, new_prefix, 1)
                    copy_source = {'Bucket': self.storage.bucket, 'Key': old_key}
                    self.storage.s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=self.storage.bucket,
                        Key=new_key
                    )
                
                # Delete all original objects
                if objects_to_copy:
                    delete_objects = [{'Key': key} for key in objects_to_copy]
                    self.storage.s3_client.delete_objects(
                        Bucket=self.storage.bucket,
                        Delete={'Objects': delete_objects}
                    )
            
            logger.info(f"Renamed {relative_path} to {new_name}")
            
            return {
                "message": "Item renamed successfully",
                "old_name": relative_path.split('/')[-1],
                "new_name": new_name,
                "new_path": new_name
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error renaming item {relative_path} to {new_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to rename item")
    
    async def move_item(self, user_base_path: str, source_relative_path: str, destination_relative_path: str, new_name: Optional[str] = None) -> Dict:
        """Move a file or folder to a new location by copying and deleting."""
        try:
            # Convert to absolute paths
            absolute_source_path = self._get_absolute_path(user_base_path, source_relative_path)
            absolute_destination_path = self._get_absolute_path(user_base_path, destination_relative_path)
            
            # Get source item name
            source_parts = source_relative_path.split('/')
            item_name = source_parts[-1]
            
            # Use new name if provided, otherwise keep original name
            final_name = new_name if new_name else item_name
            
            # Create destination path
            dest_relative_path = f"{destination_relative_path}/{final_name}" if destination_relative_path else final_name
            absolute_dest_path = self._get_absolute_path(user_base_path, dest_relative_path)
            
            # Check if destination already exists
            if await self.storage._object_exists(self.storage._get_object_key(absolute_dest_path)):
                raise HTTPException(status_code=409, detail="Item already exists in destination")
            
            # For files: copy and delete
            if not source_relative_path.endswith('/'):
                # Copy file to new location
                copy_source = {'Bucket': self.storage.bucket, 'Key': self.storage._get_object_key(absolute_source_path)}
                self.storage.s3_client.copy_object(
                    CopySource=copy_source,
                    Bucket=self.storage.bucket,
                    Key=self.storage._get_object_key(absolute_dest_path)
                )
                
                # Delete original file
                await self.storage.delete_object(absolute_source_path)
            else:
                # For folders: copy all objects with the prefix
                old_prefix = self.storage._get_object_key(absolute_source_path)
                new_prefix = self.storage._get_object_key(absolute_dest_path) + '/'
                
                # List all objects with the old prefix
                paginator = self.storage.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.storage.bucket, Prefix=old_prefix)
                
                objects_to_copy = []
                for page in pages:
                    for obj in page.get('Contents', []):
                        objects_to_copy.append(obj['Key'])
                
                # Copy each object to new location
                for old_key in objects_to_copy:
                    new_key = old_key.replace(old_prefix, new_prefix, 1)
                    copy_source = {'Bucket': self.storage.bucket, 'Key': old_key}
                    self.storage.s3_client.copy_object(
                        CopySource=copy_source,
                        Bucket=self.storage.bucket,
                        Key=new_key
                    )
                
                # Delete all original objects
                if objects_to_copy:
                    delete_objects = [{'Key': key} for key in objects_to_copy]
                    self.storage.s3_client.delete_objects(
                        Bucket=self.storage.bucket,
                        Delete={'Objects': delete_objects}
                    )
            
            logger.info(f"Moved {source_relative_path} to {dest_relative_path}")
            
            return {
                "message": "Item moved successfully",
                "name": final_name,
                "source_path": source_relative_path,
                "destination_path": dest_relative_path
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error moving item {source_relative_path} to {destination_relative_path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to move item")
    
    async def download_file(self, user_base_path: str, relative_path: str) -> Tuple[str, str]:
        """Get download URL for a file."""
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            download_url = await self.storage.get_download_url(absolute_path)
            
            # Get file info to determine MIME type
            file_info = await self.storage.get_object_info(absolute_path)
            mime_type = file_info.get('mime_type', 'application/octet-stream')
            
            return download_url, mime_type
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting download URL for {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to get download URL")
    
    async def create_folder_zip(self, user_base_path: str, relative_path: str) -> Tuple:
        """Create a zip file containing all files in a folder."""
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            return await self.storage.create_folder_zip(absolute_path)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating zip for folder {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder zip")
    
    async def download_folder(self, user_base_path: str, relative_path: str) -> Tuple[Path, str]:
        """Create zip archive of folder for download."""
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            # This is complex for object storage as we need to download all files first
            # For now, return an error
            raise HTTPException(status_code=501, detail="Folder download not yet implemented for object storage")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating zip for folder {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder archive")
    
    async def search_files(self, user_base_path: str, query: str, relative_path: str = "") -> Dict:
        """Search for files and folders."""
        try:
            if not query or len(query.strip()) < 2:
                raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
            
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            # Use the list_objects method with search
            items = await self.storage.list_objects(prefix=absolute_path, search=query.strip())
            
            # Convert item paths back to relative paths for frontend
            relative_items = self._convert_item_paths_to_relative(items, user_base_path)
            
            # Filter results that match the search query (case-insensitive)
            query_lower = query.strip().lower()
            results = [
                item for item in relative_items
                if query_lower in item["name"].lower()
            ]
            
            def sort_key(item):
                name_lower = item["name"].lower()
                query_lower_stripped = query_lower
                
                # Exact match gets highest priority
                if name_lower == query_lower_stripped:
                    return (0, name_lower)
                # Starts with query gets second priority
                elif name_lower.startswith(query_lower_stripped):
                    return (1, name_lower)
                # Contains query gets third priority
                else:
                    return (2, name_lower)
            
            # Sort results by relevance
            results.sort(key=sort_key)
            
            return {
                "query": query,
                "search_path": relative_path,  # Return relative path
                "results": results,            # Results with relative paths
                "total_results": len(results)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error searching for '{query}' in {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Search failed")
    
    async def get_file_info(self, user_base_path: str, relative_path: str) -> Dict:
        """Get detailed information about a file or folder."""
        try:
            # Convert to absolute path for storage
            absolute_path = self._get_absolute_path(user_base_path, relative_path)
            
            return await self.storage.get_object_info(absolute_path)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {relative_path} (user: {user_base_path}): {e}")
            raise HTTPException(status_code=500, detail="Failed to get file information")


# Service instance
file_manager_service = FileManagerService() 