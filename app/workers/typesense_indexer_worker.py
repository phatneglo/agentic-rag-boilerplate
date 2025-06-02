"""
Typesense indexer worker.
Processes Typesense indexing jobs from the Redis queue using Typesense client.
"""
import asyncio
import json
import os
import sys
from typing import Any, Dict, List
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis
import typesense

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import TypesenseIndexingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class TypesenseIndexerWorker:
    """Worker for processing Typesense indexing jobs with metadata and auto-embeddings."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
        self.typesense_client = None
        self.collection_name = "documents"
        self.is_running = False
    
    async def setup(self):
        """Setup Redis connection, worker, and Typesense client."""
        try:
            # Create Redis connection for health checks
            self.redis_connection = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
            )
            
            # Test connection
            await self.redis_connection.ping()
            logger.info("Redis connection established for Typesense indexer worker")
            
            # Initialize Typesense client
            self.typesense_client = typesense.Client({
                'nodes': [{
                    'host': settings.typesense_host,
                    'port': settings.typesense_port,
                    'protocol': settings.typesense_protocol
                }],
                'api_key': settings.typesense_api_key,
                'connection_timeout_seconds': 10
            })
            
            # Ensure collection exists
            await self._ensure_collection_exists()
            
            logger.info("Typesense client initialized successfully")
            
            # Create worker - BullMQ Python API
            # Note: The worker starts processing automatically when instantiated
            self.worker = Worker(
                settings.queue_names["typesense_indexer"],
                self.process_job,
            )
            
            self.is_running = True
            
            logger.info(
                "Typesense indexer worker initialized and started",
                queue_name=settings.queue_names["typesense_indexer"]
            )
            
        except Exception as e:
            logger.error("Failed to setup Typesense indexer worker", error=str(e))
            raise
    
    async def _ensure_collection_exists(self):
        """Ensure the documents collection exists with proper schema."""
        try:
            # Define collection schema with auto-embedding using OpenAI API
            collection_schema = {
                'name': self.collection_name,
                'fields': [
                    {'name': 'id', 'type': 'string'},
                    {'name': 'title', 'type': 'string'},
                    {'name': 'description', 'type': 'string'},
                    {'name': 'summary', 'type': 'string'},
                    {'name': 'type', 'type': 'string', 'facet': True},
                    {'name': 'category', 'type': 'string', 'facet': True},
                    {'name': 'authors', 'type': 'string[]', 'facet': True},
                    {'name': 'tags', 'type': 'string[]', 'facet': True},
                    {'name': 'date', 'type': 'string', 'optional': True},
                    {'name': 'language', 'type': 'string', 'facet': True},
                    {'name': 'word_count', 'type': 'int32'},
                    {'name': 'page_count', 'type': 'int32', 'optional': True},
                    {'name': 'file_path', 'type': 'string'},
                    {'name': 'original_filename', 'type': 'string'},
                    {'name': 'created_at', 'type': 'int64'},
                    {'name': 'updated_at', 'type': 'int64'},
                    # Auto-embedding field using OpenAI API - combines relevant content fields
                    {
                        'name': 'content_embedding',
                        'type': 'float[]',
                        'embed': {
                            'from': ['title', 'description', 'authors', 'type', 'category', 'tags'],
                            'model_config': {
                                'model_name': 'openai/text-embedding-3-small',
                                'api_key': settings.openai_api_key
                            }
                        }
                    },
                ],
                'default_sorting_field': 'created_at'
            }
            
            def create_collection():
                try:
                    # Check if collection exists
                    self.typesense_client.collections[self.collection_name].retrieve()
                    logger.info(f"Collection '{self.collection_name}' already exists")
                except typesense.exceptions.ObjectNotFound:
                    # Create collection
                    self.typesense_client.collections.create(collection_schema)
                    logger.info(f"Created collection '{self.collection_name}' with OpenAI auto-embedding")
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, create_collection)
            
        except Exception as e:
            logger.error("Failed to ensure collection exists", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a Typesense indexing job with metadata and embeddings.
        
        Args:
            job: BullMQ job object
            
        Returns:
            Dict[str, Any]: Job result
            
        Raises:
            TypesenseIndexingError: If indexing fails
        """
        job_id = job.id
        job_data = job.data
        
        try:
            logger.info(
                "Processing Typesense indexing job",
                job_id=job_id,
                document_id=job_data.get("document_id")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["typesense_indexer"],
                event_type="started",
                document_id=job_data.get("document_id")
            )
            
            # Extract job data
            document_id = job_data["document_id"]
            metadata = job_data["metadata"]
            embeddings = job_data.get("embeddings", {})
            indexing_options = job_data.get("indexing_options", {})
            
            # Update job progress
            await job.updateProgress(10)
            
            # Prepare document for Typesense
            typesense_document = await self._prepare_typesense_document(
                document_id, metadata, embeddings
            )
            
            await job.updateProgress(50)
            
            # Index document to Typesense
            result = await self._index_to_typesense(typesense_document)
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "document_id": document_id,
                "collection_name": self.collection_name,
                "indexing_result": result,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Typesense indexing job completed successfully",
                job_id=job_id,
                document_id=document_id,
                collection_name=self.collection_name
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["typesense_indexer"],
                event_type="completed",
                document_id=document_id,
                result=job_result
            )
            
            return job_result
            
        except Exception as e:
            logger.error(
                "Typesense indexing job failed",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["typesense_indexer"],
                event_type="failed",
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            raise TypesenseIndexingError(f"Typesense indexing failed: {e}")
    
    async def _prepare_typesense_document(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        embeddings: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """Prepare document for Typesense indexing."""
        current_timestamp = int(datetime.utcnow().timestamp())
        
        # Typesense will auto-generate embeddings using OpenAI API
        # No need to manually create embeddings here
        typesense_doc = {
            'id': document_id,
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'summary': metadata.get('summary', ''),
            'type': metadata.get('type', 'document'),
            'category': metadata.get('category', 'general'),
            'authors': metadata.get('authors', []),
            'tags': metadata.get('tags', []),
            'date': metadata.get('date', ''),
            'language': metadata.get('language', 'en'),
            'word_count': metadata.get('word_count', 0),
            'page_count': metadata.get('page_count', 0),
            'file_path': metadata.get('file_path', ''),
            'original_filename': metadata.get('original_filename', ''),
            'created_at': current_timestamp,
            'updated_at': current_timestamp,
            # Note: embedding fields will be auto-generated by Typesense from title, description, summary
        }
        
        return typesense_doc
    
    async def _index_to_typesense(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Index document to Typesense collection."""
        logger.info(
            "Indexing document to Typesense",
            document_id=document["id"],
            collection_name=self.collection_name
        )
        
        try:
            def index_document():
                # Upsert document (create or update)
                return self.typesense_client.collections[self.collection_name].documents.upsert(document)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, index_document)
            
            logger.info(
                "Document indexed successfully",
                document_id=document["id"],
                typesense_result=result
            )
            
            return {
                "success": True,
                "document_id": document["id"],
                "collection": self.collection_name,
                "typesense_response": result,
                "indexed_fields": len(document),
                "auto_embeddings": True  # Embeddings are auto-generated by Typesense
            }
            
        except Exception as e:
            logger.error("Typesense indexing failed", error=str(e))
            raise TypesenseIndexingError(f"Failed to index document: {e}")
    
    async def search_documents(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 10,
        use_vector_search: bool = True
    ) -> Dict[str, Any]:
        """Search documents in Typesense (utility method for testing)."""
        try:
            search_params = {
                'q': query,
                'query_by': 'title,description,summary',
                'limit': limit,
                'highlight_full_fields': 'title,description,summary'
            }
            
            # Add vector search if enabled and query is meaningful
            if use_vector_search and len(query.strip()) > 3:
                # Use Typesense auto-embedding with vector search
                # This will automatically generate embeddings for the query using OpenAI
                search_params['vector_query'] = f'content_embedding:([], k:{limit})'
                search_params['q'] = query  # Typesense will auto-embed this query
            
            # Add filters if provided
            if filters:
                filter_parts = []
                for key, value in filters.items():
                    if isinstance(value, list):
                        filter_parts.append(f"{key}:[{','.join(map(str, value))}]")
                    else:
                        filter_parts.append(f"{key}:={value}")
                
                if filter_parts:
                    search_params['filter_by'] = ' && '.join(filter_parts)
            
            def search():
                return self.typesense_client.collections[self.collection_name].documents.search(search_params)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, search)
            
            return result
            
        except Exception as e:
            logger.error("Typesense search failed", error=str(e))
            raise TypesenseIndexingError(f"Search failed: {e}")
    
    async def stop(self):
        """Stop the worker gracefully."""
        if self.worker and self.is_running:
            try:
                await self.worker.close()
                self.is_running = False
                logger.info("Worker stopped gracefully")
            except Exception as e:
                logger.error("Error stopping worker", error=str(e))
                self.is_running = False
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.stop()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Typesense indexer worker cleaned up")


async def main():
    """Main function to run the Typesense indexer worker."""
    worker = TypesenseIndexerWorker()
    
    try:
        await worker.setup()
        
        # Create an event that will be triggered for shutdown
        shutdown_event = asyncio.Event()
        
        def signal_handler(sig, frame):
            logger.info("Received shutdown signal")
            shutdown_event.set()
        
        # Register signal handlers for graceful shutdown
        import signal
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        logger.info("Typesense indexer worker is ready and processing jobs...")
        logger.info("Press Ctrl+C to stop the worker")
        
        # Wait until the shutdown event is set
        await shutdown_event.wait()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down gracefully...")
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        raise
    finally:
        await worker.cleanup()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main()) 