"""
File Manager Request Models

Request models for file manager operations following RORO pattern.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator


class CreateFolderRequest(BaseModel):
    """Request model for creating a new folder."""
    
    path: str = Field(
        default="",
        description="Parent directory path where folder should be created",
        example="documents/projects"
    )
    folder_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the new folder",
        example="new_project"
    )
    
    @validator("folder_name")
    def validate_folder_name(cls, v):
        """Validate folder name doesn't contain invalid characters."""
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Folder name cannot contain: {', '.join(invalid_chars)}")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "path": "documents/projects",
                "folder_name": "new_project"
            }
        }


class RenameItemRequest(BaseModel):
    """Request model for renaming a file or folder."""
    
    path: str = Field(
        ...,
        description="Current path of the item to rename",
        example="documents/old_name.txt"
    )
    new_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="New name for the item",
        example="new_name.txt"
    )
    
    @validator("new_name")
    def validate_new_name(cls, v):
        """Validate new name doesn't contain invalid characters."""
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in v for char in invalid_chars):
            raise ValueError(f"Name cannot contain: {', '.join(invalid_chars)}")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "path": "documents/old_name.txt",
                "new_name": "new_name.txt"
            }
        }


class MoveItemRequest(BaseModel):
    """Request model for moving a file or folder."""
    
    source_path: str = Field(
        ...,
        description="Current path of the item to move",
        example="documents/file.txt"
    )
    destination_path: str = Field(
        ...,
        description="Destination directory path",
        example="documents/archive"
    )
    
    @validator("destination_path")
    def validate_destination_path(cls, v):
        """Ensure destination path is provided."""
        if not v.strip():
            raise ValueError("Destination path cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "source_path": "documents/file.txt",
                "destination_path": "documents/archive"
            }
        }


class SearchRequest(BaseModel):
    """Request model for searching files and folders."""
    
    query: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Search query",
        example="project"
    )
    path: str = Field(
        default="",
        description="Directory path to search in (empty for root)",
        example="documents"
    )
    include_content: bool = Field(
        default=False,
        description="Whether to search file contents (for text files)"
    )
    file_types: Optional[list] = Field(
        default=None,
        description="Filter by file types/extensions",
        example=[".txt", ".pdf", ".docx"]
    )
    
    @validator("query")
    def validate_query(cls, v):
        """Validate search query."""
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "query": "project",
                "path": "documents",
                "include_content": False,
                "file_types": [".txt", ".pdf"]
            }
        }


class ShareFileRequest(BaseModel):
    """Request model for sharing a file."""
    
    path: str = Field(
        ...,
        description="Path of the file to share",
        example="documents/report.pdf"
    )
    expiry_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=168,  # Max 1 week
        description="Link expiry time in hours (1-168)",
        example=24
    )
    password: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=50,
        description="Optional password protection",
        example="secure123"
    )
    allow_download: bool = Field(
        default=True,
        description="Whether to allow file download"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "path": "documents/report.pdf",
                "expiry_hours": 24,
                "password": "secure123",
                "allow_download": True
            }
        }


class BulkOperationRequest(BaseModel):
    """Request model for bulk operations on multiple items."""
    
    paths: list[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of item paths to operate on",
        example=["file1.txt", "file2.txt", "folder1"]
    )
    operation: str = Field(
        ...,
        description="Operation to perform",
        regex="^(delete|move|copy)$",
        example="delete"
    )
    destination_path: Optional[str] = Field(
        default=None,
        description="Destination path for move/copy operations",
        example="archive"
    )
    
    @validator("destination_path")
    def validate_destination_for_move_copy(cls, v, values):
        """Validate destination path is provided for move/copy operations."""
        operation = values.get("operation")
        if operation in ["move", "copy"] and not v:
            raise ValueError("Destination path required for move/copy operations")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "paths": ["file1.txt", "file2.txt"],
                "operation": "move",
                "destination_path": "archive"
            }
        } 