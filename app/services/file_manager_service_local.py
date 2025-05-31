"""
File Manager Service

Handles all file operations including upload, download, rename, delete, move,
create folders, search, and sharing functionality.
"""

import os
import shutil
import mimetypes
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from fastapi import UploadFile, HTTPException
import aiofiles
import zipfile
import tempfile
from urllib.parse import quote, unquote

from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class FileManagerService:
    """Service for managing files and folders with object storage integration."""
    
    def __init__(self):
        self.base_path = Path(settings.file_storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        self.allowed_extensions = settings.allowed_extensions_list
        
    def _get_safe_path(self, path: str) -> Path:
        """Get safe path within base directory to prevent directory traversal."""
        try:
            # Remove leading slash and normalize path
            clean_path = path.lstrip('/')
            full_path = (self.base_path / clean_path).resolve()
            
            # Ensure path is within base directory
            if not str(full_path).startswith(str(self.base_path.resolve())):
                raise ValueError("Path outside allowed directory")
                
            return full_path
        except Exception as e:
            logger.error(f"Invalid path: {path}, error: {e}")
            raise HTTPException(status_code=400, detail="Invalid path")
    
    def _get_file_info(self, file_path: Path) -> Dict:
        """Get detailed file information."""
        try:
            stat = file_path.stat()
            is_dir = file_path.is_dir()
            
            # Safely get relative path
            try:
                relative_path = file_path.relative_to(self.base_path)
            except ValueError:
                # If file is not within base path, use just the name
                relative_path = file_path.name
            
            return {
                "name": file_path.name,
                "path": str(relative_path),
                "type": "folder" if is_dir else "file",
                "size": 0 if is_dir else stat.st_size,
                "size_formatted": self._format_file_size(0 if is_dir else stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": "" if is_dir else file_path.suffix.lower(),
                "mime_type": "folder" if is_dir else mimetypes.guess_type(str(file_path))[0],
                "is_directory": is_dir,
                "permissions": oct(stat.st_mode)[-3:],
                "icon": self._get_file_icon(file_path, is_dir)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"
    
    def _get_file_icon(self, file_path: Path, is_dir: bool) -> str:
        """Get appropriate FontAwesome icon for file type."""
        if is_dir:
            return "fas fa-folder"
        
        extension = file_path.suffix.lower()
        icon_map = {
            # Images
            '.jpg': 'fas fa-image', '.jpeg': 'fas fa-image', '.png': 'fas fa-image',
            '.gif': 'fas fa-image', '.bmp': 'fas fa-image', '.svg': 'fas fa-image',
            '.webp': 'fas fa-image', '.ico': 'fas fa-image',
            
            # Documents
            '.pdf': 'fas fa-file-pdf', '.doc': 'fas fa-file-word', '.docx': 'fas fa-file-word',
            '.xls': 'fas fa-file-excel', '.xlsx': 'fas fa-file-excel',
            '.ppt': 'fas fa-file-powerpoint', '.pptx': 'fas fa-file-powerpoint',
            '.txt': 'fas fa-file-alt', '.rtf': 'fas fa-file-alt',
            
            # Code files
            '.html': 'fas fa-code', '.css': 'fas fa-code', '.js': 'fas fa-code',
            '.py': 'fas fa-code', '.java': 'fas fa-code', '.cpp': 'fas fa-code',
            '.c': 'fas fa-code', '.php': 'fas fa-code', '.rb': 'fas fa-code',
            '.go': 'fas fa-code', '.rs': 'fas fa-code', '.ts': 'fas fa-code',
            '.json': 'fas fa-code', '.xml': 'fas fa-code', '.yaml': 'fas fa-code',
            '.yml': 'fas fa-code',
            
            # Archives
            '.zip': 'fas fa-file-archive', '.rar': 'fas fa-file-archive',
            '.7z': 'fas fa-file-archive', '.tar': 'fas fa-file-archive',
            '.gz': 'fas fa-file-archive', '.bz2': 'fas fa-file-archive',
            
            # Audio
            '.mp3': 'fas fa-file-audio', '.wav': 'fas fa-file-audio',
            '.flac': 'fas fa-file-audio', '.aac': 'fas fa-file-audio',
            '.ogg': 'fas fa-file-audio', '.m4a': 'fas fa-file-audio',
            
            # Video
            '.mp4': 'fas fa-file-video', '.avi': 'fas fa-file-video',
            '.mkv': 'fas fa-file-video', '.mov': 'fas fa-file-video',
            '.wmv': 'fas fa-file-video', '.flv': 'fas fa-file-video',
            '.webm': 'fas fa-file-video',
        }
        
        return icon_map.get(extension, 'fas fa-file')
    
    async def list_directory(self, path: str = "", search: str = "") -> Dict:
        """List directory contents with optional search."""
        try:
            dir_path = self._get_safe_path(path)
            
            if not dir_path.exists():
                raise HTTPException(status_code=404, detail="Directory not found")
            
            if not dir_path.is_dir():
                raise HTTPException(status_code=400, detail="Path is not a directory")
            
            items = []
            
            # Get all items in directory
            for item in dir_path.iterdir():
                try:
                    file_info = self._get_file_info(item)
                    if file_info:
                        # Apply search filter if provided
                        if not search or search.lower() in file_info["name"].lower():
                            items.append(file_info)
                except Exception as e:
                    logger.warning(f"Skipping item {item}: {e}")
                    continue
            
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
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to list directory")
    
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
    
    async def create_folder(self, path: str, folder_name: str) -> Dict:
        """Create a new folder."""
        try:
            # Validate folder name
            if not folder_name or folder_name.strip() == "":
                raise HTTPException(status_code=400, detail="Folder name cannot be empty")
            
            if any(char in folder_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise HTTPException(status_code=400, detail="Invalid characters in folder name")
            
            parent_path = self._get_safe_path(path)
            new_folder_path = parent_path / folder_name.strip()
            
            if new_folder_path.exists():
                raise HTTPException(status_code=409, detail="Folder already exists")
            
            new_folder_path.mkdir(parents=True)
            
            logger.info(f"Created folder: {new_folder_path}")
            
            return {
                "message": "Folder created successfully",
                "folder_name": folder_name,
                "path": str(new_folder_path.relative_to(self.base_path))
            }
            
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
            
            # Check file extension
            file_ext = Path(file.filename).suffix.lower()
            if self.allowed_extensions and file_ext not in self.allowed_extensions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File type {file_ext} not allowed"
                )
            
            # Check file size
            content = await file.read()
            if len(content) > self.max_file_size:
                raise HTTPException(
                    status_code=413, 
                    detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
                )
            
            # Reset file pointer
            await file.seek(0)
            
            upload_path = self._get_safe_path(path)
            file_path = upload_path / file.filename
            
            # Handle duplicate names
            counter = 1
            original_stem = file_path.stem
            original_suffix = file_path.suffix
            
            while file_path.exists():
                file_path = upload_path / f"{original_stem}_{counter}{original_suffix}"
                counter += 1
            
            # Save file
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            logger.info(f"Uploaded file: {file_path}")
            
            return {
                "message": "File uploaded successfully",
                "filename": file_path.name,
                "path": str(file_path.relative_to(self.base_path)),
                "size": len(content),
                "size_formatted": self._format_file_size(len(content))
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file {file.filename} to {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    async def delete_item(self, path: str) -> Dict:
        """Delete a file or folder."""
        try:
            item_path = self._get_safe_path(path)
            
            if not item_path.exists():
                raise HTTPException(status_code=404, detail="Item not found")
            
            item_name = item_path.name
            is_directory = item_path.is_dir()
            
            if is_directory:
                shutil.rmtree(item_path)
            else:
                item_path.unlink()
            
            logger.info(f"Deleted {'folder' if is_directory else 'file'}: {item_path}")
            
            return {
                "message": f"{'Folder' if is_directory else 'File'} deleted successfully",
                "name": item_name,
                "type": "folder" if is_directory else "file"
            }
            
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
            
            item_path = self._get_safe_path(path)
            
            if not item_path.exists():
                raise HTTPException(status_code=404, detail="Item not found")
            
            new_path = item_path.parent / new_name.strip()
            
            if new_path.exists():
                raise HTTPException(status_code=409, detail="Item with this name already exists")
            
            old_name = item_path.name
            item_path.rename(new_path)
            
            logger.info(f"Renamed {old_name} to {new_name}")
            
            return {
                "message": "Item renamed successfully",
                "old_name": old_name,
                "new_name": new_name,
                "new_path": str(new_path.relative_to(self.base_path))
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error renaming item {path} to {new_name}: {e}")
            raise HTTPException(status_code=500, detail="Failed to rename item")
    
    async def move_item(self, source_path: str, destination_path: str) -> Dict:
        """Move a file or folder to a new location."""
        try:
            source = self._get_safe_path(source_path)
            dest_dir = self._get_safe_path(destination_path)
            
            if not source.exists():
                raise HTTPException(status_code=404, detail="Source item not found")
            
            if not dest_dir.exists() or not dest_dir.is_dir():
                raise HTTPException(status_code=404, detail="Destination directory not found")
            
            dest_path = dest_dir / source.name
            
            if dest_path.exists():
                raise HTTPException(status_code=409, detail="Item already exists in destination")
            
            shutil.move(str(source), str(dest_path))
            
            logger.info(f"Moved {source} to {dest_path}")
            
            return {
                "message": "Item moved successfully",
                "name": source.name,
                "source_path": source_path,
                "destination_path": str(dest_path.relative_to(self.base_path))
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error moving item {source_path} to {destination_path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to move item")
    
    async def download_file(self, path: str) -> Tuple[Path, str]:
        """Get file path and mime type for download."""
        try:
            file_path = self._get_safe_path(path)
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="File not found")
            
            if file_path.is_dir():
                raise HTTPException(status_code=400, detail="Cannot download directory directly")
            
            mime_type = mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
            
            return file_path, mime_type
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error preparing download for {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to prepare download")
    
    async def download_folder(self, path: str) -> Tuple[Path, str]:
        """Create zip archive of folder for download."""
        try:
            folder_path = self._get_safe_path(path)
            
            if not folder_path.exists():
                raise HTTPException(status_code=404, detail="Folder not found")
            
            if not folder_path.is_dir():
                raise HTTPException(status_code=400, detail="Path is not a directory")
            
            # Create temporary zip file
            temp_dir = Path(tempfile.gettempdir())
            zip_name = f"{folder_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            zip_path = temp_dir / zip_name
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(folder_path)
                        zipf.write(file_path, arcname)
            
            return zip_path, 'application/zip'
            
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
            
            search_path = self._get_safe_path(path)
            results = []
            
            query_lower = query.lower().strip()
            
            # Search recursively
            for item in search_path.rglob('*'):
                try:
                    if query_lower in item.name.lower():
                        file_info = self._get_file_info(item)
                        if file_info:
                            # Add relative path from search root
                            file_info["relative_path"] = str(item.relative_to(search_path))
                            results.append(file_info)
                except Exception as e:
                    logger.warning(f"Skipping search result {item}: {e}")
                    continue
            
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
            item_path = self._get_safe_path(path)
            
            if not item_path.exists():
                raise HTTPException(status_code=404, detail="Item not found")
            
            file_info = self._get_file_info(item_path)
            
            if not file_info:
                raise HTTPException(status_code=500, detail="Failed to get file information")
            
            # Add additional details for files
            if not file_info["is_directory"]:
                file_info["checksum"] = await self._calculate_checksum(item_path)
            
            return file_info
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting file info for {path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get file information")
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate MD5 checksum of a file."""
        try:
            hash_md5 = hashlib.md5()
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in self._file_chunks(f):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return ""
    
    async def _file_chunks(self, file, chunk_size: int = 8192):
        """Async generator for file chunks."""
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            yield chunk


# Service instance
file_manager_service = FileManagerService() 