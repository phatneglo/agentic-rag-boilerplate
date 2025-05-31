"""
Simple File Service

Provides basic file upload and signed URL functionality for the /files endpoints.
Uses the existing object_storage_service without interfering with file manager operations.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from fastapi import UploadFile, HTTPException

from app.core.logging_config import get_logger
from app.services.object_storage_service import object_storage_service
from app.utils.exceptions import ObjectStorageError

logger = get_logger(__name__)


class SimpleFileService:
    """Simple service for basic file operations used by /files endpoints."""
    
    def __init__(self):
        self.storage = object_storage_service
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        folder_structure: str = None,
        file_metadata: Dict = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Upload multiple files to object storage.
        
        Args:
            files: List of files to upload
            folder_structure: Optional folder structure (defaults to root)
            file_metadata: Optional metadata (not used in simple implementation)
        
        Returns:
            Tuple of (successful_results, error_dicts)
        """
        results = []
        errors = []
        
        # Use default folder or root
        upload_path = folder_structure or ""
        
        for file in files:
            try:
                # Upload single file using existing method
                result = await self.storage.upload_file(file, upload_path)
                
                # Generate public URL (signed URL with long expiration)
                try:
                    public_url = await self.storage.get_download_url(result["path"], expires_in=86400)  # 24 hours
                except Exception:
                    # Fallback to a generic URL format if signed URL fails
                    public_url = f"https://{self.storage.bucket}.s3.{self.storage.region}.amazonaws.com/{result['path']}"
                
                # Convert to expected format with all required fields
                file_info = {
                    "file_path": result["path"],  # Required: Path in object storage
                    "original_filename": file.filename,  # Required: Original filename
                    "public_url": public_url,  # Required: Public URL to access file
                    "content_type": file.content_type or "application/octet-stream",  # Required: MIME type
                    "size": result["size"],  # Required: File size in bytes
                    "file_metadata": {  # Optional: Additional metadata
                        "original_filename": file.filename,
                        "uploaded_at": datetime.utcnow().isoformat(),
                        "upload_path": upload_path,
                        "size_formatted": result["size_formatted"]
                    }
                }
                results.append(file_info)
                
                logger.info(f"Successfully uploaded file: {file.filename}")
                
            except HTTPException as e:
                error_dict = {
                    "filename": file.filename,
                    "error": e.detail,
                    "status_code": e.status_code,
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_dict)
                logger.error(f"Failed to upload {file.filename}: {e.detail}")
                
            except Exception as e:
                error_dict = {
                    "filename": file.filename,
                    "error": str(e),
                    "status_code": 500,
                    "timestamp": datetime.utcnow().isoformat()
                }
                errors.append(error_dict)
                logger.error(f"Unexpected error uploading {file.filename}: {str(e)}")
        
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