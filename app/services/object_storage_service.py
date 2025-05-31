"""
Object Storage Service
Provides unified interface for S3, DigitalOcean Spaces, and MinIO.
"""
import asyncio
import mimetypes
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse
import uuid

import aiofiles
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import UploadFile

from app.core.config import settings
from app.core.logging_config import LoggerMixin
from app.utils.exceptions import (
    ObjectStorageError,
    FileUploadError,
    FileNotFoundError,
    InvalidFileTypeError,
)


class ObjectStorageService(LoggerMixin):
    """Unified object storage service supporting S3, DigitalOcean Spaces, and MinIO."""
    
    def __init__(self):
        self._client = None
        self._bucket_name = settings.object_storage_bucket
        self._provider = settings.object_storage_provider.lower()
        self._public_url_base = settings.object_storage_public_url
        
    def _get_client(self):
        """Get or create S3-compatible client."""
        if self._client is None:
            try:
                # Configure client based on provider
                client_config = Config(
                    signature_version='s3v4',
                    region_name=settings.object_storage_region,
                    retries={'max_attempts': 3, 'mode': 'adaptive'}
                )
                
                # Set endpoint URL for non-AWS providers
                endpoint_url = None
                if self._provider == 'digitalocean':
                    endpoint_url = settings.object_storage_endpoint_url or f"https://{settings.object_storage_region}.digitaloceanspaces.com"
                elif self._provider == 'minio':
                    endpoint_url = settings.object_storage_endpoint_url or "http://localhost:9000"
                elif self._provider == 's3' and settings.object_storage_endpoint_url:
                    endpoint_url = settings.object_storage_endpoint_url
                
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=settings.object_storage_access_key,
                    aws_secret_access_key=settings.object_storage_secret_key,
                    endpoint_url=endpoint_url,
                    config=client_config
                )
                
                self.logger.info(
                    "Object storage client initialized",
                    provider=self._provider,
                    bucket=self._bucket_name,
                    region=settings.object_storage_region
                )
                
            except NoCredentialsError:
                raise ObjectStorageError("Object storage credentials not configured")
            except Exception as e:
                raise ObjectStorageError(f"Failed to initialize object storage client: {e}")
        
        return self._client
    
    def _generate_file_path(self, original_filename: str, folder_structure: Optional[str] = None) -> str:
        """Generate file path with timestamp and folder structure."""
        now = datetime.utcnow()
        
        # Extract file extension
        _, ext = os.path.splitext(original_filename)
        
        # Generate unique filename with timestamp
        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}{ext}"
        
        # Create folder structure
        folder_structure = folder_structure or settings.upload_folder_structure
        
        if folder_structure == "year-month-day":
            folder = now.strftime("%Y/%m/%d")
        elif folder_structure == "year-month":
            folder = now.strftime("%Y/%m")
        elif folder_structure == "year":
            folder = now.strftime("%Y")
        else:  # flat
            folder = ""
        
        if folder:
            return f"{folder}/{filename}"
        return filename
    
    def _validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file."""
        # Check file extension
        if file.filename:
            _, ext = os.path.splitext(file.filename.lower())
            if ext not in settings.allowed_extensions_list:
                raise InvalidFileTypeError(
                    f"File type {ext} not allowed. Allowed types: {', '.join(settings.allowed_extensions_list)}"
                )
        
        # Check file size (if available)
        if hasattr(file, 'size') and file.size:
            if file.size > settings.max_file_size_bytes:
                raise FileUploadError(
                    f"File size {file.size} bytes exceeds maximum allowed size {settings.max_file_size_bytes} bytes"
                )
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type for file."""
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
    
    async def upload_file(
        self,
        file: UploadFile,
        folder_structure: Optional[str] = None,
        file_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Upload a single file to object storage.
        
        Args:
            file: FastAPI UploadFile object
            folder_structure: Override default folder structure
            file_metadata: Additional metadata to store with file
            
        Returns:
            Dict containing file information
        """
        try:
            # Validate file
            self._validate_file(file)
            
            # Generate file path
            file_path = self._generate_file_path(file.filename, folder_structure)
            
            # Prepare metadata
            storage_metadata = {
                'original_filename': file.filename or 'unknown',
                'upload_timestamp': datetime.utcnow().isoformat(),
                'content_type': self._get_content_type(file.filename or ''),
            }
            if file_metadata:
                storage_metadata.update(file_metadata)
            
            # Read file content
            content = await file.read()
            
            # Upload to storage
            client = self._get_client()
            
            upload_args = {
                'Bucket': self._bucket_name,
                'Key': file_path,
                'Body': content,
                'ContentType': storage_metadata['content_type'],
                'Metadata': storage_metadata
            }
            
            # Set ACL for public read if supported
            if self._provider in ['s3', 'digitalocean']:
                upload_args['ACL'] = 'public-read'
            
            client.put_object(**upload_args)
            
            # Generate public URL
            public_url = self._generate_public_url(file_path)
            
            result = {
                'file_path': file_path,
                'original_filename': file.filename,
                'public_url': public_url,
                'content_type': storage_metadata['content_type'],
                'size': len(content),
                'file_metadata': storage_metadata
            }
            
            self.logger.info(
                "File uploaded successfully",
                file_path=file_path,
                original_filename=file.filename,
                size=len(content)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "File upload failed",
                filename=file.filename,
                error=str(e)
            )
            if isinstance(e, (ObjectStorageError, FileUploadError, InvalidFileTypeError)):
                raise
            raise FileUploadError(f"Upload failed: {e}")
    
    async def upload_multiple_files(
        self,
        files: List[UploadFile],
        folder_structure: Optional[str] = None,
        file_metadata: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple files to object storage.
        
        Args:
            files: List of FastAPI UploadFile objects
            folder_structure: Override default folder structure
            file_metadata: Additional metadata to store with files
            
        Returns:
            List of dictionaries containing file information
        """
        results = []
        errors = []
        
        for i, file in enumerate(files):
            try:
                result = await self.upload_file(file, folder_structure, file_metadata)
                results.append(result)
            except Exception as e:
                error_info = {
                    'index': i,
                    'filename': file.filename,
                    'error': str(e)
                }
                errors.append(error_info)
                self.logger.error(
                    "Failed to upload file in batch",
                    index=i,
                    filename=file.filename,
                    error=str(e)
                )
        
        if errors:
            self.logger.warning(
                "Some files failed to upload",
                total_files=len(files),
                successful=len(results),
                failed=len(errors)
            )
        
        return results
    
    async def download_file(self, file_path: str) -> bytes:
        """
        Download file from object storage.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            File content as bytes
        """
        try:
            client = self._get_client()
            
            response = client.get_object(Bucket=self._bucket_name, Key=file_path)
            content = response['Body'].read()
            
            self.logger.info(
                "File downloaded successfully",
                file_path=file_path,
                size=len(content)
            )
            
            return content
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {file_path}")
            raise ObjectStorageError(f"Download failed: {e}")
        except Exception as e:
            raise ObjectStorageError(f"Download failed: {e}")
    
    def get_signed_url(
        self,
        file_path: str,
        expiration: int = 3600,
        method: str = 'GET'
    ) -> str:
        """
        Generate signed URL for file access.
        
        Args:
            file_path: Path to file in storage
            expiration: URL expiration time in seconds
            method: HTTP method (GET, PUT, DELETE)
            
        Returns:
            Signed URL string
        """
        try:
            client = self._get_client()
            
            if method.upper() == 'GET':
                url = client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self._bucket_name, 'Key': file_path},
                    ExpiresIn=expiration
                )
            elif method.upper() == 'PUT':
                url = client.generate_presigned_url(
                    'put_object',
                    Params={'Bucket': self._bucket_name, 'Key': file_path},
                    ExpiresIn=expiration
                )
            elif method.upper() == 'DELETE':
                url = client.generate_presigned_url(
                    'delete_object',
                    Params={'Bucket': self._bucket_name, 'Key': file_path},
                    ExpiresIn=expiration
                )
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.logger.info(
                "Signed URL generated",
                file_path=file_path,
                method=method,
                expiration=expiration
            )
            
            return url
            
        except Exception as e:
            raise ObjectStorageError(f"Failed to generate signed URL: {e}")
    
    def _generate_public_url(self, file_path: str) -> str:
        """Generate public URL for file."""
        if self._public_url_base:
            return f"{self._public_url_base.rstrip('/')}/{file_path}"
        
        # Generate default URL based on provider
        if self._provider == 's3':
            if settings.object_storage_endpoint_url:
                base_url = settings.object_storage_endpoint_url
            else:
                base_url = f"https://s3.{settings.object_storage_region}.amazonaws.com"
            return f"{base_url}/{self._bucket_name}/{file_path}"
        elif self._provider == 'digitalocean':
            return f"https://{self._bucket_name}.{settings.object_storage_region}.digitaloceanspaces.com/{file_path}"
        elif self._provider == 'minio':
            endpoint = settings.object_storage_endpoint_url or "http://localhost:9000"
            return f"{endpoint}/{self._bucket_name}/{file_path}"
        
        return file_path
    
    async def delete_file(self, file_path: str) -> bool:
        """
        Delete file from object storage.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            True if deleted successfully
        """
        try:
            client = self._get_client()
            
            client.delete_object(Bucket=self._bucket_name, Key=file_path)
            
            self.logger.info("File deleted successfully", file_path=file_path)
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                self.logger.warning("File not found for deletion", file_path=file_path)
                return False
            raise ObjectStorageError(f"Delete failed: {e}")
        except Exception as e:
            raise ObjectStorageError(f"Delete failed: {e}")
    
    async def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List files in object storage.
        
        Args:
            prefix: Filter files by prefix
            max_keys: Maximum number of files to return
            
        Returns:
            List of file information dictionaries
        """
        try:
            client = self._get_client()
            
            response = client.list_objects_v2(
                Bucket=self._bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                file_info = {
                    'file_path': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag'].strip('"'),
                    'public_url': self._generate_public_url(obj['Key'])
                }
                files.append(file_info)
            
            self.logger.info(
                "Files listed successfully",
                prefix=prefix,
                count=len(files)
            )
            
            return files
            
        except Exception as e:
            raise ObjectStorageError(f"List files failed: {e}")
    
    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Get file information and metadata.
        
        Args:
            file_path: Path to file in storage
            
        Returns:
            File information dictionary
        """
        try:
            client = self._get_client()
            
            response = client.head_object(Bucket=self._bucket_name, Key=file_path)
            
            file_info = {
                'file_path': file_path,
                'size': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'].isoformat(),
                'etag': response['ETag'].strip('"'),
                'file_metadata': response.get('Metadata', {}),
                'public_url': self._generate_public_url(file_path)
            }
            
            return file_info
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found: {file_path}")
            raise ObjectStorageError(f"Get file info failed: {e}")
        except Exception as e:
            raise ObjectStorageError(f"Get file info failed: {e}")
    
    async def copy_file(
        self,
        source_path: str,
        destination_path: str,
        file_metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Copy file within object storage.
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            file_metadata: Additional metadata for copied file
            
        Returns:
            Information about copied file
        """
        try:
            client = self._get_client()
            
            copy_source = {'Bucket': self._bucket_name, 'Key': source_path}
            
            copy_args = {
                'CopySource': copy_source,
                'Bucket': self._bucket_name,
                'Key': destination_path
            }
            
            if file_metadata:
                copy_args['Metadata'] = file_metadata
                copy_args['MetadataDirective'] = 'REPLACE'
            
            client.copy_object(**copy_args)
            
            # Get info about copied file
            file_info = await self.get_file_info(destination_path)
            
            self.logger.info(
                "File copied successfully",
                source_path=source_path,
                destination_path=destination_path
            )
            
            return file_info
            
        except Exception as e:
            raise ObjectStorageError(f"Copy file failed: {e}")


# Global object storage service instance
object_storage_service = ObjectStorageService() 