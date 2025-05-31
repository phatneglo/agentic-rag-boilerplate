"""
File Manager Response Models

Response models for file manager operations following RORO pattern.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model for all file manager operations."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class FileItem(BaseModel):
    """Model representing a file or folder item."""
    
    name: str = Field(..., description="Item name")
    path: str = Field(..., description="Full path relative to storage root")
    type: str = Field(..., description="Item type: 'file' or 'folder'")
    size: int = Field(..., description="Size in bytes (0 for folders)")
    size_formatted: str = Field(..., description="Human-readable size")
    modified: str = Field(..., description="Last modified timestamp (ISO format)")
    extension: str = Field(..., description="File extension (empty for folders)")
    mime_type: Optional[str] = Field(None, description="MIME type")
    is_directory: bool = Field(..., description="Whether item is a directory")
    permissions: str = Field(..., description="File permissions (octal)")
    icon: str = Field(..., description="FontAwesome icon class")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "document.pdf",
                "path": "documents/document.pdf",
                "type": "file",
                "size": 1024000,
                "size_formatted": "1.0 MB",
                "modified": "2024-01-15T10:30:00",
                "extension": ".pdf",
                "mime_type": "application/pdf",
                "is_directory": False,
                "permissions": "644",
                "icon": "fas fa-file-pdf"
            }
        }


class Breadcrumb(BaseModel):
    """Model representing a breadcrumb navigation item."""
    
    name: str = Field(..., description="Breadcrumb name")
    path: str = Field(..., description="Path for this breadcrumb")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Documents",
                "path": "documents"
            }
        }


class DirectoryListing(BaseModel):
    """Model representing directory listing data."""
    
    current_path: str = Field(..., description="Current directory path")
    items: List[FileItem] = Field(..., description="List of files and folders")
    breadcrumbs: List[Breadcrumb] = Field(..., description="Breadcrumb navigation")
    total_items: int = Field(..., description="Total number of items")
    search_query: str = Field(default="", description="Applied search query")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_path": "documents",
                "items": [
                    {
                        "name": "folder1",
                        "path": "documents/folder1",
                        "type": "folder",
                        "size": 0,
                        "size_formatted": "0 B",
                        "modified": "2024-01-15T10:30:00",
                        "extension": "",
                        "mime_type": "folder",
                        "is_directory": True,
                        "permissions": "755",
                        "icon": "fas fa-folder"
                    }
                ],
                "breadcrumbs": [
                    {"name": "Home", "path": ""},
                    {"name": "Documents", "path": "documents"}
                ],
                "total_items": 1,
                "search_query": ""
            }
        }


class DirectoryListingResponse(BaseResponse):
    """Response model for directory listing operations."""
    
    data: DirectoryListing = Field(..., description="Directory listing data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Directory listed successfully",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "current_path": "documents",
                    "items": [],
                    "breadcrumbs": [],
                    "total_items": 0,
                    "search_query": ""
                }
            }
        }


class FileOperationData(BaseModel):
    """Model representing file operation result data."""
    
    name: Optional[str] = Field(None, description="Item name")
    path: Optional[str] = Field(None, description="Item path")
    type: Optional[str] = Field(None, description="Item type")
    size: Optional[int] = Field(None, description="File size in bytes")
    size_formatted: Optional[str] = Field(None, description="Human-readable size")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "new_folder",
                "path": "documents/new_folder",
                "type": "folder"
            }
        }


class FileOperationResponse(BaseResponse):
    """Response model for file operations (create, upload, delete, rename, move)."""
    
    data: FileOperationData = Field(..., description="Operation result data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "name": "new_folder",
                    "path": "documents/new_folder",
                    "type": "folder"
                }
            }
        }


class SearchResult(BaseModel):
    """Model representing search result data."""
    
    query: str = Field(..., description="Search query used")
    search_path: str = Field(..., description="Path where search was performed")
    results: List[FileItem] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "document",
                "search_path": "documents",
                "results": [],
                "total_results": 0
            }
        }


class SearchResponse(BaseResponse):
    """Response model for search operations."""
    
    data: SearchResult = Field(..., description="Search result data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Search completed successfully",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "query": "document",
                    "search_path": "documents",
                    "results": [],
                    "total_results": 0
                }
            }
        }


class FileInfoData(BaseModel):
    """Model representing detailed file information."""
    
    name: str = Field(..., description="File name")
    path: str = Field(..., description="Full path")
    type: str = Field(..., description="Item type")
    size: int = Field(..., description="Size in bytes")
    size_formatted: str = Field(..., description="Human-readable size")
    modified: str = Field(..., description="Last modified timestamp")
    extension: str = Field(..., description="File extension")
    mime_type: Optional[str] = Field(None, description="MIME type")
    is_directory: bool = Field(..., description="Whether item is a directory")
    permissions: str = Field(..., description="File permissions")
    icon: str = Field(..., description="FontAwesome icon class")
    checksum: Optional[str] = Field(None, description="MD5 checksum (for files)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "document.pdf",
                "path": "documents/document.pdf",
                "type": "file",
                "size": 1024000,
                "size_formatted": "1.0 MB",
                "modified": "2024-01-15T10:30:00",
                "extension": ".pdf",
                "mime_type": "application/pdf",
                "is_directory": False,
                "permissions": "644",
                "icon": "fas fa-file-pdf",
                "checksum": "d41d8cd98f00b204e9800998ecf8427e"
            }
        }


class FileInfoResponse(BaseResponse):
    """Response model for file information operations."""
    
    data: FileInfoData = Field(..., description="File information data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "File information retrieved successfully",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "name": "document.pdf",
                    "path": "documents/document.pdf",
                    "type": "file",
                    "size": 1024000,
                    "size_formatted": "1.0 MB",
                    "modified": "2024-01-15T10:30:00",
                    "extension": ".pdf",
                    "mime_type": "application/pdf",
                    "is_directory": False,
                    "permissions": "644",
                    "icon": "fas fa-file-pdf"
                }
            }
        }


class ShareLinkData(BaseModel):
    """Model representing shared link data."""
    
    share_id: str = Field(..., description="Unique share identifier")
    share_url: str = Field(..., description="Public share URL")
    file_path: str = Field(..., description="Path of shared file")
    expires_at: datetime = Field(..., description="Link expiry timestamp")
    password_protected: bool = Field(..., description="Whether link is password protected")
    allow_download: bool = Field(..., description="Whether download is allowed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "share_id": "abc123def456",
                "share_url": "https://example.com/share/abc123def456",
                "file_path": "documents/report.pdf",
                "expires_at": "2024-01-16T10:30:00",
                "password_protected": True,
                "allow_download": True
            }
        }


class ShareLinkResponse(BaseResponse):
    """Response model for file sharing operations."""
    
    data: ShareLinkData = Field(..., description="Share link data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Share link created successfully",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "share_id": "abc123def456",
                    "share_url": "https://example.com/share/abc123def456",
                    "file_path": "documents/report.pdf",
                    "expires_at": "2024-01-16T10:30:00",
                    "password_protected": True,
                    "allow_download": True
                }
            }
        }


class BulkOperationResult(BaseModel):
    """Model representing bulk operation results."""
    
    operation: str = Field(..., description="Operation performed")
    total_items: int = Field(..., description="Total items processed")
    successful_items: int = Field(..., description="Successfully processed items")
    failed_items: int = Field(..., description="Failed items")
    errors: List[Dict[str, str]] = Field(default=[], description="List of errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "operation": "delete",
                "total_items": 3,
                "successful_items": 2,
                "failed_items": 1,
                "errors": [
                    {"path": "file3.txt", "error": "File not found"}
                ]
            }
        }


class BulkOperationResponse(BaseResponse):
    """Response model for bulk operations."""
    
    data: BulkOperationResult = Field(..., description="Bulk operation results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Bulk operation completed",
                "timestamp": "2024-01-15T10:30:00",
                "data": {
                    "operation": "delete",
                    "total_items": 3,
                    "successful_items": 2,
                    "failed_items": 1,
                    "errors": []
                }
            }
        } 