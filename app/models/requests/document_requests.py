"""
Request models for document operations.
Following RORO (Request-Response Object) pattern.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class DocumentConversionRequest(BaseModel):
    """Request model for document conversion."""
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the document",
        min_length=1,
        max_length=255
    )
    source_path: str = Field(
        ...,
        description="Path to the source document",
        min_length=1
    )
    output_path: str = Field(
        ...,
        description="Path where the converted document will be saved",
        min_length=1
    )
    conversion_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional options for document conversion"
    )
    
    @validator("document_id")
    def validate_document_id(cls, v):
        """Validate document ID format."""
        if not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()
    
    @validator("source_path", "output_path")
    def validate_paths(cls, v):
        """Validate file paths."""
        if not v.strip():
            raise ValueError("Path cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "source_path": "/path/to/document.pdf",
                "output_path": "/path/to/output.md",
                "conversion_options": {
                    "preserve_formatting": True,
                    "extract_images": False
                }
            }
        }


class TypesenseIndexingRequest(BaseModel):
    """Request model for Typesense indexing."""
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the document",
        min_length=1,
        max_length=255
    )
    content: str = Field(
        ...,
        description="Document content to index",
        min_length=1
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )
    collection_name: str = Field(
        ...,
        description="Typesense collection name",
        min_length=1,
        max_length=100
    )
    
    @validator("document_id", "collection_name")
    def validate_identifiers(cls, v):
        """Validate identifiers."""
        if not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()
    
    @validator("content")
    def validate_content(cls, v):
        """Validate content."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "content": "Document content to index",
                "metadata": {
                    "title": "Document Title",
                    "author": "Author Name",
                    "tags": ["tag1", "tag2"]
                },
                "collection_name": "documents"
            }
        }


class QdrantIndexingRequest(BaseModel):
    """Request model for Qdrant indexing."""
    
    document_id: str = Field(
        ...,
        description="Unique identifier for the document",
        min_length=1,
        max_length=255
    )
    content: str = Field(
        ...,
        description="Document content to vectorize",
        min_length=1
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Document metadata"
    )
    collection_name: str = Field(
        ...,
        description="Qdrant collection name",
        min_length=1,
        max_length=100
    )
    
    @validator("document_id", "collection_name")
    def validate_identifiers(cls, v):
        """Validate identifiers."""
        if not v.strip():
            raise ValueError("Identifier cannot be empty")
        return v.strip()
    
    @validator("content")
    def validate_content(cls, v):
        """Validate content."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v.strip()
    
    class Config:
        schema_extra = {
            "example": {
                "document_id": "doc_123",
                "content": "Document content to vectorize",
                "metadata": {
                    "title": "Document Title",
                    "source": "upload"
                },
                "collection_name": "document_vectors"
            }
        }


class DocumentSyncRequest(BaseModel):
    """Request model for document synchronization."""
    
    source_document_id: str = Field(
        ...,
        description="ID of the source document to sync",
        min_length=1,
        max_length=255
    )
    target_systems: List[str] = Field(
        ...,
        description="List of target systems to sync to",
        min_items=1
    )
    sync_options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional synchronization options"
    )
    
    @validator("source_document_id")
    def validate_document_id(cls, v):
        """Validate document ID."""
        if not v.strip():
            raise ValueError("Document ID cannot be empty")
        return v.strip()
    
    @validator("target_systems")
    def validate_target_systems(cls, v):
        """Validate target systems."""
        if not v:
            raise ValueError("At least one target system must be specified")
        
        valid_systems = {"typesense", "qdrant"}
        for system in v:
            if system not in valid_systems:
                raise ValueError(f"Invalid target system: {system}. Valid options: {valid_systems}")
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "source_document_id": "doc_123",
                "target_systems": ["typesense", "qdrant"],
                "sync_options": {
                    "force_update": False,
                    "batch_size": 100
                }
            }
        }