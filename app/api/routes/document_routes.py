"""
Document processing API routes.
"""
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from app.models.requests.document_requests import (
    DocumentConversionRequest,
    TypesenseIndexingRequest,
    QdrantIndexingRequest,
    DocumentSyncRequest,
)
from app.models.responses.document_responses import (
    DocumentConversionResponse,
    TypesenseIndexingResponse,
    QdrantIndexingResponse,
    DocumentSyncResponse,
    JobStatusResponse,
    ErrorResponse,
)
from app.services.document_converter_service import document_converter_service
from app.services.typesense_indexer_service import typesense_indexer_service
from app.services.qdrant_indexer_service import qdrant_indexer_service
from app.services.document_sync_service import document_sync_service
from app.utils.exceptions import (
    DocumentProcessingError,
    ValidationError,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/convert",
    response_model=DocumentConversionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convert document to Markdown",
    description="Create a job to convert a document to Markdown format"
)
async def convert_document(
    request: DocumentConversionRequest
) -> DocumentConversionResponse:
    """
    Convert a document to Markdown format.
    
    This endpoint creates a background job to convert a document from various formats
    (PDF, DOCX, TXT, HTML) to Markdown format.
    
    Args:
        request: Document conversion request
        
    Returns:
        DocumentConversionResponse: Job details and estimated completion time
        
    Raises:
        HTTPException: If validation fails or job creation fails
    """
    try:
        logger.info(
            "Document conversion request received",
            document_id=request.document_id,
            source_path=request.source_path
        )
        
        response = await document_converter_service.convert_document(request)
        
        logger.info(
            "Document conversion job created",
            document_id=request.document_id,
            job_id=response.job_id
        )
        
        return response
        
    except ValidationError as e:
        logger.error(
            "Validation error in document conversion",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except DocumentProcessingError as e:
        logger.error(
            "Document processing error",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Document Processing Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except Exception as e:
        logger.error(
            "Unexpected error in document conversion",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )


@router.post(
    "/index/typesense",
    response_model=TypesenseIndexingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index document to Typesense",
    description="Create a job to index a document to Typesense search engine"
)
async def index_to_typesense(
    request: TypesenseIndexingRequest
) -> TypesenseIndexingResponse:
    """
    Index a document to Typesense search engine.
    
    This endpoint creates a background job to index document content and metadata
    to a Typesense collection for full-text search capabilities.
    
    Args:
        request: Typesense indexing request
        
    Returns:
        TypesenseIndexingResponse: Job details and estimated completion time
        
    Raises:
        HTTPException: If validation fails or job creation fails
    """
    try:
        logger.info(
            "Typesense indexing request received",
            document_id=request.document_id,
            collection_name=request.collection_name
        )
        
        response = await typesense_indexer_service.index_document(request)
        
        logger.info(
            "Typesense indexing job created",
            document_id=request.document_id,
            job_id=response.job_id
        )
        
        return response
        
    except ValidationError as e:
        logger.error(
            "Validation error in Typesense indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except DocumentProcessingError as e:
        logger.error(
            "Document processing error in Typesense indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Document Processing Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except Exception as e:
        logger.error(
            "Unexpected error in Typesense indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )


@router.post(
    "/index/qdrant",
    response_model=QdrantIndexingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index document to Qdrant",
    description="Create a job to index a document to Qdrant vector database"
)
async def index_to_qdrant(
    request: QdrantIndexingRequest
) -> QdrantIndexingResponse:
    """
    Index a document to Qdrant vector database.
    
    This endpoint creates a background job to vectorize document content and store
    it in a Qdrant collection for semantic search capabilities.
    
    Args:
        request: Qdrant indexing request
        
    Returns:
        QdrantIndexingResponse: Job details and estimated completion time
        
    Raises:
        HTTPException: If validation fails or job creation fails
    """
    try:
        logger.info(
            "Qdrant indexing request received",
            document_id=request.document_id,
            collection_name=request.collection_name
        )
        
        response = await qdrant_indexer_service.index_document(request)
        
        logger.info(
            "Qdrant indexing job created",
            document_id=request.document_id,
            job_id=response.job_id
        )
        
        return response
        
    except ValidationError as e:
        logger.error(
            "Validation error in Qdrant indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except DocumentProcessingError as e:
        logger.error(
            "Document processing error in Qdrant indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Document Processing Error",
                "message": str(e),
                "document_id": request.document_id
            }
        )
    except Exception as e:
        logger.error(
            "Unexpected error in Qdrant indexing",
            document_id=request.document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        )


@router.post(
    "/sync",
    response_model=DocumentSyncResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Synchronize document across systems",
    description="Create a job to synchronize a document across multiple systems"
)
async def sync_document(
    request: DocumentSyncRequest
) -> DocumentSyncResponse:
    """
    Synchronize a document across multiple systems.
    
    This endpoint creates a background job to synchronize a document across
    multiple target systems (Typesense, Qdrant, etc.).
    
    Args:
        request: Document synchronization request
        
    Returns:
        DocumentSyncResponse: Job details and estimated completion time
        
    Raises:
        HTTPException: If validation fails or job creation fails
    """
    try:
        logger.info(
            "Document sync request received",
            source_document_id=request.source_document_id,
            target_systems=request.target_systems
        )
        
        response = await document_sync_service.sync_document(request)
        
        logger.info(
            "Document sync job created",
            source_document_id=request.source_document_id,
            job_id=response.job_id
        )
        
        return response
        
    except ValidationError as e:
        logger.error(
            "Validation error in document sync",
            source_document_id=request.source_document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Validation Error",
                "message": str(e),
                "source_document_id": request.source_document_id
            }
        )
    except DocumentProcessingError as e:
        logger.error(
            "Document processing error in sync",
            source_document_id=request.source_document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Document Processing Error",
                "message": str(e),
                "source_document_id": request.source_document_id
            }
        )
    except Exception as e:
        logger.error(
            "Unexpected error in document sync",
            source_document_id=request.source_document_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }
        ) 