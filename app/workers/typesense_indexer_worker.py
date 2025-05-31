"""
Typesense indexer worker.
Processes Typesense indexing jobs from the Redis queue.
"""
import asyncio
import os
import sys
from typing import Any, Dict

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import TypesenseIndexingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class TypesenseIndexerWorker:
    """Worker for processing Typesense indexing jobs."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
    
    async def setup(self):
        """Setup Redis connection and worker."""
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
            
            # Create worker - BullMQ Python API
            self.worker = Worker(
                settings.queue_names["typesense_indexer"],
                self.process_job,
            )
            
            logger.info(
                "Typesense indexer worker initialized",
                queue_name=settings.queue_names["typesense_indexer"]
            )
            
        except Exception as e:
            logger.error("Failed to setup Typesense indexer worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a Typesense indexing job.
        
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
                document_id=job_data.get("document_id"),
                collection_name=job_data.get("collection_name")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["typesense_indexer"],
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
            
            # Simulate Typesense indexing process
            # In a real implementation, you would:
            # 1. Connect to Typesense
            # 2. Prepare the document for indexing
            # 3. Index the document to the specified collection
            
            await job.updateProgress(30)
            
            # Simulate indexing process
            result = await self._index_to_typesense(
                document_id, content, metadata, collection_name
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
                "Typesense indexing job completed successfully",
                job_id=job_id,
                document_id=document_id,
                collection_name=collection_name
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
    
    async def _index_to_typesense(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str
    ) -> Dict[str, Any]:
        """Index document to Typesense."""
        # Simulate Typesense indexing
        await asyncio.sleep(1.5)  # Simulate processing time
        
        logger.info(
            "Indexing document to Typesense",
            document_id=document_id,
            collection_name=collection_name,
            content_length=len(content)
        )
        
        # In a real implementation, you would:
        # 1. Initialize Typesense client
        # 2. Prepare document structure
        # 3. Index the document
        # 
        # Example:
        # import typesense
        # client = typesense.Client({
        #     'nodes': [{
        #         'host': settings.typesense_host,
        #         'port': settings.typesense_port,
        #         'protocol': settings.typesense_protocol
        #     }],
        #     'api_key': settings.typesense_api_key,
        #     'connection_timeout_seconds': 2
        # })
        # 
        # document = {
        #     'id': document_id,
        #     'content': content,
        #     **metadata
        # }
        # 
        # result = client.collections[collection_name].documents.create(document)
        
        # Simulate successful indexing
        return {
            "indexed_document_id": document_id,
            "collection": collection_name,
            "content_length": len(content),
            "metadata_fields": len(metadata),
            "indexed_at": "2024-01-15T10:30:00Z",
            "typesense_id": f"ts_{document_id}",
        }
    
    async def start(self):
        """Start the worker."""
        await self.setup()
        
        logger.info("Starting Typesense indexer worker")
        
        try:
            # Start processing jobs
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("Typesense indexer worker stopped by user")
        except Exception as e:
            logger.error("Typesense indexer worker error", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up Typesense indexer worker")
        
        if self.worker:
            await self.worker.close()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Typesense indexer worker cleanup complete")


async def main():
    """Main function to run the worker."""
    worker = TypesenseIndexerWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main()) 