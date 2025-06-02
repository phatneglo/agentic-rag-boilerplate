"""
Document processing API routes.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Query
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


@router.get(
    "/search",
    summary="Search documents in Typesense",
    description="Search indexed documents using Typesense full-text search with faceted filtering"
)
async def search_documents(
    q: Optional[str] = Query("*", description="Search query (* for all documents)"),
    query_by: str = Query("title,description,summary", description="Fields to search in"),
    filter_by: Optional[str] = Query(None, description="Filter conditions (e.g., type:=document)"),
    facet_by: Optional[str] = Query(None, description="Facet fields (e.g., type,category,language)"),
    sort_by: Optional[str] = Query("created_at:desc", description="Sort by field and order"),
    page: int = Query(1, description="Page number", ge=1),
    per_page: int = Query(10, description="Results per page", ge=1, le=100),
    include_facet_counts: bool = Query(True, description="Include facet counts in response"),
    highlight_full_fields: Optional[str] = Query("title,description,summary", description="Fields to highlight"),
    use_vector_search: bool = Query(False, description="Enable semantic/vector search"),
) -> Dict[str, Any]:
    """
    Search documents using Typesense with full-text and semantic search capabilities.
    
    This endpoint provides powerful search functionality with:
    - Full-text search across multiple fields
    - Faceted filtering by document type, category, language, etc.
    - Semantic/vector search using auto-embeddings
    - Pagination and sorting
    - Search highlighting
    - Facet counts for building filter UIs
    
    Args:
        q: Search query string
        query_by: Comma-separated list of fields to search in
        filter_by: Filter conditions (e.g., "type:=document && language:=en")
        facet_by: Comma-separated list of fields to facet by
        sort_by: Sort field and order (e.g., "created_at:desc")
        page: Page number (1-based)
        per_page: Number of results per page
        include_facet_counts: Include facet counts in response
        highlight_full_fields: Fields to highlight in search results
        use_vector_search: Enable semantic search using embeddings
        
    Returns:
        Dict[str, Any]: Search results with documents, facets, and metadata
        
    Raises:
        HTTPException: If search fails or validation errors occur
    """
    try:
        # Import Typesense client here to avoid circular imports
        import typesense
        from app.core.config import settings
        
        # Initialize Typesense client
        client = typesense.Client({
            'nodes': [{
                'host': settings.typesense_host,
                'port': settings.typesense_port,
                'protocol': settings.typesense_protocol
            }],
            'api_key': settings.typesense_api_key,
            'connection_timeout_seconds': 10
        })
        
        # Build search parameters
        # Ensure we have a valid query (default to "*" for browse all)
        search_query = q.strip() if q else "*"
        if not search_query:
            search_query = "*"
        
        logger.info(
            "Document search request",
            query=search_query,
            query_by=query_by,
            filter_by=filter_by,
            page=page,
            per_page=per_page,
            use_vector_search=use_vector_search
        )
        
        search_params = {
            'q': search_query,
            'query_by': query_by,
            'per_page': per_page,
            'page': page,
            'sort_by': sort_by,
        }
        
        # Add optional parameters
        if filter_by:
            search_params['filter_by'] = filter_by
            
        if facet_by:
            search_params['facet_by'] = facet_by
            
        if highlight_full_fields:
            search_params['highlight_full_fields'] = highlight_full_fields
            
        if include_facet_counts and facet_by:
            search_params['max_facet_values'] = 50
            
        # Add vector search for semantic similarity
        if use_vector_search and len(search_query.strip()) > 3 and search_query != "*":
            # Use Typesense auto-embedding with vector search
            search_params['vector_query'] = f'content_embedding:([], k:{per_page})'
            search_params['q'] = search_query  # Typesense will auto-embed this query
        
        # Execute search
        try:
            results = client.collections[settings.typesense_collection_name].documents.search(search_params)
            
            # Format response for File Browser
            response = {
                "success": True,
                "query": search_query,
                "found": results.get('found', 0),
                "out_of": results.get('out_of', 0),
                "page": page,
                "per_page": per_page,
                "total_pages": (results.get('found', 0) + per_page - 1) // per_page,
                "search_time_ms": results.get('search_time_ms', 0),
                "documents": [],
                "facet_counts": results.get('facet_counts', []) if include_facet_counts else [],
                "metadata": {
                    "search_params": search_params,
                    "vector_search_enabled": use_vector_search,
                    "collection": settings.typesense_collection_name
                }
            }
            
            # Process search hits
            for hit in results.get('hits', []):
                doc = hit['document']
                search_result = {
                    "id": doc.get('id'),
                    "title": doc.get('title', 'Untitled'),
                    "description": doc.get('description', ''),
                    "summary": doc.get('summary', ''),
                    "type": doc.get('type', 'document'),
                    "category": doc.get('category', 'general'),
                    "authors": doc.get('authors', []),
                    "tags": doc.get('tags', []),
                    "date": doc.get('date', ''),
                    "language": doc.get('language', 'en'),
                    "word_count": doc.get('word_count', 0),
                    "page_count": doc.get('page_count', 0),
                    "file_path": doc.get('file_path', ''),
                    "original_filename": doc.get('original_filename', ''),
                    "created_at": doc.get('created_at', 0),
                    "updated_at": doc.get('updated_at', 0),
                    # Search-specific fields
                    "score": hit.get('text_match_info', {}).get('score', 0),
                    "highlights": hit.get('highlights', []),
                    "text_match": hit.get('text_match', 0)
                }
                response["documents"].append(search_result)
            
            logger.info(
                "Document search completed",
                query=search_query,
                found=response["found"],
                search_time_ms=response["search_time_ms"]
            )
            
            return response
            
        except typesense.exceptions.RequestMalformed as e:
            logger.error("Malformed search request", error=str(e), search_params=search_params)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Bad Request",
                    "message": f"Invalid search parameters: {str(e)}",
                    "search_params": search_params
                }
            )
            
        except typesense.exceptions.ObjectNotFound as e:
            logger.error("Collection not found", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "Not Found",
                    "message": "Documents collection not found. Please index some documents first.",
                    "collection": settings.typesense_collection_name
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Unexpected error in document search",
            query=search_query if 'search_query' in locals() else q,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred during search"
            }
        ) 