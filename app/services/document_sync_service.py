"""
Document sync service.
Handles document synchronization job creation and management.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.core.logging_config import LoggerMixin
from app.models.requests.document_requests import DocumentSyncRequest
from app.models.responses.document_responses import DocumentSyncResponse
from app.utils.queue_manager import queue_manager
from app.utils.exceptions import (
    DocumentSyncError,
    ValidationError,
    QueueError,
)


class DocumentSyncService(LoggerMixin):
    """Service for handling document synchronization operations."""
    
    def __init__(self):
        self.queue_manager = queue_manager
        self.supported_systems = {"typesense", "qdrant"}
    
    async def sync_document(
        self,
        request: DocumentSyncRequest
    ) -> DocumentSyncResponse:
        """
        Create a document synchronization job.
        
        Args:
            request: Document synchronization request
            
        Returns:
            DocumentSyncResponse: Response with job details
            
        Raises:
            DocumentSyncError: If sync job creation fails
            ValidationError: If request validation fails
        """
        try:
            self.logger.info(
                "Creating document synchronization job",
                source_document_id=request.source_document_id,
                target_systems=request.target_systems
            )
            
            # Validate request
            await self._validate_sync_request(request)
            
            # Create job in queue
            job_id = await self.queue_manager.add_document_sync_job(
                source_document_id=request.source_document_id,
                target_systems=request.target_systems,
                sync_options=request.sync_options
            )
            
            # Calculate estimated completion time based on number of target systems
            base_time = 2  # Base 2 minutes
            additional_time = len(request.target_systems) * 1  # 1 minute per system
            estimated_completion = datetime.utcnow() + timedelta(minutes=base_time + additional_time)
            
            self.logger.info(
                "Document synchronization job created successfully",
                source_document_id=request.source_document_id,
                job_id=job_id
            )
            
            from app.core.config import settings
            return DocumentSyncResponse(
                success=True,
                message="Document synchronization job created successfully",
                job_id=job_id,
                queue_name=settings.queue_names["document_sync"],
                estimated_completion=estimated_completion,
                source_document_id=request.source_document_id,
                target_systems=request.target_systems
            )
            
        except ValidationError:
            raise
        except QueueError as e:
            self.logger.error(
                "Failed to create document synchronization job",
                source_document_id=request.source_document_id,
                error=str(e)
            )
            raise DocumentSyncError(f"Failed to create sync job: {e}")
        except Exception as e:
            self.logger.error(
                "Unexpected error in document synchronization service",
                source_document_id=request.source_document_id,
                error=str(e)
            )
            raise DocumentSyncError(f"Unexpected error: {e}")
    
    async def _validate_sync_request(
        self,
        request: DocumentSyncRequest
    ) -> None:
        """
        Validate document synchronization request.
        
        Args:
            request: Document synchronization request
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate target systems
        invalid_systems = set(request.target_systems) - self.supported_systems
        if invalid_systems:
            raise ValidationError(
                f"Unsupported target systems: {', '.join(invalid_systems)}. "
                f"Supported systems: {', '.join(self.supported_systems)}"
            )
        
        # Check for duplicate systems
        if len(request.target_systems) != len(set(request.target_systems)):
            raise ValidationError("Duplicate target systems are not allowed")
        
        # Validate sync options
        if request.sync_options:
            await self._validate_sync_options(request.sync_options)
    
    async def _validate_sync_options(
        self,
        options: Dict[str, Any]
    ) -> None:
        """
        Validate synchronization options.
        
        Args:
            options: Synchronization options
            
        Raises:
            ValidationError: If options are invalid
        """
        valid_options = {
            'force_update',
            'batch_size',
            'include_metadata',
            'exclude_fields',
            'timeout',
            'retry_failed'
        }
        
        for key in options.keys():
            if key not in valid_options:
                raise ValidationError(
                    f"Invalid sync option: {key}. "
                    f"Valid options: {', '.join(valid_options)}"
                )
        
        # Validate specific option values
        if 'batch_size' in options:
            batch_size = options['batch_size']
            if not isinstance(batch_size, int) or not 1 <= batch_size <= 1000:
                raise ValidationError("Batch size must be an integer between 1 and 1000")
        
        if 'timeout' in options:
            timeout = options['timeout']
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValidationError("Timeout must be a positive number")
        
        if 'exclude_fields' in options:
            exclude_fields = options['exclude_fields']
            if not isinstance(exclude_fields, list):
                raise ValidationError("Exclude fields must be a list")
            
            if not all(isinstance(field, str) for field in exclude_fields):
                raise ValidationError("All exclude fields must be strings")
    
    async def get_sync_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Get document synchronization job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict[str, Any]: Job status information
            
        Raises:
            DocumentSyncError: If status retrieval fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["document_sync"]
            
            status = await self.queue_manager.get_job_status(queue_name, job_id)
            
            self.logger.info(
                "Retrieved document synchronization job status",
                job_id=job_id,
                status=status.get("status")
            )
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get document synchronization job status",
                job_id=job_id,
                error=str(e)
            )
            raise DocumentSyncError(f"Failed to get job status: {e}")
    
    async def retry_sync(
        self,
        job_id: str
    ) -> bool:
        """
        Retry a failed document synchronization job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if retry was successful
            
        Raises:
            DocumentSyncError: If retry fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["document_sync"]
            
            success = await self.queue_manager.retry_failed_job(queue_name, job_id)
            
            if success:
                self.logger.info("Document synchronization job retried successfully", job_id=job_id)
            else:
                self.logger.warning("Failed to retry document synchronization job", job_id=job_id)
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to retry document synchronization job",
                job_id=job_id,
                error=str(e)
            )
            raise DocumentSyncError(f"Failed to retry job: {e}")
    
    async def get_supported_systems(self) -> List[str]:
        """
        Get list of supported synchronization systems.
        
        Returns:
            List[str]: List of supported systems
        """
        return list(self.supported_systems)
    
    async def validate_system_connectivity(
        self,
        systems: List[str]
    ) -> Dict[str, bool]:
        """
        Validate connectivity to target systems.
        
        Args:
            systems: List of systems to validate
            
        Returns:
            Dict[str, bool]: System connectivity status
        """
        connectivity = {}
        
        for system in systems:
            if system not in self.supported_systems:
                connectivity[system] = False
                continue
            
            try:
                # In a real implementation, you would test actual connectivity
                # For now, we'll simulate connectivity checks
                if system == "typesense":
                    # Test Typesense connectivity
                    connectivity[system] = await self._test_typesense_connectivity()
                elif system == "qdrant":
                    # Test Qdrant connectivity
                    connectivity[system] = await self._test_qdrant_connectivity()
                else:
                    connectivity[system] = False
                    
            except Exception as e:
                self.logger.error(
                    "Failed to test connectivity",
                    system=system,
                    error=str(e)
                )
                connectivity[system] = False
        
        return connectivity
    
    async def _test_typesense_connectivity(self) -> bool:
        """
        Test Typesense connectivity.
        
        Returns:
            bool: True if connected
        """
        try:
            # In a real implementation, you would make an actual API call
            # For now, we'll simulate a successful connection
            self.logger.info("Testing Typesense connectivity")
            return True
        except Exception as e:
            self.logger.error("Typesense connectivity test failed", error=str(e))
            return False
    
    async def _test_qdrant_connectivity(self) -> bool:
        """
        Test Qdrant connectivity.
        
        Returns:
            bool: True if connected
        """
        try:
            # In a real implementation, you would make an actual API call
            # For now, we'll simulate a successful connection
            self.logger.info("Testing Qdrant connectivity")
            return True
        except Exception as e:
            self.logger.error("Qdrant connectivity test failed", error=str(e))
            return False


# Global service instance
document_sync_service = DocumentSyncService() 