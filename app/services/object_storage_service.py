"""
Object Storage Service

Handles file operations with various object storage providers (S3, DigitalOcean Spaces, MinIO).
"""

import os
import io
import mimetypes
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, BinaryIO
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile

from app.core.config import get_settings
from app.core.logging_config import get_logger

settings = get_settings()
logger = get_logger(__name__)


class ObjectStorageService:
    """Service for managing files in object storage."""
    
    def __init__(self):
        self.provider = settings.object_storage_provider
        self.bucket = settings.object_storage_bucket
        self.region = settings.object_storage_region
        self.access_key = settings.object_storage_access_key
        self.secret_key = settings.object_storage_secret_key
        self.endpoint_url = settings.object_storage_endpoint_url
        self.public_url = settings.object_storage_public_url
        
        # Initialize S3 client
        self.s3_client = self._init_s3_client()
        
        # Validate configuration
        self._validate_config()
    
    def _init_s3_client(self):
        """Initialize S3 client based on provider."""
        try:
            session = boto3.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region
            )
            
            # Configure endpoint based on provider
            if self.provider == 'digitalocean':
                endpoint_url = self.endpoint_url or f"https://{self.region}.digitaloceanspaces.com"
            elif self.provider == 'minio':
                endpoint_url = self.endpoint_url or "http://localhost:9000"
            else:  # s3
                endpoint_url = self.endpoint_url
            
            return session.client(
                's3',
                endpoint_url=endpoint_url,
                config=boto3.session.Config(signature_version='s3v4')
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise HTTPException(status_code=500, detail="Object storage configuration error")
    
    def _validate_config(self):
        """Validate object storage configuration."""
        if not self.bucket:
            raise HTTPException(status_code=500, detail="Object storage bucket not configured")
        
        if not self.access_key or not self.secret_key:
            raise HTTPException(status_code=500, detail="Object storage credentials not configured")
        
        try:
            # Test connection by listing bucket
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise HTTPException(status_code=500, detail=f"Bucket '{self.bucket}' not found")
            elif error_code == '403':
                raise HTTPException(status_code=500, detail="Access denied to bucket")
            else:
                raise HTTPException(status_code=500, detail=f"Bucket access error: {error_code}")
        except NoCredentialsError:
            raise HTTPException(status_code=500, detail="Invalid object storage credentials")
        except Exception as e:
            logger.error(f"Object storage validation failed: {e}")
            raise HTTPException(status_code=500, detail="Object storage connection failed")
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path for object storage (no leading slash)."""
        return path.lstrip('/').replace('\\', '/')
    
    def _get_object_key(self, path: str) -> str:
        """Get object key from path."""
        return self._normalize_path(path)
    
    async def list_objects(self, prefix: str = "", search: str = "") -> List[Dict]:
        """List objects in bucket with optional prefix and search."""
        try:
            prefix = self._normalize_path(prefix)
            if prefix and not prefix.endswith('/'):
                prefix += '/'
            
            # List objects
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                Delimiter='/'
            )
            
            items = []
            
            for page in pages:
                # Add folders (common prefixes)
                for prefix_info in page.get('CommonPrefixes', []):
                    folder_path = prefix_info['Prefix'].rstrip('/')
                    folder_name = folder_path.split('/')[-1]
                    
                    if not search or search.lower() in folder_name.lower():
                        items.append({
                            "name": folder_name,
                            "path": folder_path,
                            "type": "folder",
                            "size": 0,
                            "size_formatted": "0 B",
                            "modified": datetime.now().isoformat(),
                            "extension": "",
                            "mime_type": "folder",
                            "is_directory": True,
                            "permissions": "755",
                            "icon": "fas fa-folder"
                        })
                
                # Add files
                for obj in page.get('Contents', []):
                    # Skip the prefix itself
                    if obj['Key'] == prefix:
                        continue
                    
                    # Only include direct children (not nested)
                    relative_key = obj['Key'][len(prefix):]
                    if '/' in relative_key:
                        continue
                    
                    file_name = relative_key
                    if not search or search.lower() in file_name.lower():
                        file_info = self._get_file_info_from_object(obj, obj['Key'])
                        items.append(file_info)
            
            return items
            
        except Exception as e:
            logger.error(f"Error listing objects: {e}")
            raise HTTPException(status_code=500, detail="Failed to list files")
    
    def _get_file_info_from_object(self, obj: Dict, key: str) -> Dict:
        """Convert S3 object to file info."""
        file_name = key.split('/')[-1]
        file_path = Path(file_name)
        
        return {
            "name": file_name,
            "path": key,
            "type": "file",
            "size": obj['Size'],
            "size_formatted": self._format_file_size(obj['Size']),
            "modified": obj['LastModified'].isoformat(),
            "extension": file_path.suffix.lower(),
            "mime_type": mimetypes.guess_type(file_name)[0],
            "is_directory": False,
            "permissions": "644",
            "icon": self._get_file_icon(file_path.suffix.lower())
        }
    
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
    
    def _get_file_icon(self, extension: str) -> str:
        """Get appropriate FontAwesome icon for file type."""
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
    
    async def upload_file(self, file: UploadFile, path: str) -> Dict:
        """Upload file to object storage."""
        try:
            # Read file content
            content = await file.read()
            
            # Validate file size
            max_size = settings.max_file_size_mb * 1024 * 1024
            if len(content) > max_size:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {settings.max_file_size_mb}MB"
                )
            
            # Validate file extension
            file_ext = Path(file.filename).suffix.lower()
            if settings.allowed_extensions_list and file_ext not in settings.allowed_extensions_list:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type {file_ext} not allowed"
                )
            
            # Generate object key
            object_key = self._get_object_key(f"{path}/{file.filename}" if path else file.filename)
            
            # Check if file already exists and generate unique name
            counter = 1
            original_key = object_key
            while await self._object_exists(object_key):
                name_parts = Path(original_key)
                object_key = f"{name_parts.parent}/{name_parts.stem}_{counter}{name_parts.suffix}"
                counter += 1
            
            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=content,
                ContentType=file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
            )
            
            logger.info(f"Uploaded file to object storage: {object_key}")
            
            return {
                "message": "File uploaded successfully",
                "filename": object_key.split('/')[-1],
                "path": object_key,
                "size": len(content),
                "size_formatted": self._format_file_size(len(content))
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading file to object storage: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload file")
    
    async def _object_exists(self, key: str) -> bool:
        """Check if object exists in bucket."""
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    async def delete_object(self, path: str) -> Dict:
        """Delete object from storage."""
        try:
            object_key = self._get_object_key(path)
            
            # Check if it's a folder (ends with /)
            if path.endswith('/'):
                # Delete all objects with this prefix
                objects_to_delete = []
                paginator = self.s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=self.bucket, Prefix=object_key)
                
                for page in pages:
                    for obj in page.get('Contents', []):
                        objects_to_delete.append({'Key': obj['Key']})
                
                if objects_to_delete:
                    self.s3_client.delete_objects(
                        Bucket=self.bucket,
                        Delete={'Objects': objects_to_delete}
                    )
                
                return {
                    "message": "Folder deleted successfully",
                    "name": path.rstrip('/').split('/')[-1],
                    "type": "folder"
                }
            else:
                # Delete single file
                self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
                
                return {
                    "message": "File deleted successfully",
                    "name": object_key.split('/')[-1],
                    "type": "file"
                }
                
        except Exception as e:
            logger.error(f"Error deleting object: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete item")
    
    async def create_folder(self, path: str, folder_name: str) -> Dict:
        """Create a folder (empty object with trailing slash)."""
        try:
            # Validate folder name
            if not folder_name or folder_name.strip() == "":
                raise HTTPException(status_code=400, detail="Folder name cannot be empty")
            
            if any(char in folder_name for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise HTTPException(status_code=400, detail="Invalid characters in folder name")
            
            # Create folder key
            folder_path = f"{path}/{folder_name}" if path else folder_name
            folder_key = self._get_object_key(folder_path) + '/'
            
            # Check if folder already exists
            if await self._object_exists(folder_key):
                raise HTTPException(status_code=409, detail="Folder already exists")
            
            # Create empty object to represent folder
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=folder_key,
                Body=b'',
                ContentType='application/x-directory'
            )
            
            logger.info(f"Created folder in object storage: {folder_key}")
            
            return {
                "message": "Folder created successfully",
                "folder_name": folder_name,
                "path": folder_key.rstrip('/')
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating folder: {e}")
            raise HTTPException(status_code=500, detail="Failed to create folder")
    
    async def get_download_url(self, path: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for file download."""
        try:
            object_key = self._get_object_key(path)
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': object_key},
                ExpiresIn=expires_in
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating download URL: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate download URL")
    
    async def get_object_info(self, path: str) -> Dict:
        """Get object information."""
        try:
            object_key = self._get_object_key(path)
            
            response = self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            
            file_name = object_key.split('/')[-1]
            file_path = Path(file_name)
            
            return {
                "name": file_name,
                "path": object_key,
                "type": "file",
                "size": response['ContentLength'],
                "size_formatted": self._format_file_size(response['ContentLength']),
                "modified": response['LastModified'].isoformat(),
                "extension": file_path.suffix.lower(),
                "mime_type": response.get('ContentType'),
                "is_directory": False,
                "permissions": "644",
                "icon": self._get_file_icon(file_path.suffix.lower()),
                "etag": response['ETag'].strip('"')
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise HTTPException(status_code=404, detail="File not found")
            raise HTTPException(status_code=500, detail="Failed to get file info")
        except Exception as e:
            logger.error(f"Error getting object info: {e}")
            raise HTTPException(status_code=500, detail="Failed to get file information")


# Service instance
object_storage_service = ObjectStorageService() 