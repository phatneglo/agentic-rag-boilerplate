"""
Document Processing Pipeline Service.
Orchestrates the 4-step document processing workflow:
1. Document-to-Markdown conversion using Marker
2. Metadata extraction using LlamaIndex
3. Typesense indexing with embeddings
4. Qdrant indexing for RAG using Typesense document ID
"""
import asyncio
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from bullmq import Queue
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger


# Configure logging
configure_logging()
logger = get_logger(__name__)


class DocumentProcessingPipeline:
    """Service to orchestrate the complete document processing pipeline."""
    
    def __init__(self):
        self.redis_connection = None
        self.queues = {}
        
    async def setup(self):
        """Setup Redis connection and queues."""
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
            logger.info("Redis connection established for document processing pipeline")
            
            # Initialize queues
            self.queues = {
                "document_converter": Queue(settings.queue_names["document_converter"]),
                "metadata_extractor": Queue(settings.queue_names["metadata_extractor"]),
                "typesense_indexer": Queue(settings.queue_names["typesense_indexer"]),
                "qdrant_indexer": Queue(settings.queue_names["qdrant_indexer"]),
            }
            
            logger.info("Document processing pipeline initialized successfully")
            
        except Exception as e:
            logger.error("Failed to setup document processing pipeline", error=str(e))
            raise
    
    async def process_document(
        self,
        source_file_path: str,
        output_directory: str = None,
        processing_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline.
        
        Args:
            source_file_path: Path to the source document
            output_directory: Directory for output files (optional)
            processing_options: Additional processing options
            
        Returns:
            Dict[str, Any]: Processing result with job IDs
        """
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Set default output directory
            if not output_directory:
                output_directory = os.path.join(settings.processed_dir, document_id)
            
            os.makedirs(output_directory, exist_ok=True)
            
            # Extract file information
            source_path = Path(source_file_path)
            original_filename = source_path.name
            file_extension = source_path.suffix.lower()
            
            # Define output paths
            markdown_path = os.path.join(output_directory, f"{source_path.stem}.md")
            
            processing_options = processing_options or {}
            
            logger.info(
                "Starting document processing pipeline",
                document_id=document_id,
                source_file=original_filename,
                output_directory=output_directory
            )
            
            # Step 1: Queue document conversion job
            conversion_job = await self._queue_document_conversion(
                document_id=document_id,
                source_path=source_file_path,
                output_path=markdown_path,
                original_filename=original_filename,
                conversion_options=processing_options.get("conversion", {})
            )
            
            logger.info(f"Queued document conversion job: {conversion_job.id}")
            
            # Return initial result with job tracking information
            result = {
                "success": True,
                "document_id": document_id,
                "original_filename": original_filename,
                "source_path": source_file_path,
                "output_directory": output_directory,
                "markdown_path": markdown_path,
                "jobs": {
                    "conversion": {
                        "job_id": conversion_job.id,
                        "status": "queued",
                        "queue": settings.queue_names["document_converter"]
                    }
                },
                "pipeline_status": "started",
                "started_at": datetime.utcnow().isoformat(),
            }
            
            # Start monitoring and chaining jobs
            asyncio.create_task(
                self._monitor_and_chain_jobs(document_id, conversion_job.id, result)
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Failed to start document processing pipeline",
                document_id=document_id if 'document_id' in locals() else "unknown",
                error=str(e)
            )
            raise
    
    async def _monitor_and_chain_jobs(
        self,
        document_id: str,
        conversion_job_id: str,
        initial_result: Dict[str, Any]
    ):
        """Monitor job completion and chain subsequent jobs."""
        try:
            logger.info(f"🔄 Starting pipeline monitoring for document {document_id}")
            logger.info(f"📋 Conversion job ID: {conversion_job_id}")
            
            # Wait for conversion job to complete
            logger.info("⏳ Waiting for Step 1 (Document Conversion) to complete...")
            conversion_result = await self._wait_for_job_completion(
                conversion_job_id, settings.queue_names["document_converter"]
            )
            
            if not conversion_result.get("success"):
                logger.error(f"❌ Document conversion failed for {document_id}: {conversion_result.get('error')}")
                return
            
            logger.info(f"✅ Step 1 completed for {document_id} - Starting Step 2")
            
            # Step 2: Queue metadata extraction
            metadata_job = await self._queue_metadata_extraction(
                document_id=document_id,
                markdown_path=initial_result["markdown_path"],
                original_file_path=initial_result["source_path"],
                original_filename=initial_result["original_filename"],
                extraction_options={}
            )
            
            logger.info(f"📋 Step 2 queued - Metadata extraction job: {metadata_job.id}")
            
            # Wait for metadata extraction to complete
            logger.info("⏳ Waiting for Step 2 (Metadata Extraction) to complete...")
            metadata_result = await self._wait_for_job_completion(
                metadata_job.id, settings.queue_names["metadata_extractor"]
            )
            
            if not metadata_result.get("success"):
                logger.error(f"❌ Metadata extraction failed for {document_id}: {metadata_result.get('error')}")
                return
            
            logger.info(f"✅ Step 2 completed for {document_id} - Starting Steps 3 & 4")
            
            # Parse metadata result
            try:
                import json
                metadata_data = json.loads(metadata_result.get("result", "{}"))
                extracted_metadata = metadata_data.get("metadata", {})
                embeddings = metadata_data.get("embeddings", {})
            except (json.JSONDecodeError, ValueError):
                logger.warning("Could not parse metadata result, using empty metadata")
                extracted_metadata = {}
                embeddings = {}
            
            # Step 3 & 4: Queue both indexing jobs in parallel
            typesense_job = await self._queue_typesense_indexing(
                document_id=document_id,
                metadata=extracted_metadata,
                embeddings=embeddings,
                indexing_options={}
            )
            
            qdrant_job = await self._queue_qdrant_indexing(
                document_id=document_id,
                markdown_path=initial_result["markdown_path"],
                metadata=extracted_metadata,
                indexing_options={}
            )
            
            logger.info(f"📋 Step 3 queued - Typesense indexing job: {typesense_job.id}")
            logger.info(f"📋 Step 4 queued - Qdrant indexing job: {qdrant_job.id}")
            
            # Wait for both indexing jobs to complete (parallel)
            logger.info("⏳ Waiting for Steps 3 & 4 (Indexing) to complete...")
            typesense_result, qdrant_result = await asyncio.gather(
                self._wait_for_job_completion(
                    typesense_job.id, settings.queue_names["typesense_indexer"]
                ),
                self._wait_for_job_completion(
                    qdrant_job.id, settings.queue_names["qdrant_indexer"]
                ),
                return_exceptions=True
            )
            
            # Log final results
            if isinstance(typesense_result, Exception):
                logger.error(f"❌ Typesense indexing failed for {document_id}: {typesense_result}")
            elif typesense_result.get("success"):
                logger.info(f"✅ Step 3 completed - Typesense indexing for {document_id}")
            else:
                logger.error(f"❌ Typesense indexing failed for {document_id}: {typesense_result.get('error')}")
            
            if isinstance(qdrant_result, Exception):
                logger.error(f"❌ Qdrant indexing failed for {document_id}: {qdrant_result}")
            elif qdrant_result.get("success"):
                logger.info(f"✅ Step 4 completed - Qdrant indexing for {document_id}")
            else:
                logger.error(f"❌ Qdrant indexing failed for {document_id}: {qdrant_result.get('error')}")
            
            # Pipeline completed
            success_count = sum([
                1,  # Step 1 always succeeded to get here
                1 if metadata_result.get("success") else 0,
                1 if isinstance(typesense_result, dict) and typesense_result.get("success") else 0,
                1 if isinstance(qdrant_result, dict) and qdrant_result.get("success") else 0
            ])
            
            logger.info(f"🎉 Document processing pipeline completed for {document_id}")
            logger.info(f"📊 Success rate: {success_count}/4 steps completed")
            
        except Exception as e:
            logger.error(f"❌ Pipeline monitoring failed for {document_id}: {e}")
    
    async def _queue_document_conversion(
        self,
        document_id: str,
        source_path: str,
        output_path: str,
        original_filename: str,
        conversion_options: Dict[str, Any]
    ):
        """Queue document conversion job."""
        job_data = {
            "document_id": document_id,
            "source_path": source_path,
            "output_path": output_path,
            "original_filename": original_filename,
            "conversion_options": conversion_options,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        job = await self.queues["document_converter"].add(
            "convert_document",
            job_data,
            opts={
                "attempts": 3,
                "backoff": {"type": "exponential", "delay": 2000},
                "removeOnComplete": 100,
                "removeOnFail": 50,
            }
        )
        
        return job
    
    async def _queue_metadata_extraction(
        self,
        document_id: str,
        markdown_path: str,
        original_file_path: str,
        original_filename: str,
        extraction_options: Dict[str, Any]
    ):
        """Queue metadata extraction job."""
        job_data = {
            "document_id": document_id,
            "markdown_path": markdown_path,
            "original_file_path": original_file_path,
            "original_filename": original_filename,
            "extraction_options": extraction_options,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        job = await self.queues["metadata_extractor"].add(
            "extract_metadata",
            job_data,
            opts={
                "attempts": 3,
                "backoff": {"type": "exponential", "delay": 2000},
                "removeOnComplete": 100,
                "removeOnFail": 50,
            }
        )
        
        return job
    
    async def _queue_typesense_indexing(
        self,
        document_id: str,
        metadata: Dict[str, Any],
        embeddings: Dict[str, List[float]],
        indexing_options: Dict[str, Any]
    ):
        """Queue Typesense indexing job."""
        job_data = {
            "document_id": document_id,
            "metadata": metadata,
            "embeddings": embeddings,
            "indexing_options": indexing_options,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        job = await self.queues["typesense_indexer"].add(
            "index_to_typesense",
            job_data,
            opts={
                "attempts": 3,
                "backoff": {"type": "exponential", "delay": 2000},
                "removeOnComplete": 100,
                "removeOnFail": 50,
            }
        )
        
        return job
    
    async def _queue_qdrant_indexing(
        self,
        document_id: str,
        markdown_path: str,
        metadata: Dict[str, Any],
        indexing_options: Dict[str, Any]
    ):
        """Queue Qdrant indexing job."""
        job_data = {
            "document_id": document_id,
            "markdown_path": markdown_path,
            "metadata": metadata,
            "indexing_options": indexing_options,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        job = await self.queues["qdrant_indexer"].add(
            "index_to_qdrant",
            job_data,
            opts={
                "attempts": 3,
                "backoff": {"type": "exponential", "delay": 2000},
                "removeOnComplete": 100,
                "removeOnFail": 50,
            }
        )
        
        return job
    
    async def _wait_for_job_completion(
        self,
        job_id: str,
        queue_name: str,
        timeout: int = 600  # 10 minutes
    ) -> Dict[str, Any]:
        """Wait for a job to complete and return its result."""
        try:
            logger.info(f"Waiting for job {job_id} in queue {queue_name} to complete...")
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check timeout
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > timeout:
                    raise TimeoutError(f"Job {job_id} timed out after {timeout} seconds")
                
                try:
                    # Check job status using Redis directly
                    # BullMQ stores job data in Redis with specific keys
                    job_key = f"bull:{queue_name}:{job_id}"
                    
                    # Check if job is completed
                    job_data = await self.redis_connection.hgetall(job_key)
                    
                    if job_data:
                        # Check job status
                        finished_on = job_data.get('finishedOn')
                        failed_on = job_data.get('failedOn')
                        
                        if finished_on:
                            # Job completed successfully
                            logger.info(f"Job {job_id} completed successfully")
                            return {
                                "success": True,
                                "job_id": job_id,
                                "queue": queue_name,
                                "completed_at": finished_on,
                                "result": job_data.get('returnvalue', '{}')
                            }
                        elif failed_on:
                            # Job failed
                            error_msg = job_data.get('failedReason', 'Unknown error')
                            logger.error(f"Job {job_id} failed: {error_msg}")
                            return {
                                "success": False,
                                "job_id": job_id,
                                "queue": queue_name,
                                "error": error_msg,
                                "failed_at": failed_on
                            }
                    
                    # Job still in progress, wait and check again
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.warning(f"Error checking job status for {job_id}: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            return {
                "success": False,
                "job_id": job_id,
                "queue": queue_name,
                "error": str(e),
                "failed_at": datetime.utcnow().isoformat(),
            }
    
    async def get_pipeline_status(self, document_id: str) -> Dict[str, Any]:
        """Get the status of a document processing pipeline."""
        try:
            # In a real implementation, you would query job statuses
            # This is a placeholder for the actual status checking logic
            return {
                "document_id": document_id,
                "status": "in_progress",
                "steps": {
                    "conversion": {"status": "completed", "progress": 100},
                    "metadata_extraction": {"status": "in_progress", "progress": 50},
                    "typesense_indexing": {"status": "queued", "progress": 0},
                    "qdrant_indexing": {"status": "queued", "progress": 0},
                },
                "overall_progress": 37.5,
                "last_updated": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get pipeline status for {document_id}: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Document processing pipeline cleaned up")


# Singleton instance
pipeline_service = DocumentProcessingPipeline()


async def get_pipeline_service() -> DocumentProcessingPipeline:
    """Get the document processing pipeline service."""
    if not pipeline_service.redis_connection:
        await pipeline_service.setup()
    return pipeline_service 