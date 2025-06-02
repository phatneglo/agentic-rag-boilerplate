"""
Qdrant indexer worker.
Processes Qdrant indexing jobs from the Redis queue using LlamaIndex + Qdrant integration.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis
from llama_index.core import Document, VectorStoreIndex, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import QdrantIndexingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class QdrantIndexerWorker:
    """Worker for processing Qdrant indexing jobs using LlamaIndex integration."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
        self.qdrant_client = None
        self.vector_store = None
        self.index = None
        self.collection_name = settings.qdrant_collection_name
        self.node_parser = None
        self.openai_api_key = settings.openai_api_key
        self.qdrant_host = settings.qdrant_host
        self.qdrant_port = settings.qdrant_port
        self.qdrant_api_key = settings.qdrant_api_key
        self.is_running = False
    
    async def setup(self):
        """Setup Redis connection, worker, and LlamaIndex + Qdrant components."""
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
            logger.info("Redis connection established for Qdrant indexer worker")
            
            logger.info("Setting up LlamaIndex settings")
            
            # Configure LlamaIndex settings
            Settings.llm = OpenAI(
                model="gpt-4o-mini",
                api_key=self.openai_api_key,
                temperature=0.1
            )
            Settings.embed_model = OpenAIEmbedding(
                model="text-embedding-3-small", 
                api_key=self.openai_api_key
            )
            Settings.chunk_size = 512  # Standard chunk size
            
            # Initialize Qdrant client
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                api_key=self.qdrant_api_key,
                https=False,
                prefer_grpc=False,
            )
            
            # DON'T manually create collection - let LlamaIndex handle it
            # This is the key insight from the successful test
            
            # Initialize vector store - LlamaIndex will create collection as needed
            self.vector_store = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=self.collection_name,
                # Let LlamaIndex handle collection creation automatically
            )
            
            # Create storage context - this is crucial!
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            
            # Setup node parser for chunking
            self.node_parser = SentenceSplitter(
                chunk_size=1024,
                chunk_overlap=200,
                paragraph_separator="\n\n",
                secondary_chunking_regex="[.!?;]",
            )
            
            logger.info("LlamaIndex + Qdrant components initialized successfully")
            
            # Create worker - BullMQ Python API
            # Note: The worker starts processing automatically when instantiated
            self.worker = Worker(
                settings.queue_names["qdrant_indexer"],
                self.process_job,
            )
            
            self.is_running = True
            
            logger.info(
                "Qdrant indexer worker initialized and started",
                queue_name=settings.queue_names["qdrant_indexer"]
            )
            
        except Exception as e:
            logger.error(f"Failed to setup Qdrant indexer worker: {e}", exc_info=True)
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a Qdrant indexing job using LlamaIndex.
        
        Args:
            job: BullMQ job object
            
        Returns:
            Dict[str, Any]: Job result
            
        Raises:
            QdrantIndexingError: If indexing fails
        """
        job_id = job.id
        job_data = job.data
        
        try:
            logger.info(
                "Processing Qdrant indexing job",
                job_id=job_id,
                document_id=job_data.get("document_id")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["qdrant_indexer"],
                event_type="started",
                document_id=job_data.get("document_id")
            )
            
            # Extract job data
            document_id = job_data["document_id"]  # This is the Typesense document ID
            markdown_path = job_data["markdown_path"]
            metadata = job_data["metadata"]
            indexing_options = job_data.get("indexing_options", {})
            
            # Update job progress
            await job.updateProgress(10)
            
            # Validate markdown file exists
            if not os.path.exists(markdown_path):
                raise QdrantIndexingError(f"Markdown file not found: {markdown_path}")
            
            # Read markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            await job.updateProgress(20)
            
            # Create document chunks using LlamaIndex
            document_chunks = await self._create_document_chunks(
                content, document_id, metadata
            )
            
            await job.updateProgress(60)
            
            # Index to Qdrant using LlamaIndex
            result = await self._index_documents_to_qdrant(document_chunks, document_id)
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "document_id": document_id,
                "collection_name": self.collection_name,
                "chunks_created": len(document_chunks),
                "indexing_result": result,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Qdrant indexing job completed successfully",
                job_id=job_id,
                document_id=document_id,
                chunks_created=len(document_chunks)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["qdrant_indexer"],
                event_type="completed",
                document_id=document_id,
                result=job_result
            )
            
            return job_result
            
        except Exception as e:
            logger.error(
                "Qdrant indexing job failed",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["qdrant_indexer"],
                event_type="failed",
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            raise QdrantIndexingError(f"Qdrant indexing failed: {e}")
    
    async def _create_document_chunks(
        self,
        content: str,
        document_id: str,
        metadata: Dict[str, Any]
    ) -> List[Document]:
        """Create document chunks using LlamaIndex node parser."""
        logger.info(
            "Creating document chunks",
            document_id=document_id,
            content_length=len(content)
        )
        
        try:
            # Create a Document for parsing
            document = Document(
                text=content,
                metadata=metadata,
            )
            
            # Parse document into chunks
            def parse_chunks():
                return self.node_parser.get_nodes_from_documents([document])
            
            loop = asyncio.get_event_loop()
            nodes = await loop.run_in_executor(None, parse_chunks)
            
            # Create LlamaIndex Documents from the chunks
            documents = []
            for i, node in enumerate(nodes):
                doc = Document(
                    text=node.text,
                    metadata={
                        **metadata,
                        "document_id": document_id,
                        "chunk_id": f"{document_id}_{i}",
                        "chunk_index": i,
                        "total_chunks": len(nodes)
                    },
                    id_=str(uuid.uuid4())  # Generate proper UUID for each chunk
                )
                documents.append(doc)
            
            logger.info(
                "Document chunks created",
                document_id=document_id,
                num_chunks=len(documents)
            )
            
            return documents
            
        except Exception as e:
            logger.error("Document chunking failed", error=str(e))
            raise QdrantIndexingError(f"Failed to create document chunks: {e}")
    
    async def _index_documents_to_qdrant(
        self,
        documents: List[Document],
        document_id: str
    ) -> Dict[str, Any]:
        """Index document chunks to Qdrant using proper LlamaIndex approach."""
        logger.info(
            "Indexing document chunks to Qdrant",
            document_id=document_id,
            num_chunks=len(documents)
        )
        
        try:
            # Remove existing chunks for this document first
            await self._remove_existing_chunks(document_id)
            
            # Index documents using VectorStoreIndex with storage context
            # This is the key - using the storage context we created in setup()
            index = VectorStoreIndex.from_documents(
                documents,
                storage_context=self.storage_context,
                show_progress=False  # Disable progress bar in worker
            )
            
            logger.info(
                "Document chunks indexed successfully",
                document_id=document_id,
                num_chunks=len(documents)
            )
            
            return {
                "success": True,
                "document_id": document_id,
                "collection": self.collection_name,
                "chunks_indexed": len(documents),
                "index_created": True,
            }
            
        except Exception as e:
            logger.error("Qdrant indexing failed", error=str(e))
            raise QdrantIndexingError(f"Failed to index to Qdrant: {e}")
    
    async def _remove_existing_chunks(self, document_id: str):
        """Remove existing document chunks from Qdrant."""
        try:
            def remove_chunks():
                # Remove by metadata filter
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="metadata.document_id",
                                    match=models.MatchValue(value=document_id),
                                ),
                            ],
                        )
                    ),
                )
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, remove_chunks)
            
            logger.info(f"Removed existing chunks for document {document_id}")
            
        except Exception as e:
            logger.warning(f"Failed to remove existing chunks: {e}")
            # Don't fail the job for this, just log the warning
    
    async def query_documents(
        self,
        query: str,
        document_id: str = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """Query documents in Qdrant (utility method for testing)."""
        try:
            if not self.index:
                # Create a query engine from the vector store
                index = VectorStoreIndex.from_vector_store(self.vector_store)
                query_engine = index.as_query_engine(
                    similarity_top_k=top_k,
                    response_mode="tree_summarize"
                )
            else:
                query_engine = self.index.as_query_engine(
                    similarity_top_k=top_k,
                    response_mode="tree_summarize"
                )
            
            def execute_query():
                return query_engine.query(query)
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, execute_query)
            
            return {
                "query": query,
                "response": str(response),
                "source_nodes": [
                    {
                        "text": node.text,
                        "metadata": node.metadata,
                        "score": node.score
                    }
                    for node in response.source_nodes
                ],
                "top_k": top_k,
            }
            
        except Exception as e:
            logger.error("Qdrant query failed", error=str(e))
            raise QdrantIndexingError(f"Query failed: {e}")
    
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
        
        if self.qdrant_client:
            self.qdrant_client.close()
        
        logger.info("Qdrant indexer worker cleaned up")


async def main():
    """Main function to run the Qdrant indexer worker."""
    worker = QdrantIndexerWorker()
    
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
        
        logger.info("Qdrant indexer worker is ready and processing jobs...")
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