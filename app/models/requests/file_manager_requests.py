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
        json_schema_extra = {
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
        json_schema_extra = {
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
    new_name: Optional[str] = Field(
        default=None,
        description="Optional new name for the item",
        example="renamed_file.txt"
    )
    
    @validator("destination_path")
    def validate_destination_path(cls, v):
        """Ensure destination path is provided."""
        if not v.strip():
            raise ValueError("Destination path cannot be empty")
        return v.strip()
    
    @validator("new_name")
    def validate_new_name(cls, v):
        """Validate new name if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if any(char in v for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']):
                raise ValueError(f"Name cannot contain: {', '.join(['/', '\\', ':', '*', '?', '\"', '<', '>', '|'])}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_path": "documents/file.txt",
                "destination_path": "documents/archive",
                "new_name": "renamed_file.txt"
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
        json_schema_extra = {
            "example": {
                "query": "project",
                "path": "documents",
                "include_content": False,
                "file_types": [".txt", ".pdf"]
            }
        } 