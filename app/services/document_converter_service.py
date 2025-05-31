"""
Document converter service.
Handles document conversion job creation and management.
"""
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from app.core.logging_config import LoggerMixin
from app.models.requests.document_requests import DocumentConversionRequest
from app.models.responses.document_responses import DocumentConversionResponse
from app.utils.queue_manager import queue_manager
from app.utils.exceptions import (
    DocumentConversionError,
    ValidationError,
    QueueError,
)


class DocumentConverterService(LoggerMixin):
    """Service for handling document conversion operations."""
    
    def __init__(self):
        self.queue_manager = queue_manager
    
    async def convert_document(
        self,
        request: DocumentConversionRequest
    ) -> DocumentConversionResponse:
        """
        Create a document conversion job.
        
        Args:
            request: Document conversion request
            
        Returns:
            DocumentConversionResponse: Response with job details
            
        Raises:
            DocumentConversionError: If conversion job creation fails
            ValidationError: If request validation fails
        """
        try:
            self.logger.info(
                "Creating document conversion job",
                document_id=request.document_id,
                source_path=request.source_path,
                output_path=request.output_path
            )
            
            # Validate request
            await self._validate_conversion_request(request)
            
            # Create job in queue
            job_id = await self.queue_manager.add_document_conversion_job(
                document_id=request.document_id,
                source_path=request.source_path,
                output_path=request.output_path,
                conversion_options=request.conversion_options
            )
            
            # Calculate estimated completion time
            estimated_completion = datetime.utcnow() + timedelta(minutes=5)
            
            self.logger.info(
                "Document conversion job created successfully",
                document_id=request.document_id,
                job_id=job_id
            )
            
            return DocumentConversionResponse(
                success=True,
                message="Document conversion job created successfully",
                job_id=job_id,
                queue_name=self.queue_manager._connection_config.get("queue_names", {}).get("document_converter", "document_converter"),
                estimated_completion=estimated_completion,
                document_id=request.document_id,
                source_path=request.source_path,
                output_path=request.output_path
            )
            
        except ValidationError:
            raise
        except QueueError as e:
            self.logger.error(
                "Failed to create document conversion job",
                document_id=request.document_id,
                error=str(e)
            )
            raise DocumentConversionError(f"Failed to create conversion job: {e}")
        except Exception as e:
            self.logger.error(
                "Unexpected error in document conversion service",
                document_id=request.document_id,
                error=str(e)
            )
            raise DocumentConversionError(f"Unexpected error: {e}")
    
    async def _validate_conversion_request(
        self,
        request: DocumentConversionRequest
    ) -> None:
        """
        Validate document conversion request.
        
        Args:
            request: Document conversion request
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if source file exists (in a real implementation)
        # For now, we'll just validate the path format
        if not request.source_path.strip():
            raise ValidationError("Source path cannot be empty")
        
        if not request.output_path.strip():
            raise ValidationError("Output path cannot be empty")
        
        # Validate file extensions
        supported_input_formats = {'.pdf', '.docx', '.txt', '.md', '.html'}
        supported_output_formats = {'.md', '.txt', '.html', '.pdf'}
        
        source_ext = self._get_file_extension(request.source_path)
        output_ext = self._get_file_extension(request.output_path)
        
        if source_ext not in supported_input_formats:
            raise ValidationError(
                f"Unsupported input format: {source_ext}. "
                f"Supported formats: {', '.join(supported_input_formats)}"
            )
        
        if output_ext not in supported_output_formats:
            raise ValidationError(
                f"Unsupported output format: {output_ext}. "
                f"Supported formats: {', '.join(supported_output_formats)}"
            )
        
        # Validate conversion options
        if request.conversion_options:
            await self._validate_conversion_options(request.conversion_options)
    
    async def _validate_conversion_options(
        self,
        options: Dict[str, Any]
    ) -> None:
        """
        Validate conversion options.
        
        Args:
            options: Conversion options
            
        Raises:
            ValidationError: If options are invalid
        """
        valid_options = {
            'preserve_formatting',
            'extract_images',
            'include_metadata',
            'quality',
            'compression'
        }
        
        for key in options.keys():
            if key not in valid_options:
                raise ValidationError(
                    f"Invalid conversion option: {key}. "
                    f"Valid options: {', '.join(valid_options)}"
                )
        
        # Validate specific option values
        if 'quality' in options:
            quality = options['quality']
            if not isinstance(quality, (int, float)) or not 0 <= quality <= 100:
                raise ValidationError("Quality must be a number between 0 and 100")
    
    def _get_file_extension(self, file_path: str) -> str:
        """
        Get file extension from path.
        
        Args:
            file_path: File path
            
        Returns:
            str: File extension (including dot)
        """
        import os
        return os.path.splitext(file_path.lower())[1]
    
    async def get_conversion_status(
        self,
        job_id: str
    ) -> Dict[str, Any]:
        """
        Get conversion job status.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict[str, Any]: Job status information
            
        Raises:
            DocumentConversionError: If status retrieval fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["document_converter"]
            
            status = await self.queue_manager.get_job_status(queue_name, job_id)
            
            self.logger.info(
                "Retrieved conversion job status",
                job_id=job_id,
                status=status.get("status")
            )
            
            return status
            
        except Exception as e:
            self.logger.error(
                "Failed to get conversion job status",
                job_id=job_id,
                error=str(e)
            )
            raise DocumentConversionError(f"Failed to get job status: {e}")
    
    async def retry_conversion(
        self,
        job_id: str
    ) -> bool:
        """
        Retry a failed conversion job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if retry was successful
            
        Raises:
            DocumentConversionError: If retry fails
        """
        try:
            from app.core.config import settings
            queue_name = settings.queue_names["document_converter"]
            
            success = await self.queue_manager.retry_failed_job(queue_name, job_id)
            
            if success:
                self.logger.info("Conversion job retried successfully", job_id=job_id)
            else:
                self.logger.warning("Failed to retry conversion job", job_id=job_id)
            
            return success
            
        except Exception as e:
            self.logger.error(
                "Failed to retry conversion job",
                job_id=job_id,
                error=str(e)
            )
            raise DocumentConversionError(f"Failed to retry job: {e}")


# Global service instance
document_converter_service = DocumentConverterService() 