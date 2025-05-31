"""
Queue manager for BullMQ integration.
"""
import asyncio
import json
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import redis.asyncio as redis
from bullmq import Queue, Worker

from app.core.config import settings
from app.core.logging_config import LoggerMixin, log_job_event
from app.utils.exceptions import (
    QueueError,
    RedisConnectionError,
    JobCreationError,
)


class QueueManager(LoggerMixin):
    """Manages BullMQ queues and job operations."""
    
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._queues: Dict[str, Queue] = {}
        self._connection_config = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "password": settings.redis_password,
            "db": settings.redis_db,
            "decode_responses": True,
        }
    
    async def get_redis_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(**self._connection_config)
                # Test connection
                await self._redis_client.ping()
                self.logger.info("Redis connection established")
            except Exception as e:
                self.logger.error("Failed to connect to Redis", error=str(e))
                raise RedisConnectionError(f"Failed to connect to Redis: {e}")
        
        return self._redis_client
    
    async def get_queue(self, queue_name: str) -> Queue:
        """Get or create a queue instance."""
        if queue_name not in self._queues:
            try:
                # BullMQ Python API - no connection parameter needed
                # It will use default Redis connection (localhost:6379)
                # For custom connection, we need to set environment variables or use different approach
                self._queues[queue_name] = Queue(queue_name)
                self.logger.info("Queue created", queue_name=queue_name)
            except Exception as e:
                self.logger.error(
                    "Failed to create queue",
                    queue_name=queue_name,
                    error=str(e)
                )
                raise QueueError(f"Failed to create queue {queue_name}: {e}")
        
        return self._queues[queue_name]
    
    async def add_job(
        self,
        queue_name: str,
        job_name: str,
        job_data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a job to the queue."""
        try:
            queue = await self.get_queue(queue_name)
            
            # Default job options for BullMQ Python
            job_options = {
                "attempts": settings.max_retries,
                "delay": 0,  # No delay by default
            }
            
            # Merge with provided options
            if options:
                job_options.update(options)
            
            # Add job to queue - BullMQ Python API
            job = await queue.add(job_name, job_data, job_options)
            job_id = str(job.id) if hasattr(job, 'id') else str(job)
            
            self.logger.info(
                "Job added to queue",
                job_id=job_id,
                queue_name=queue_name,
                job_name=job_name
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=queue_name,
                event_type="created",
                job_name=job_name,
                job_data=job_data
            )
            
            return job_id
            
        except Exception as e:
            self.logger.error(
                "Failed to add job to queue",
                queue_name=queue_name,
                job_name=job_name,
                error=str(e)
            )
            raise JobCreationError(f"Failed to add job to queue: {e}")
    
    async def add_document_conversion_job(
        self,
        document_id: str,
        source_path: str,
        output_path: str,
        conversion_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a document conversion job."""
        job_data = {
            "document_id": document_id,
            "source_path": source_path,
            "output_path": output_path,
            "conversion_options": conversion_options or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.add_job(
            queue_name=settings.queue_names["document_converter"],
            job_name="convert_document",
            job_data=job_data
        )
    
    async def add_typesense_indexing_job(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str
    ) -> str:
        """Add a Typesense indexing job."""
        job_data = {
            "document_id": document_id,
            "content": content,
            "metadata": metadata,
            "collection_name": collection_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.add_job(
            queue_name=settings.queue_names["typesense_indexer"],
            job_name="index_to_typesense",
            job_data=job_data
        )
    
    async def add_qdrant_indexing_job(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        collection_name: str
    ) -> str:
        """Add a Qdrant indexing job."""
        job_data = {
            "document_id": document_id,
            "content": content,
            "metadata": metadata,
            "collection_name": collection_name,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.add_job(
            queue_name=settings.queue_names["qdrant_indexer"],
            job_name="index_to_qdrant",
            job_data=job_data
        )
    
    async def add_document_sync_job(
        self,
        source_document_id: str,
        target_systems: list,
        sync_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a document synchronization job."""
        job_data = {
            "source_document_id": source_document_id,
            "target_systems": target_systems,
            "sync_options": sync_options or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        return await self.add_job(
            queue_name=settings.queue_names["document_sync"],
            job_name="sync_document",
            job_data=job_data
        )
    
    async def get_job_status(self, queue_name: str, job_id: str) -> Dict[str, Any]:
        """Get job status and information."""
        try:
            queue = await self.get_queue(queue_name)
            job = await queue.getJob(job_id)
            
            if not job:
                return {"status": "not_found"}
            
            return {
                "id": job.id,
                "name": job.name,
                "data": job.data,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.timestamp,
                "processed_at": job.processedOn,
                "finished_at": job.finishedOn,
                "failed_reason": job.failedReason,
                "attempts_made": job.attemptsMade,
                "attempts_total": job.opts.get("attempts", 1),
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get job status",
                queue_name=queue_name,
                job_id=job_id,
                error=str(e)
            )
            raise QueueError(f"Failed to get job status: {e}")
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get queue statistics."""
        try:
            queue = await self.get_queue(queue_name)
            
            # Get job counts
            waiting = await queue.getWaiting()
            active = await queue.getActive()
            completed = await queue.getCompleted()
            failed = await queue.getFailed()
            delayed = await queue.getDelayed()
            
            return {
                "queue_name": queue_name,
                "waiting": len(waiting),
                "active": len(active),
                "completed": len(completed),
                "failed": len(failed),
                "delayed": len(delayed),
                "total": len(waiting) + len(active) + len(completed) + len(failed) + len(delayed),
            }
            
        except Exception as e:
            self.logger.error(
                "Failed to get queue stats",
                queue_name=queue_name,
                error=str(e)
            )
            raise QueueError(f"Failed to get queue stats: {e}")
    
    async def retry_failed_job(self, queue_name: str, job_id: str) -> bool:
        """Retry a failed job."""
        try:
            queue = await self.get_queue(queue_name)
            job = await queue.getJob(job_id)
            
            if not job:
                return False
            
            await job.retry()
            
            self.logger.info(
                "Job retried",
                queue_name=queue_name,
                job_id=job_id
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=queue_name,
                event_type="retried"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to retry job",
                queue_name=queue_name,
                job_id=job_id,
                error=str(e)
            )
            raise QueueError(f"Failed to retry job: {e}")
    
    async def close(self):
        """Close Redis connection and cleanup."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            self.logger.info("Redis connection closed")


# Global queue manager instance
queue_manager = QueueManager() 