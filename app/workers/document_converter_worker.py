"""
Document converter worker.
Processes document conversion jobs from the Redis queue.
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
from app.utils.exceptions import DocumentConversionError, FileProcessingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class DocumentConverterWorker:
    """Worker for processing document conversion jobs."""
    
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
            logger.info("Redis connection established for document converter worker")
            
            # Create worker - BullMQ Python API
            self.worker = Worker(
                settings.queue_names["document_converter"],
                self.process_job,
            )
            
            logger.info(
                "Document converter worker initialized",
                queue_name=settings.queue_names["document_converter"]
            )
            
        except Exception as e:
            logger.error("Failed to setup document converter worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a document conversion job.
        
        Args:
            job: BullMQ job object
            
        Returns:
            Dict[str, Any]: Job result
            
        Raises:
            DocumentConversionError: If conversion fails
        """
        job_id = job.id
        job_data = job.data
        
        try:
            logger.info(
                "Processing document conversion job",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                source_path=job_data.get("source_path")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_converter"],
                event_type="started",
                document_id=job_data.get("document_id")
            )
            
            # Extract job data
            document_id = job_data["document_id"]
            source_path = job_data["source_path"]
            output_path = job_data["output_path"]
            conversion_options = job_data.get("conversion_options", {})
            
            # Update job progress
            await job.updateProgress(10)
            
            # Simulate document conversion process
            # In a real implementation, you would:
            # 1. Read the source document
            # 2. Convert it to markdown using appropriate libraries
            # 3. Save the result to the output path
            
            await job.updateProgress(30)
            
            # Simulate conversion based on file type
            source_ext = os.path.splitext(source_path.lower())[1]
            
            if source_ext == '.pdf':
                result = await self._convert_pdf_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext == '.docx':
                result = await self._convert_docx_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.txt', '.md']:
                result = await self._convert_text_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext == '.html':
                result = await self._convert_html_to_markdown(
                    source_path, output_path, conversion_options
                )
            else:
                raise DocumentConversionError(f"Unsupported file format: {source_ext}")
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "document_id": document_id,
                "source_path": source_path,
                "output_path": output_path,
                "conversion_result": result,
                "processed_at": job_data.get("created_at"),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Document conversion job completed successfully",
                job_id=job_id,
                document_id=document_id,
                output_path=output_path
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_converter"],
                event_type="completed",
                document_id=document_id,
                result=job_result
            )
            
            return job_result
            
        except Exception as e:
            logger.error(
                "Document conversion job failed",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["document_converter"],
                event_type="failed",
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            raise DocumentConversionError(f"Conversion failed: {e}")
    
    async def _convert_pdf_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert PDF to Markdown."""
        # Simulate PDF conversion
        await asyncio.sleep(2)  # Simulate processing time
        
        logger.info("Converting PDF to Markdown", source_path=source_path)
        
        # In a real implementation, you would use libraries like:
        # - PyPDF2 or pdfplumber for text extraction
        # - pdf2image for image extraction
        # - Custom logic for markdown formatting
        
        return {
            "format": "pdf",
            "pages_processed": 5,
            "images_extracted": options.get("extract_images", False),
            "formatting_preserved": options.get("preserve_formatting", True),
        }
    
    async def _convert_docx_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert DOCX to Markdown."""
        # Simulate DOCX conversion
        await asyncio.sleep(1.5)  # Simulate processing time
        
        logger.info("Converting DOCX to Markdown", source_path=source_path)
        
        # In a real implementation, you would use libraries like:
        # - python-docx for reading DOCX files
        # - Custom logic for markdown conversion
        
        return {
            "format": "docx",
            "paragraphs_processed": 25,
            "tables_converted": 2,
            "formatting_preserved": options.get("preserve_formatting", True),
        }
    
    async def _convert_text_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert text/markdown to Markdown."""
        # Simulate text conversion
        await asyncio.sleep(0.5)  # Simulate processing time
        
        logger.info("Converting text to Markdown", source_path=source_path)
        
        return {
            "format": "text",
            "lines_processed": 100,
            "encoding_detected": "utf-8",
        }
    
    async def _convert_html_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert HTML to Markdown."""
        # Simulate HTML conversion
        await asyncio.sleep(1)  # Simulate processing time
        
        logger.info("Converting HTML to Markdown", source_path=source_path)
        
        # In a real implementation, you would use libraries like:
        # - BeautifulSoup for HTML parsing
        # - html2text for markdown conversion
        
        return {
            "format": "html",
            "elements_processed": 50,
            "links_preserved": True,
            "images_processed": 5,
        }
    
    async def start(self):
        """Start the worker."""
        await self.setup()
        
        logger.info("Starting document converter worker")
        
        try:
            # Start processing jobs
            await self.worker.run()
        except KeyboardInterrupt:
            logger.info("Document converter worker stopped by user")
        except Exception as e:
            logger.error("Document converter worker error", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up document converter worker")
        
        if self.worker:
            await self.worker.close()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Document converter worker cleanup complete")


async def main():
    """Main function to run the worker."""
    worker = DocumentConverterWorker()
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main()) 