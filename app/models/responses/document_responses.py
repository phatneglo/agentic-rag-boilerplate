"""
Response models for document operations.
Following RORO (Request-Response Object) pattern.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Base response model."""
    
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class JobResponse(BaseResponse):
    """Response model for job creation."""
    
    job_id: str = Field(..., description="Unique job identifier")
    queue_name: str = Field(..., description="Name of the queue where job was added")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Job created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "job_id": "job_123456",
                "queue_name": "document_processing:document_converter",
                "estimated_completion": "2024-01-15T10:35:00Z"
            }
        }


class DocumentConversionResponse(JobResponse):
    """Response model for document conversion."""
    
    document_id: str = Field(..., description="Document identifier")
    source_path: str = Field(..., description="Source document path")
    output_path: str = Field(..., description="Output document path")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Document conversion job created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "job_id": "job_123456",
                "queue_name": "document_processing:document_converter",
                "estimated_completion": "2024-01-15T10:35:00Z",
                "document_id": "doc_123",
                "source_path": "/path/to/document.pdf",
                "output_path": "/path/to/output.md"
            }
        }


class TypesenseIndexingResponse(JobResponse):
    """Response model for Typesense indexing."""
    
    document_id: str = Field(..., description="Document identifier")
    collection_name: str = Field(..., description="Typesense collection name")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Typesense indexing job created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "job_id": "job_123456",
                "queue_name": "document_processing:typesense_indexer",
                "estimated_completion": "2024-01-15T10:32:00Z",
                "document_id": "doc_123",
                "collection_name": "documents"
            }
        }


class QdrantIndexingResponse(JobResponse):
    """Response model for Qdrant indexing."""
    
    document_id: str = Field(..., description="Document identifier")
    collection_name: str = Field(..., description="Qdrant collection name")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Qdrant indexing job created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "job_id": "job_123456",
                "queue_name": "document_processing:qdrant_indexer",
                "estimated_completion": "2024-01-15T10:33:00Z",
                "document_id": "doc_123",
                "collection_name": "document_vectors"
            }
        }


class DocumentSyncResponse(JobResponse):
    """Response model for document synchronization."""
    
    source_document_id: str = Field(..., description="Source document identifier")
    target_systems: List[str] = Field(..., description="Target systems for synchronization")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Document synchronization job created successfully",
                "timestamp": "2024-01-15T10:30:00Z",
                "job_id": "job_123456",
                "queue_name": "document_processing:document_sync",
                "estimated_completion": "2024-01-15T10:40:00Z",
                "source_document_id": "doc_123",
                "target_systems": ["typesense", "qdrant"]
            }
        }


class JobStatusResponse(BaseResponse):
    """Response model for job status."""
    
    job_id: str = Field(..., description="Job identifier")
    job_name: str = Field(..., description="Job name")
    status: str = Field(..., description="Job status")
    progress: Optional[int] = Field(None, description="Job progress percentage")
    created_at: Optional[datetime] = Field(None, description="Job creation time")
    processed_at: Optional[datetime] = Field(None, description="Job processing start time")
    finished_at: Optional[datetime] = Field(None, description="Job completion time")
    failed_reason: Optional[str] = Field(None, description="Failure reason if job failed")
    attempts_made: int = Field(0, description="Number of attempts made")
    attempts_total: int = Field(1, description="Total number of attempts allowed")
    data: Optional[Dict[str, Any]] = Field(None, description="Job data")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Job status retrieved successfully",
                "timestamp": "2024-01-15T10:35:00Z",
                "job_id": "job_123456",
                "job_name": "convert_document",
                "status": "completed",
                "progress": 100,
                "created_at": "2024-01-15T10:30:00Z",
                "processed_at": "2024-01-15T10:31:00Z",
                "finished_at": "2024-01-15T10:35:00Z",
                "failed_reason": None,
                "attempts_made": 1,
                "attempts_total": 3,
                "data": {
                    "document_id": "doc_123",
                    "source_path": "/path/to/document.pdf",
                    "output_path": "/path/to/output.md"
                }
            }
        }


class QueueStatsResponse(BaseResponse):
    """Response model for queue statistics."""
    
    queue_name: str = Field(..., description="Queue name")
    waiting: int = Field(..., description="Number of waiting jobs")
    active: int = Field(..., description="Number of active jobs")
    completed: int = Field(..., description="Number of completed jobs")
    failed: int = Field(..., description="Number of failed jobs")
    delayed: int = Field(..., description="Number of delayed jobs")
    total: int = Field(..., description="Total number of jobs")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Queue statistics retrieved successfully",
                "timestamp": "2024-01-15T10:35:00Z",
                "queue_name": "document_processing:document_converter",
                "waiting": 5,
                "active": 2,
                "completed": 150,
                "failed": 3,
                "delayed": 1,
                "total": 161
            }
        }


class ErrorResponse(BaseResponse):
    """Response model for errors."""
    
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "message": "Validation error occurred",
                "timestamp": "2024-01-15T10:35:00Z",
                "error_code": "VALIDATION_ERROR",
                "details": {
                    "field": "document_id",
                    "issue": "Document ID cannot be empty"
                }
            }
        }


class HealthCheckResponse(BaseResponse):
    """Response model for health checks."""
    
    service: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Service uptime in seconds")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Dependency statuses")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Service is healthy",
                "timestamp": "2024-01-15T10:35:00Z",
                "service": "document-processing-api",
                "status": "healthy",
                "version": "1.0.0",
                "uptime": 3600.5,
                "dependencies": {
                    "redis": "connected",
                    "typesense": "connected",
                    "qdrant": "connected"
                }
            }
        } 