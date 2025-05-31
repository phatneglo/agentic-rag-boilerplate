"""
Qdrant indexer service.
Handles Qdrant indexing job creation and management.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from app.core.logging_config import LoggerMixin
from app.models.requests.document_requests import QdrantIndexingRequest
from app.models.responses.document_responses import QdrantIndexingResponse
from app.utils.queue_manager import queue_manager
from app.utils.exceptions import (
    QdrantIndexingError,
    ValidationError,
    QueueError,
)


class QdrantIndexerService(LoggerMixin):
    """Service for handling Qdrant indexing operations."""
    
    def __init__(self):
        self.queue_manager = queue_manager
    
    async def index_document(
        self,
        request: QdrantIndexingRequest
    ) -> QdrantIndexingResponse:
        """
        Create a Qdrant indexing job.
        
        Args:
            request: Qdrant indexing request
            
        Returns:
            QdrantIndexingResponse: Response with job details
            
        Raises:
            QdrantIndexingError: If indexing job creation fails
            ValidationError: If request validation fails
        """
        try:
            self.logger.info(
                "Creating Qdrant indexing job",
                document_id=request.document_id,
                collection_name=request.collection_name
            )
            
            # Validate request
            await self._validate_indexing_request(request)
            
            # Create job in queue
            job_id = await self.queue_manager.add_qdrant_indexing_job(
                document_id=request.document_id,
                content=request.content,
                metadata=request.metadata,
                collection_name=request.collection_name
            )
            
            # Calculate estimated completion time (vectorization takes longer)
            estimated_completion = datetime.utcnow() + timedelta(minutes=3)
            
            self.logger.info(
                "Qdrant indexing job created successfully",
                document_id=request.document_id,
                job_id=job_id
            )
            
            from app.core.config import settings
            return QdrantIndexingResponse(
                success=True,
                message="Qdrant indexing job created successfully",
                job_id=job_id,
                queue_name=settings.queue_names["qdrant_indexer"],
                estimated_completion=estimated_completion,
                document_id=request.document_id,
                collection_name=request.collection_name
            )
            
        except ValidationError:
            raise
        except QueueError as e:
            self.logger.error(
                "Failed to create Qdrant indexing job",
                document_id=request.document_id,
                error=str(e)
            )
            raise QdrantIndexingError(f"Failed to create indexing job: {e}")
        except Exception as e:
            self.logger.error(
                "Unexpected error in Qdrant indexing service",
                document_id=request.document_id,
                error=str(e)
            )
            raise QdrantIndexingError(f"Unexpected error: {e}")
    
    async def _validate_indexing_request(
        self,
        request: QdrantIndexingRequest
    ) -> None:
        """
        Validate Qdrant indexing request.
        
        Args:
            request: Qdrant indexing request
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate content length (Qdrant has different limits than Typesense)
        if len(request.content) > 2_000_000:  # 2MB limit for vectorization
            raise ValidationError("Content too large for vectorization. Maximum size is 2MB")
        
        # Validate minimum content length
        if len(request.content.strip()) < 10:
            raise ValidationError("Content too short for meaningful vectorization. Minimum 10 characters")
        
        # Validate collection name format
        if not request.collection_name.replace('_', '').replace('-', '').isalnum():
            raise ValidationError(
                "Collection name must contain only alphanumeric characters, hyphens, and underscores"
            )
        
        # Validate metadata
        if request.metadata:
            await self._validate_metadata(request.metadata)
    
    async def _validate_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Validate metadata for Qdrant indexing.
        
        Args:
            metadata: Document metadata
            
        Raises:
            ValidationError: If metadata is invalid
        """
        # Check metadata size
        import json
        metadata_size = len(json.dumps(metadata))
        if metadata_size > 50_000:  # 50KB limit for Qdrant payload
            raise ValidationError("Metadata too large. Maximum size is 50KB")
        
        # Validate metadata fields
        reserved_fields = {'id', 'vector', 'payload'}
        for key in metadata.keys():
            if key in reserved_fields:
                raise ValidationError(f"'{key}' is a reserved field name in Qdrant")
            
            if not isinstance(key, str) or not key.strip():
                raise ValidationError("Metadata keys must be non-empty strings")
            
            # Validate field name format
            if not key.replace('_', '').replace('-', '').isalnum():
                raise ValidationError(
                    f"Field name '{key}' must contain only alphanumeric characters, hyphens, and underscores"
                )
            
            # Validate field values for Qdrant compatibility
            value = metadata[key]
            if not self._is_valid_qdrant_value(value):
                raise ValidationError(
                    f"Invalid value type for field '{key}'. "
                    "Qdrant supports strings, numbers, booleans, and lists of these types"
                )
    
    def _is_valid_qdrant_value(self, value: Any) -> bool:
        """
        Check if a value is valid for Qdrant payload.
        
        Args:
            value: Value to validate
            
        Returns:
            bool: True if value is valid
        """
        if value is None:
            return True
        
        if isinstance(value, (str, int, float, bool)):
            return True
        
        if isinstance(value, list):
            return all(isinstance(item, (str, int, float, bool)) for item in value)
        
        if isinstance(value, dict):
            return all(
                isinstance(k, str) and self._is_valid_qdrant_value(v)
                for k, v in value.items()
            )
        
        return False
    
    async def get_indexing_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Get Qdrant indexing job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict[str, Any]: Job status information
            
        Raises:
            QdrantIndexingError: If status retrieval fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["qdrant_indexer"]
            
            status = await self.queue_manager.get_job_status(queue_name, job_id)
            
            self.logger.info(
                "Retrieved Qdrant indexing job status",
                job_id=job_id,
                status=status.get("status")
            )
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get Qdrant indexing job status",
                job_id=job_id,
                error=str(e)
            )
            raise QdrantIndexingError(f"Failed to get job status: {e}")
    
    async def retry_indexing(
        self,
        job_id: str
    ) -> bool:
        """
        Retry a failed Qdrant indexing job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if retry was successful
            
        Raises:
            QdrantIndexingError: If retry fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["qdrant_indexer"]
            
            success = await self.queue_manager.retry_failed_job(queue_name, job_id)
            
            if success:
                self.logger.info("Qdrant indexing job retried successfully", job_id=job_id)
            else:
                self.logger.warning("Failed to retry Qdrant indexing job", job_id=job_id)
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to retry Qdrant indexing job",
                job_id=job_id,
                error=str(e)
            )
            raise QdrantIndexingError(f"Failed to retry job: {e}")


# Global service instance
qdrant_indexer_service = QdrantIndexerService() 