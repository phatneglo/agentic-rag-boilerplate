"""
Test Worker.
Processes files from object storage by downloading locally, extracting text, and cleaning up.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.services.object_storage_service import object_storage_service
from app.utils.exceptions import ObjectStorageError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class TestWorker:
    """Worker for processing test file jobs from Redis queue."""
    
    def __init__(self):
        self.redis_connection = None
        self.storage_service = object_storage_service
        self.running = False
        self.queue_key = settings.queue_names.get('test_worker', 'test:worker')
    
    async def setup(self):
        """Setup Redis connection."""
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
            logger.info("Redis connection established for test worker")
            
        except Exception as e:
            logger.error("Failed to setup test worker", error=str(e))
            raise
    
    async def process_job(self, job_data: str) -> Dict[str, Any]:
        """
        Process a single test job.
        
        Args:
            job_data: Job data in format "job_id:file_path"
            
        Returns:
            Dict[str, Any]: Processing result
        """
        try:
            # Parse job data
            if ':' not in job_data:
                raise ValueError(f"Invalid job data format: {job_data}")
            
            job_id, file_path = job_data.split(':', 1)
            
            logger.info(
                "Processing test job",
                job_id=job_id,
                file_path=file_path
            )
            
            # Step 1: Download file from object storage to temporary location
            temp_file_path = await self._download_file_locally(file_path)
            
            try:
                # Step 2: Extract text from the file
                extracted_text = await self._extract_text_from_file(temp_file_path, file_path)
                
                # Step 3: Process the extracted text (for demo, just count words/lines)
                text_stats = self._analyze_text(extracted_text)
                
                # Step 4: Prepare result
                result = {
                    "job_id": job_id,
                    "file_path": file_path,
                    "success": True,
                    "temp_file_path": temp_file_path,
                    "text_length": len(extracted_text),
                    "text_stats": text_stats,
                    "text_sample": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
                    "processed_at": asyncio.get_event_loop().time()
                }
                
                logger.info(
                    "Test job completed successfully",
                    job_id=job_id,
                    file_path=file_path,
                    text_length=len(extracted_text),
                    word_count=text_stats.get('word_count', 0)
                )
                
                return result
                
            finally:
                # Step 5: Always clean up the temporary file
                await self._cleanup_temp_file(temp_file_path)
            
        except Exception as e:
            logger.error(
                "Test job failed",
                job_id=job_id if 'job_id' in locals() else "unknown",
                file_path=file_path if 'file_path' in locals() else "unknown",
                error=str(e)
            )
            
            return {
                "job_id": job_id if 'job_id' in locals() else "unknown",
                "file_path": file_path if 'file_path' in locals() else "unknown",
                "success": False,
                "error": str(e),
                "processed_at": asyncio.get_event_loop().time()
            }
    
    async def _download_file_locally(self, file_path: str) -> str:
        """
        Download file from object storage to a temporary local file.
        
        Args:
            file_path: Path to file in object storage
            
        Returns:
            str: Path to temporary local file
        """
        try:
            logger.info(f"Downloading file from object storage: {file_path}")
            
            # Create a temporary directory
            temp_dir = tempfile.mkdtemp()
            
            # Download the file to the temporary directory
            result = await self.storage_service.download_file(file_path, temp_dir)
            
            # Get the downloaded file path
            downloaded_file_path = os.path.join(temp_dir, os.path.basename(file_path))
            
            if not os.path.exists(downloaded_file_path):
                raise FileNotFoundError(f"Downloaded file not found: {downloaded_file_path}")
            
            logger.info(f"Successfully downloaded file to: {downloaded_file_path}")
            return downloaded_file_path
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise Exception(f"Download failed for {file_path}: {e}")
    
    async def _extract_text_from_file(self, temp_file_path: str, original_file_path: str) -> str:
        """
        Extract text content from the downloaded file.
        
        Args:
            temp_file_path: Path to temporary local file
            original_file_path: Original file path for context
            
        Returns:
            str: Extracted text content
        """
        try:
            file_extension = Path(temp_file_path).suffix.lower()
            
            logger.info(
                f"Extracting text from file",
                temp_file_path=temp_file_path,
                file_extension=file_extension
            )
            
            def extract_text():
                if file_extension in ['.txt', '.md', '.py', '.js', '.json', '.csv', '.xml', '.html']:
                    # Plain text files
                    with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                
                elif file_extension == '.pdf':
                    # PDF files - using PyPDF2
                    try:
                        import PyPDF2
                        text = ""
                        with open(temp_file_path, 'rb') as f:
                            pdf_reader = PyPDF2.PdfReader(f)
                            for page in pdf_reader.pages:
                                text += page.extract_text() + "\n"
                        return text
                    except ImportError:
                        return f"PDF text extraction requires PyPDF2. File: {original_file_path}"
                    except Exception as e:
                        return f"PDF extraction failed: {e}. File: {original_file_path}"
                
                elif file_extension in ['.docx', '.doc']:
                    # Word documents - using python-docx
                    try:
                        from docx import Document
                        doc = Document(temp_file_path)
                        text = ""
                        for paragraph in doc.paragraphs:
                            text += paragraph.text + "\n"
                        return text
                    except ImportError:
                        return f"DOCX text extraction requires python-docx. File: {original_file_path}"
                    except Exception as e:
                        return f"DOCX extraction failed: {e}. File: {original_file_path}"
                
                else:
                    # Unsupported format - try to read as text anyway
                    try:
                        with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        return f"Raw text content (unsupported format {file_extension}):\n{content}"
                    except Exception as e:
                        return f"Cannot extract text from {file_extension} file: {e}"
            
            loop = asyncio.get_event_loop()
            extracted_text = await loop.run_in_executor(None, extract_text)
            
            logger.info(
                f"Text extraction completed",
                temp_file_path=temp_file_path,
                text_length=len(extracted_text),
                file_extension=file_extension
            )
            
            return extracted_text
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return f"Text extraction failed: {e}"
    
    def _analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analyze extracted text and return statistics.
        
        Args:
            text: Extracted text content
            
        Returns:
            Dict[str, Any]: Text analysis statistics
        """
        try:
            lines = text.split('\n')
            words = text.split()
            
            # Basic text statistics
            stats = {
                "character_count": len(text),
                "line_count": len(lines),
                "word_count": len(words),
                "non_empty_lines": len([line for line in lines if line.strip()]),
                "average_words_per_line": len(words) / len(lines) if lines else 0,
                "unique_words": len(set(word.lower().strip('.,!?";') for word in words)) if words else 0
            }
            
            # Find most common words (simple implementation)
            if words:
                word_freq = {}
                for word in words:
                    clean_word = word.lower().strip('.,!?";')
                    if len(clean_word) > 2:  # Skip very short words
                        word_freq[clean_word] = word_freq.get(clean_word, 0) + 1
                
                # Get top 5 most common words
                top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
                stats["top_words"] = top_words
            
            return stats
            
        except Exception as e:
            logger.warning(f"Text analysis failed: {e}")
            return {"error": str(e)}
    
    async def _cleanup_temp_file(self, temp_file_path: str):
        """
        Clean up temporary file.
        
        Args:
            temp_file_path: Path to temporary file to delete
        """
        try:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                logger.info(f"Cleaned up temporary file: {temp_file_path}")
            else:
                logger.warning(f"Temporary file not found for cleanup: {temp_file_path}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup temporary file {temp_file_path}: {e}")
    
    async def run(self):
        """Main worker loop."""
        self.running = True
        logger.info(f"Starting test worker, listening on queue: {self.queue_key}")
        
        while self.running:
            try:
                # Block and wait for jobs (with timeout)
                job_data = await self.redis_connection.brpop(self.queue_key, timeout=5)
                
                if job_data:
                    queue_name, job_payload = job_data
                    logger.info(f"Received job from {queue_name}: {job_payload}")
                    
                    # Process the job
                    result = await self.process_job(job_payload)
                    
                    # Log result
                    if result.get("success"):
                        logger.info(f"Job completed successfully: {result['job_id']}")
                    else:
                        logger.error(f"Job failed: {result['job_id']}, error: {result.get('error')}")
                
                else:
                    # Timeout - continue loop
                    logger.debug("No jobs in queue, continuing...")
                    
            except asyncio.CancelledError:
                logger.info("Worker cancelled, stopping...")
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(1)
        
        logger.info("Test worker stopped")
    
    async def stop(self):
        """Stop the worker."""
        self.running = False
        logger.info("Stopping test worker...")
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.redis_connection:
            await self.redis_connection.close()
        logger.info("Test worker cleaned up")


async def main():
    """Main function to run the test worker."""
    worker = TestWorker()
    
    try:
        await worker.setup()
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await worker.stop()
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        raise
    finally:
        await worker.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 