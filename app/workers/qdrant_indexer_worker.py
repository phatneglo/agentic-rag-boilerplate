"""
Qdrant indexer worker.
Processes Qdrant indexing jobs from the Redis queue.
"""
import asyncio
import os
import sys
from typing import Any, Dict, List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import QdrantIndexingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class QdrantIndexerWorker:
    """Worker for processing Qdrant indexing jobs."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
    
    async def setup(self):
        """Setup Redis connection and worker."""
        try:
            # Create Redis connection
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
            
            # Create worker
            self.worker = Worker(
                settings.queue_names["qdrant_indexer"],
                self.process_job,
                connection={"connection": self.redis_connection},
                concurrency=settings.worker_concurrency,
            )
            
            logger.info(
                "Qdrant indexer worker initialized",
                queue_name=settings.queue_names["qdrant_indexer"],
                concurrency=settings.worker_concurrency
            )
            
        except Exception as e:
            logger.error("Failed to setup Qdrant indexer worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a Qdrant indexing job.
        
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
                document_id=job_data.get("document_id"),
                collection_name=job_data.get("collection_name")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["qdrant_indexer"],
                event_type="started",
                document_id=job_data.get("document_id")
            )
            
            # Extract job data
            document_id = job_data["document_id"]
            content = job_data["content"]
            metadata = job_data.get("metadata", {})
            collection_name = job_data["collection_name"]
            
            # Update job progress
            await job.updateProgress(10)
            
            # Simulate Qdrant indexing process
            # In a real implementation, you would:
            # 1. Connect to Qdrant
            # 2. Generate embeddings for the content
            # 3. Store the vector and metadata in Qdrant
            
            await job.updateProgress(30)
            
            # Generate embeddings (simulated)
            embeddings = await self._generate_embeddings(content)
            
            await job.updateProgress(60)
            
            # Index to Qdrant
            result = await self._index_to_qdrant(
                document_id, embeddings, metadata, collection_name
            )
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "document_id": document_id,
                "collection_name": collection_name,
                "indexing_result": result,
                "processed_at": job_data.get("created_at"),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Qdrant indexing job completed successfully",
                job_id=job_id,
                document_id=document_id,
                collection_name=collection_name
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
    
    async def _generate_embeddings(self, content: str) -> List[float]:
        """Generate embeddings for the content."""
        # Simulate embedding generation
        await asyncio.sleep(2)  # Simulate processing time for embedding generation
        
        logger.info(
            "Generating embeddings",
            content_length=len(content)
        )
        
        # In a real implementation, you would:
        # 1. Use a sentence transformer or OpenAI embeddings
        # 2. Generate actual embeddings
        # 
        # Example with sentence-transformers:
        # from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # embeddings = model.encode(content)
        # return embeddings.tolist()
        #
        # Example with OpenAI:
        # import openai
        # response = openai.Embedding.create(
        #     input=content,
        #     model="text-embedding-ada-002"
        # )
        # return response['data'][0]['embedding']
        
        # Simulate 384-dimensional embeddings (typical for sentence transformers)
        import random
        random.seed(hash(content) % 2**32)  # Deterministic for same content
        return [random.uniform(-1, 1) for _ in range(384)]
    
    async def _index_to_qdrant(
        self,
        document_id: str,
        embeddings: List[float],
        metadata: Dict[str, Any],
        collection_name: str
    ) -> Dict[str, Any]:
        """Index document to Qdrant."""
        # Simulate Qdrant indexing
        await asyncio.sleep(1)  # Simulate processing time
        
        logger.info(
            "Indexing document to Qdrant",
            document_id=document_id,
            collection_name=collection_name,
            embedding_dimensions=len(embeddings)
        )
        
        # In a real implementation, you would:
        # 1. Initialize Qdrant client
        # 2. Prepare point structure
        # 3. Upsert the point
        # 
        # Example:
        # from qdrant_client import QdrantClient
        # from qdrant_client.http.models import Distance, VectorParams, PointStruct
        # 
        # client = QdrantClient(
        #     host=settings.qdrant_host,
        #     port=settings.qdrant_port,
        #     api_key=settings.qdrant_api_key,
        # )
        # 
        # # Ensure collection exists
        # try:
        #     client.get_collection(collection_name)
        # except:
        #     client.create_collection(
        #         collection_name=collection_name,
        #         vectors_config=VectorParams(size=len(embeddings), distance=Distance.COSINE),
        #     )
        # 
        # # Upsert point
        # point = PointStruct(
        #     id=document_id,
        #     vector=embeddings,
        #     payload=metadata
        # )
        # 
        # result = client.upsert(
        #     collection_name=collection_name,
        #     points=[point]
        # )
        
        # Simulate successful indexing
        return {
            "indexed_document_id": document_id,
            "collection": collection_name,
            "vector_dimensions": len(embeddings),
            "metadata_fields": len(metadata),
            "indexed_at": "2024-01-15T10:30:00Z",
            "qdrant_id": document_id,
            "similarity_metric": "cosine",
        }
    
    async def start(self):
        """Start the worker."""
        await self.setup()
        
        logger.info("Starting Qdrant indexer worker")
        
        try:
            # Start processing jobs
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("Qdrant indexer worker stopped by user")
        except Exception as e:
            logger.error("Qdrant indexer worker error", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up Qdrant indexer worker")
        
        if self.worker:
            await self.worker.close()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Qdrant indexer worker cleanup complete")


async def main():
    """Main function to run the worker."""
    worker = QdrantIndexerWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main()) 