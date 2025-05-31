"""
File upload request models.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, validator


class FileUploadRequest(BaseModel):
    """Request model for file upload metadata."""
    
    folder_structure: Optional[str] = Field(
        default=None,
        description="Override default folder structure (year-month-day, year-month, year, flat)"
    )
    file_metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional metadata to store with files"
    )
    
    @validator("folder_structure")
    def validate_folder_structure(cls, v):
        if v is not None:
            allowed_structures = ["year-month-day", "year-month", "year", "flat"]
            if v not in allowed_structures:
                raise ValueError(f"folder_structure must be one of: {', '.join(allowed_structures)}")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "folder_structure": "year-month-day",
                "file_metadata": {
                    "category": "documents",
                    "project": "project-alpha",
                    "uploaded_by": "user123"
                }
            }
        }


class FileDownloadRequest(BaseModel):
    """Request model for file download."""
    
    file_path: str = Field(
        ...,
        description="Path to file in object storage"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "2024/01/15/20240115_143022_abc123.pdf"
            }
        }


class SignedUrlRequest(BaseModel):
    """Request model for generating signed URLs."""
    
    file_path: str = Field(
        ...,
        description="Path to file in object storage"
    )
    expiration: int = Field(
        default=3600,
        ge=60,
        le=604800,  # 7 days max
        description="URL expiration time in seconds (60 seconds to 7 days)"
    )
    method: str = Field(
        default="GET",
        description="HTTP method for the signed URL"
    )
    
    @validator("method")
    def validate_method(cls, v):
        allowed_methods = ["GET", "PUT", "DELETE"]
        if v.upper() not in allowed_methods:
            raise ValueError(f"method must be one of: {', '.join(allowed_methods)}")
        return v.upper()
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "2024/01/15/20240115_143022_abc123.pdf",
                "expiration": 3600,
                "method": "GET"
            }
        }


class FileListRequest(BaseModel):
    """Request model for listing files."""
    
    prefix: str = Field(
        default="",
        description="Filter files by prefix (folder path)"
    )
    max_files: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of files to return (1-1000)"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "prefix": "2024/01/",
                "max_files": 100
            }
        }


class FileDeleteRequest(BaseModel):
    """Request model for file deletion."""
    
    file_path: str = Field(
        ...,
        description="Path to file in object storage"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "file_path": "2024/01/15/20240115_143022_abc123.pdf"
            }
        }


class FileCopyRequest(BaseModel):
    """Request model for file copying."""
    
    source_path: str = Field(
        ...,
        description="Source file path in object storage"
    )
    destination_path: str = Field(
        ...,
        description="Destination file path in object storage"
    )
    file_metadata: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional metadata for copied file"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "source_path": "2024/01/15/20240115_143022_abc123.pdf",
                "destination_path": "backup/2024/01/15/20240115_143022_abc123.pdf",
                "file_metadata": {
                    "backup_type": "manual",
                    "copied_by": "user123"
                }
            }
        } 