"""
Typesense indexer service.
Handles Typesense indexing job creation and management.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from app.core.logging_config import LoggerMixin
from app.models.requests.document_requests import TypesenseIndexingRequest
from app.models.responses.document_responses import TypesenseIndexingResponse
from app.utils.queue_manager import queue_manager
from app.utils.exceptions import (
    TypesenseIndexingError,
    ValidationError,
    QueueError,
)


class TypesenseIndexerService(LoggerMixin):
    """Service for handling Typesense indexing operations."""
    
    def __init__(self):
        self.queue_manager = queue_manager
    
    async def index_document(
        self,
        request: TypesenseIndexingRequest
    ) -> TypesenseIndexingResponse:
        """
        Create a Typesense indexing job.
        
        Args:
            request: Typesense indexing request
            
        Returns:
            TypesenseIndexingResponse: Response with job details
            
        Raises:
            TypesenseIndexingError: If indexing job creation fails
            ValidationError: If request validation fails
        """
        try:
            self.logger.info(
                "Creating Typesense indexing job",
                document_id=request.document_id,
                collection_name=request.collection_name
            )
            
            # Validate request
            await self._validate_indexing_request(request)
            
            # Create job in queue
            job_id = await self.queue_manager.add_typesense_indexing_job(
                document_id=request.document_id,
                content=request.content,
                metadata=request.metadata,
                collection_name=request.collection_name
            )
            
            # Calculate estimated completion time
            estimated_completion = datetime.utcnow() + timedelta(minutes=2)
            
            self.logger.info(
                "Typesense indexing job created successfully",
                document_id=request.document_id,
                job_id=job_id
            )
            
            from app.core.config import settings
            return TypesenseIndexingResponse(
                success=True,
                message="Typesense indexing job created successfully",
                job_id=job_id,
                queue_name=settings.queue_names["typesense_indexer"],
                estimated_completion=estimated_completion,
                document_id=request.document_id,
                collection_name=request.collection_name
            )
            
        except ValidationError:
            raise
        except QueueError as e:
            self.logger.error(
                "Failed to create Typesense indexing job",
                document_id=request.document_id,
                error=str(e)
            )
            raise TypesenseIndexingError(f"Failed to create indexing job: {e}")
        except Exception as e:
            self.logger.error(
                "Unexpected error in Typesense indexing service",
                document_id=request.document_id,
                error=str(e)
            )
            raise TypesenseIndexingError(f"Unexpected error: {e}")
    
    async def _validate_indexing_request(
        self,
        request: TypesenseIndexingRequest
    ) -> None:
        """
        Validate Typesense indexing request.
        
        Args:
            request: Typesense indexing request
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate content length
        if len(request.content) > 1_000_000:  # 1MB limit
            raise ValidationError("Content too large. Maximum size is 1MB")
        
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
        Validate metadata for Typesense indexing.
        
        Args:
            metadata: Document metadata
            
        Raises:
            ValidationError: If metadata is invalid
        """
        # Check metadata size
        import json
        metadata_size = len(json.dumps(metadata))
        if metadata_size > 100_000:  # 100KB limit
            raise ValidationError("Metadata too large. Maximum size is 100KB")
        
        # Validate metadata fields
        reserved_fields = {'id', '_id', 'document_id'}
        for key in metadata.keys():
            if key in reserved_fields:
                raise ValidationError(f"'{key}' is a reserved field name")
            
            if not isinstance(key, str) or not key.strip():
                raise ValidationError("Metadata keys must be non-empty strings")
            
            # Validate field name format
            if not key.replace('_', '').replace('-', '').isalnum():
                raise ValidationError(
                    f"Field name '{key}' must contain only alphanumeric characters, hyphens, and underscores"
                )
    
    async def get_indexing_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Get Typesense indexing job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict[str, Any]: Job status information
            
        Raises:
            TypesenseIndexingError: If status retrieval fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["typesense_indexer"]
            
            status = await self.queue_manager.get_job_status(queue_name, job_id)
            
            self.logger.info(
                "Retrieved Typesense indexing job status",
                job_id=job_id,
                status=status.get("status")
            )
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get Typesense indexing job status",
                job_id=job_id,
                error=str(e)
            )
            raise TypesenseIndexingError(f"Failed to get job status: {e}")
    
    async def retry_indexing(
        self,
        job_id: str
    ) -> bool:
        """
        Retry a failed Typesense indexing job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if retry was successful
            
        Raises:
            TypesenseIndexingError: If retry fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["typesense_indexer"]
            
            success = await self.queue_manager.retry_failed_job(queue_name, job_id)
            
            if success:
                self.logger.info("Typesense indexing job retried successfully", job_id=job_id)
            else:
                self.logger.warning("Failed to retry Typesense indexing job", job_id=job_id)
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to retry Typesense indexing job",
                job_id=job_id,
                error=str(e)
            )
            raise TypesenseIndexingError(f"Failed to retry job: {e}")


# Global service instance
typesense_indexer_service = TypesenseIndexerService() 