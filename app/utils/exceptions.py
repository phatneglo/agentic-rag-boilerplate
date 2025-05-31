"""
Custom exceptions for the document processing application.
"""
from typing import Any, Dict, Optional


class DocumentProcessingError(Exception):
    """Base exception for document processing errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class QueueError(DocumentProcessingError):
    """Exception raised for queue-related errors."""
    pass


class RedisConnectionError(QueueError):
    """Exception raised when Redis connection fails."""
    pass


class JobCreationError(QueueError):
    """Exception raised when job creation fails."""
    pass


class JobProcessingError(DocumentProcessingError):
    """Exception raised during job processing."""
    pass


class DocumentConversionError(DocumentProcessingError):
    """Exception raised during document conversion."""
    pass


class IndexingError(DocumentProcessingError):
    """Exception raised during document indexing."""
    pass


class TypesenseIndexingError(IndexingError):
    """Exception raised during Typesense indexing."""
    pass


class QdrantIndexingError(IndexingError):
    """Exception raised during Qdrant indexing."""
    pass


class DocumentSyncError(DocumentProcessingError):
    """Exception raised during document synchronization."""
    pass


class ValidationError(DocumentProcessingError):
    """Exception raised for validation errors."""
    pass


class ConfigurationError(DocumentProcessingError):
    """Exception raised for configuration errors."""
    pass


class ExternalServiceError(DocumentProcessingError):
    """Exception raised when external service calls fail."""
    
    def __init__(
        self,
        message: str,
        service_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        self.service_name = service_name
        self.status_code = status_code
        self.response_body = response_body
        
        details = {
            "service_name": service_name,
            "status_code": status_code,
            "response_body": response_body,
            **kwargs
        }
        
        super().__init__(message, details=details)


class FileProcessingError(DocumentProcessingError):
    """Exception raised during file processing."""
    
    def __init__(
        self,
        message: str,
        file_path: str = None,
        file_type: str = None,
        **kwargs
    ):
        self.file_path = file_path
        self.file_type = file_type
        
        details = {
            "file_path": file_path,
            "file_type": file_type,
            **kwargs
        }
        
        super().__init__(message, details=details)


class RateLimitError(DocumentProcessingError):
    """Exception raised when rate limits are exceeded."""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        **kwargs
    ):
        self.retry_after = retry_after
        
        details = {
            "retry_after": retry_after,
            **kwargs
        }
        
        super().__init__(message, details=details)


class AuthenticationError(DocumentProcessingError):
    """Exception raised for authentication errors."""
    pass


class AuthorizationError(DocumentProcessingError):
    """Exception raised for authorization errors."""
    pass 