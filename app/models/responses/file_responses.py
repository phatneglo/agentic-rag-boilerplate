"""
File upload response models.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """File information model."""
    
    file_path: str = Field(..., description="Path to file in object storage")
    original_filename: str = Field(..., description="Original filename")
    public_url: str = Field(..., description="Public URL to access the file")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")
    file_metadata: Dict[str, str] = Field(default_factory=dict, description="File metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                "original_filename": "document.pdf",
                "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf",
                "content_type": "application/pdf",
                "size": 1024000,
                "file_metadata": {
                    "original_filename": "document.pdf",
                    "upload_timestamp": "2024-01-15T14:30:22.123456",
                    "content_type": "application/pdf"
                }
            }
        }


class FileUploadResponse(BaseModel):
    """Response model for single file upload."""
    
    success: bool = Field(default=True, description="Upload success status")
    message: str = Field(default="File uploaded successfully", description="Response message")
    file: FileInfo = Field(..., description="Uploaded file information")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File uploaded successfully",
                "file": {
                    "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                    "original_filename": "document.pdf",
                    "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf",
                    "content_type": "application/pdf",
                    "size": 1024000,
                    "file_metadata": {
                        "original_filename": "document.pdf",
                        "upload_timestamp": "2024-01-15T14:30:22.123456",
                        "content_type": "application/pdf"
                    }
                },
                "timestamp": 1705327822.123456
            }
        }


class MultipleFileUploadResponse(BaseModel):
    """Response model for multiple file upload."""
    
    success: bool = Field(default=True, description="Overall upload success status")
    message: str = Field(..., description="Response message")
    files: List[FileInfo] = Field(default_factory=list, description="Successfully uploaded files")
    total_files: int = Field(..., description="Total number of files processed")
    successful_uploads: int = Field(..., description="Number of successful uploads")
    failed_uploads: int = Field(default=0, description="Number of failed uploads")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="Upload errors if any")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "2 files uploaded successfully",
                "files": [
                    {
                        "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                        "original_filename": "document1.pdf",
                        "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf",
                        "content_type": "application/pdf",
                        "size": 1024000,
                        "file_metadata": {}
                    },
                    {
                        "file_path": "2024/01/15/20240115_143023_def456.jpg",
                        "original_filename": "image1.jpg",
                        "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143023_def456.jpg",
                        "content_type": "image/jpeg",
                        "size": 512000,
                        "file_metadata": {}
                    }
                ],
                "total_files": 2,
                "successful_uploads": 2,
                "failed_uploads": 0,
                "errors": [],
                "timestamp": 1705327822.123456
            }
        }


class FileDownloadResponse(BaseModel):
    """Response model for file download."""
    
    success: bool = Field(default=True, description="Download success status")
    message: str = Field(default="File downloaded successfully", description="Response message")
    file_path: str = Field(..., description="Path to downloaded file")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File downloaded successfully",
                "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                "content_type": "application/pdf",
                "size": 1024000,
                "timestamp": 1705327822.123456
            }
        }


class SignedUrlResponse(BaseModel):
    """Response model for signed URL generation."""
    
    success: bool = Field(default=True, description="URL generation success status")
    message: str = Field(default="Signed URL generated successfully", description="Response message")
    file_path: str = Field(..., description="Path to file in storage")
    signed_url: str = Field(..., description="Generated signed URL")
    method: str = Field(..., description="HTTP method for the URL")
    expiration: int = Field(..., description="URL expiration time in seconds")
    expires_at: str = Field(..., description="URL expiration timestamp")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Signed URL generated successfully",
                "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                "signed_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf?AWSAccessKeyId=...",
                "method": "GET",
                "expiration": 3600,
                "expires_at": "2024-01-15T15:30:22.123456",
                "timestamp": 1705327822.123456
            }
        }


class FileListResponse(BaseModel):
    """Response model for file listing."""
    
    success: bool = Field(default=True, description="List operation success status")
    message: str = Field(..., description="Response message")
    files: List[FileInfo] = Field(default_factory=list, description="List of files")
    prefix: str = Field(..., description="Search prefix used")
    total_files: int = Field(..., description="Total number of files found")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Files listed successfully",
                "files": [
                    {
                        "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                        "original_filename": "document.pdf",
                        "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf",
                        "content_type": "application/pdf",
                        "size": 1024000,
                        "file_metadata": {}
                    }
                ],
                "prefix": "2024/01/",
                "total_files": 1,
                "timestamp": 1705327822.123456
            }
        }


class FileDeleteResponse(BaseModel):
    """Response model for file deletion."""
    
    success: bool = Field(default=True, description="Delete operation success status")
    message: str = Field(..., description="Response message")
    file_path: str = Field(..., description="Path to deleted file")
    deleted: bool = Field(..., description="Whether file was actually deleted")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File deleted successfully",
                "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                "deleted": True,
                "timestamp": 1705327822.123456
            }
        }


class FileCopyResponse(BaseModel):
    """Response model for file copying."""
    
    success: bool = Field(default=True, description="Copy operation success status")
    message: str = Field(default="File copied successfully", description="Response message")
    source_path: str = Field(..., description="Source file path")
    destination_path: str = Field(..., description="Destination file path")
    file: FileInfo = Field(..., description="Copied file information")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File copied successfully",
                "source_path": "2024/01/15/20240115_143022_abc123.pdf",
                "destination_path": "backup/2024/01/15/20240115_143022_abc123.pdf",
                "file": {
                    "file_path": "backup/2024/01/15/20240115_143022_abc123.pdf",
                    "original_filename": "document.pdf",
                    "public_url": "https://bucket.s3.amazonaws.com/backup/2024/01/15/20240115_143022_abc123.pdf",
                    "content_type": "application/pdf",
                    "size": 1024000,
                    "file_metadata": {}
                },
                "timestamp": 1705327822.123456
            }
        }


class FileInfoResponse(BaseModel):
    """Response model for file information."""
    
    success: bool = Field(default=True, description="Info retrieval success status")
    message: str = Field(default="File information retrieved successfully", description="Response message")
    file: FileInfo = Field(..., description="File information")
    timestamp: float = Field(..., description="Response timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "File information retrieved successfully",
                "file": {
                    "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                    "original_filename": "document.pdf",
                    "public_url": "https://bucket.s3.amazonaws.com/2024/01/15/20240115_143022_abc123.pdf",
                    "content_type": "application/pdf",
                    "size": 1024000,
                    "file_metadata": {
                        "original_filename": "document.pdf",
                        "upload_timestamp": "2024-01-15T14:30:22.123456",
                        "content_type": "application/pdf"
                    }
                },
                "timestamp": 1705327822.123456
            }
        } 