"""
Document sync worker.
Processes document synchronization jobs from the Redis queue.
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
from app.utils.exceptions import DocumentSyncError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class DocumentSyncWorker:
    """Worker for processing document synchronization jobs."""
    
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
            logger.info("Redis connection established for document sync worker")
            
            # Create worker - BullMQ Python API
            self.worker = Worker(
                settings.queue_names["document_sync"],
                self.process_job,
            )
            
            logger.info(
                "Document sync worker initialized",
                queue_name=settings.queue_names["document_sync"]
            )
            
        except Exception as e:
            logger.error("Failed to setup document sync worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a document synchronization job.
        
        Args:
            job: BullMQ job object
            
        Returns:
            Dict[str, Any]: Job result
            
        Raises:
            DocumentSyncError: If synchronization fails
        """
        job_id = job.id
        job_data = job.data
        
        try:
            logger.info(
                "Processing document synchronization job",
                job_id=job_id,
                source_document_id=job_data.get("source_document_id"),
                target_systems=job_data.get("target_systems")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_sync"],
                event_type="started",
                document_id=job_data.get("source_document_id")
            )
            
            # Extract job data
            source_document_id = job_data["source_document_id"]
            target_systems = job_data["target_systems"]
            sync_options = job_data.get("sync_options", {})
            
            # Update job progress
            await job.updateProgress(10)
            
            # Simulate document synchronization process
            # In a real implementation, you would:
            # 1. Retrieve the source document
            # 2. For each target system, sync the document
            # 3. Handle conflicts and updates
            
            # Retrieve source document (simulated)
            source_document = await self._retrieve_source_document(source_document_id)
            
            await job.updateProgress(30)
            
            # Sync to each target system
            sync_results = []
            progress_per_system = 60 / len(target_systems)
            current_progress = 30
            
            for system in target_systems:
                logger.info(
                    "Syncing to target system",
                    source_document_id=source_document_id,
                    target_system=system
                )
                
                result = await self._sync_to_system(
                    source_document, system, sync_options
                )
                sync_results.append(result)
                
                current_progress += progress_per_system
                await job.updateProgress(int(current_progress))
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "source_document_id": source_document_id,
                "target_systems": target_systems,
                "sync_results": sync_results,
                "processed_at": job_data.get("created_at"),
                "total_synced": len([r for r in sync_results if r["success"]]),
                "total_failed": len([r for r in sync_results if not r["success"]]),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Document synchronization job completed",
                job_id=job_id,
                source_document_id=source_document_id,
                total_synced=job_result["total_synced"],
                total_failed=job_result["total_failed"]
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_sync"],
                event_type="completed",
                document_id=source_document_id,
                result=job_result
            )
            
            return job_result
            
        except Exception as e:
            logger.error(
                "Document synchronization job failed",
                job_id=job_id,
                source_document_id=job_data.get("source_document_id"),
                error=str(e)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_sync"],
                event_type="failed",
                document_id=job_data.get("source_document_id"),
                error=str(e)
            )
            
            raise DocumentSyncError(f"Document synchronization failed: {e}")
    
    async def _retrieve_source_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve source document for synchronization."""
        # Simulate document retrieval
        await asyncio.sleep(0.5)  # Simulate processing time
        
        logger.info("Retrieving source document", document_id=document_id)
        
        # In a real implementation, you would:
        # 1. Query your database for the document
        # 2. Retrieve content and metadata
        # 3. Return structured document data
        
        # Simulate document data
        return {
            "id": document_id,
            "title": f"Document {document_id}",
            "content": f"This is the content of document {document_id}. It contains important information that needs to be synchronized across multiple systems.",
            "metadata": {
                "author": "System",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "tags": ["sync", "document", "processing"],
                "category": "general"
            },
            "version": 1,
            "checksum": f"sha256_{hash(document_id) % 10000}"
        }
    
    async def _sync_to_system(
        self,
        document: Dict[str, Any],
        target_system: str,
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to a specific target system."""
        try:
            if target_system == "typesense":
                return await self._sync_to_typesense(document, sync_options)
            elif target_system == "qdrant":
                return await self._sync_to_qdrant(document, sync_options)
            else:
                raise DocumentSyncError(f"Unsupported target system: {target_system}")
                
        except Exception as e:
            logger.error(
                "Failed to sync to target system",
                target_system=target_system,
                document_id=document["id"],
                error=str(e)
            )
            return {
                "system": target_system,
                "success": False,
                "error": str(e),
                "document_id": document["id"]
            }
    
    async def _sync_to_typesense(
        self,
        document: Dict[str, Any],
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to Typesense."""
        # Simulate Typesense sync
        await asyncio.sleep(1)  # Simulate processing time
        
        logger.info(
            "Syncing document to Typesense",
            document_id=document["id"]
        )
        
        # In a real implementation, you would:
        # 1. Connect to Typesense
        # 2. Check if document exists
        # 3. Update or create the document
        # 4. Handle conflicts based on sync_options
        
        force_update = sync_options.get("force_update", False)
        
        # Simulate sync logic
        if force_update:
            action = "updated"
        else:
            # Simulate checking if document exists
            action = "created"  # or "updated" or "skipped"
        
        return {
            "system": "typesense",
            "success": True,
            "action": action,
            "document_id": document["id"],
            "collection": "documents",
            "indexed_fields": len(document["metadata"]) + 2,  # content + title + metadata
            "sync_timestamp": "2024-01-15T10:30:00Z"
        }
    
    async def _sync_to_qdrant(
        self,
        document: Dict[str, Any],
        sync_options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sync document to Qdrant."""
        # Simulate Qdrant sync
        await asyncio.sleep(1.5)  # Simulate processing time (longer due to vectorization)
        
        logger.info(
            "Syncing document to Qdrant",
            document_id=document["id"]
        )
        
        # In a real implementation, you would:
        # 1. Connect to Qdrant
        # 2. Generate embeddings for the content
        # 3. Check if document exists
        # 4. Update or create the vector point
        # 5. Handle conflicts based on sync_options
        
        force_update = sync_options.get("force_update", False)
        
        # Simulate embedding generation and sync
        if force_update:
            action = "updated"
        else:
            # Simulate checking if document exists
            action = "created"  # or "updated" or "skipped"
        
        return {
            "system": "qdrant",
            "success": True,
            "action": action,
            "document_id": document["id"],
            "collection": "document_vectors",
            "vector_dimensions": 384,
            "payload_fields": len(document["metadata"]) + 1,  # metadata + title
            "sync_timestamp": "2024-01-15T10:30:00Z"
        }
    
    async def start(self):
        """Start the worker."""
        await self.setup()
        
        logger.info("Starting document sync worker")
        
        try:
            # Start processing jobs
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("Document sync worker stopped by user")
        except Exception as e:
            logger.error("Document sync worker error", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up document sync worker")
        
        if self.worker:
            await self.worker.close()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Document sync worker cleanup complete")


async def main():
    """Main function to run the worker."""
    worker = DocumentSyncWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main()) 