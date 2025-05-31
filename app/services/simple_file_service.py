"""
Simple File Service

Provides basic file upload and signed URL functionality for the /files endpoints.
Uses the existing object_storage_service without interfering with file manager operations.
"""

import time
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
from fastapi import UploadFile, HTTPException

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.services.object_storage_service import object_storage_service
from app.utils.exceptions import ObjectStorageError

settings = get_settings()
logger = get_logger(__name__)


class SimpleFileService:
    """Simple service for basic file operations used by /files endpoints."""
    
    def __init__(self):
        self.storage = object_storage_service
        self.folder_structure = settings.upload_folder_structure
    
    def _clean_filename(self, filename: str) -> str:
        """
        Clean filename while preserving extension.
        Removes special characters and replaces spaces with underscores.
        """
        if not filename:
            return f"unnamed_{uuid.uuid4().hex[:8]}"
        
        # Get file extension
        path = Path(filename)
        name_part = path.stem
        extension = path.suffix
        
        # Clean the name part
        # Remove or replace special characters
        clean_name = re.sub(r'[^\w\s-]', '', name_part)  # Remove special chars except word chars, spaces, hyphens
        clean_name = re.sub(r'[-\s]+', '_', clean_name)  # Replace spaces and hyphens with underscores
        clean_name = clean_name.strip('_')  # Remove leading/trailing underscores
        
        # Ensure we have a valid name
        if not clean_name:
            clean_name = f"file_{uuid.uuid4().hex[:8]}"
        
        # Add timestamp to make it unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return f"{timestamp}_{clean_name}{extension.lower()}"
    
    def _get_upload_path(self) -> str:
        """Generate upload path based on folder structure setting."""
        now = datetime.now()
        
        if self.folder_structure == "year-month-day":
            date_path = now.strftime("%Y/%m/%d")
        elif self.folder_structure == "year-month":
            date_path = now.strftime("%Y/%m")
        elif self.folder_structure == "year":
            date_path = now.strftime("%Y")
        else:  # flat
            date_path = ""
        
        # Always start with 'uploads' folder
        if date_path:
            return f"uploads/{date_path}"
        else:
            return "uploads"
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        folder_structure: str = None,
        file_metadata: Dict = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Upload multiple files to object storage with organized structure.
        
        Args:
            files: List of files to upload
            folder_structure: Optional override (ignored, uses settings)
            file_metadata: Optional metadata (not used in simple implementation)
        
        Returns:
            Tuple of (successful_results, error_dicts)
        """
        results = []
        errors = []
        
        # Use organized upload path based on settings
        upload_path = self._get_upload_path()
        
        for file in files:
            try:
                # Store original filename
                original_filename = file.filename
                
                # Generate clean filename
                clean_filename = self._clean_filename(original_filename)
                
                # Temporarily change file.filename for upload
                file.filename = clean_filename
                
                # Upload single file using existing method
                result = await self.storage.upload_file(file, upload_path)
                
                # Restore original filename for reference
                file.filename = original_filename
                
                # Generate public URL (signed URL with long expiration)
                try:
                    public_url = await self.storage.get_download_url(result["path"], expires_in=86400)  # 24 hours
                except Exception:
                    # Fallback to a generic URL format if signed URL fails
                    public_url = f"https://{self.storage.bucket}.s3.{self.storage.region}.amazonaws.com/{result['path']}"
                
                # Convert to expected format with all required fields
                file_info = {
                    "file_path": result["path"],  # Required: Path in object storage (with clean filename)
                    "original_filename": original_filename,  # Required: Original filename from user
                    "public_url": public_url,  # Required: Public URL to access file
                    "content_type": file.content_type or "application/octet-stream",  # Required: MIME type
                    "size": result["size"],  # Required: File size in bytes
                    "file_metadata": {  # Optional: Additional metadata
                        "original_filename": original_filename,
                        "clean_filename": clean_filename,
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "upload_path": upload_path,
                        "folder_structure": self.folder_structure,
                        "size_formatted": result["size_formatted"],
                        "content_type": file.content_type or "application/octet-stream"
                    }
                }
                results.append(file_info)
                
                logger.info(
                    f"Successfully uploaded file: {original_filename} -> {result['path']}",
                    original_filename=original_filename,
                    clean_filename=clean_filename,
                    upload_path=upload_path
                )
                
            except HTTPException as e:
                error_dict = {
                    "filename": original_filename,
                    "error": e.detail,
                    "status_code": e.status_code,
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_dict)
                logger.error(f"Failed to upload {original_filename}: {e.detail}")
                
            except Exception as e:
                error_dict = {
                    "filename": original_filename,
                    "error": str(e),
                    "status_code": 500,
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_dict)
                logger.error(f"Unexpected error uploading {original_filename}: {str(e)}")
        
        return results, errors
    
    def get_signed_url(
        self,
        file_path: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> str:
        """
        Generate a signed URL for file access.
        
        Args:
            file_path: Path to the file
            expiration: URL expiration time in seconds
            method: HTTP method (GET, PUT, etc.)
        
        Returns:
            Signed URL string
        """
        try:
            # Use existing download URL method for GET requests
            if method.upper() == "GET":
                # This is synchronous, so we need to handle it differently
                # For now, use the existing get_download_url method
                object_key = self.storage._get_object_key(file_path)
                
                signed_url = self.storage.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.storage.bucket, 'Key': object_key},
                    ExpiresIn=expiration
                )
                
                logger.info(f"Generated signed URL for {file_path}")
                return signed_url
            
            elif method.upper() == "PUT":
                # Generate PUT URL for uploads
                object_key = self.storage._get_object_key(file_path)
                
                signed_url = self.storage.s3_client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': self.storage.bucket, 'Key': object_key},
                    ExpiresIn=expiration
                )
                
                logger.info(f"Generated signed PUT URL for {file_path}")
                return signed_url
            
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
        except Exception as e:
            logger.error(f"Error generating signed URL for {file_path}: {e}")
            raise ObjectStorageError(f"Failed to generate signed URL: {str(e)}")


# Create service instance
simple_file_service = SimpleFileService() 