"""
Document converter worker.
Processes document conversion jobs from the Redis queue using Marker library.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis
from marker import convert_single_pdf
from marker.models import load_all_models

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import DocumentConversionError, FileProcessingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class DocumentConverterWorker:
    """Worker for processing document conversion jobs using Marker."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
        self.marker_models = None
        self.is_running = False
    
    async def setup(self):
        """Setup Redis connection, worker, and load Marker models."""
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
            
            # Load Marker models (this may take some time on first run)
            logger.info("Loading Marker models...")
            self.marker_models = load_all_models()
            logger.info("Marker models loaded successfully")
            
            # Create worker - BullMQ Python API
            # Note: The worker starts processing automatically when instantiated
            self.worker = Worker(
                settings.queue_names["document_converter"],
                self.process_job,
            )
            
            self.is_running = True
            
            logger.info(
                "Document converter worker initialized and started",
                queue_name=settings.queue_names["document_converter"]
            )
            
        except Exception as e:
            logger.error("Failed to setup document converter worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a document conversion job using Marker library.
        
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
            
            # Validate source file exists
            if not os.path.exists(source_path):
                raise DocumentConversionError(f"Source file not found: {source_path}")
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            await job.updateProgress(20)
            
            # Convert document based on file type
            source_ext = os.path.splitext(source_path.lower())[1]
            
            if source_ext == '.pdf':
                result = await self._convert_pdf_with_marker(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.docx', '.doc']:
                result = await self._convert_docx_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.txt', '.md']:
                result = await self._convert_text_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.html', '.htm']:
                result = await self._convert_html_to_markdown(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.pptx', '.ppt']:
                result = await self._convert_pptx_with_marker(
                    source_path, output_path, conversion_options
                )
            elif source_ext in ['.xlsx', '.xls']:
                result = await self._convert_xlsx_with_marker(
                    source_path, output_path, conversion_options
                )
            elif source_ext == '.epub':
                result = await self._convert_epub_with_marker(
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
    
    async def _convert_pdf_with_marker(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert PDF to Markdown using Marker."""
        logger.info("Converting PDF to Markdown with Marker", source_path=source_path)
        
        try:
            # Run Marker conversion in thread pool to avoid blocking
            def convert_pdf():
                full_text, images, out_meta = convert_single_pdf(
                    source_path,
                    self.marker_models,
                    max_pages=options.get("max_pages"),
                    langs=options.get("langs"),
                    batch_multiplier=options.get("batch_multiplier", 2)
                )
                return full_text, images, out_meta
            
            loop = asyncio.get_event_loop()
            full_text, images, out_meta = await loop.run_in_executor(None, convert_pdf)
            
            # Save markdown content to output file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            # Save images if any (optional)
            if images and options.get("save_images", False):
                images_dir = os.path.join(os.path.dirname(output_path), "images")
                os.makedirs(images_dir, exist_ok=True)
                for i, image in enumerate(images):
                    image_path = os.path.join(images_dir, f"image_{i}.png")
                    image.save(image_path)
            
            return {
                "format": "pdf",
                "pages_processed": len(out_meta.get("pages", [])),
                "images_extracted": len(images),
                "output_size": len(full_text),
                "metadata": out_meta,
                "success": True
            }
            
        except Exception as e:
            logger.error("Marker PDF conversion failed", error=str(e))
            raise DocumentConversionError(f"PDF conversion with Marker failed: {e}")
    
    async def _convert_pptx_with_marker(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert PPTX to Markdown using Marker."""
        logger.info("Converting PPTX to Markdown with Marker", source_path=source_path)
        
        try:
            # Marker also supports PPTX files
            def convert_pptx():
                from marker import convert_single_pdf  # This also handles PPTX
                full_text, images, out_meta = convert_single_pdf(
                    source_path,
                    self.marker_models,
                    max_pages=options.get("max_pages"),
                    langs=options.get("langs")
                )
                return full_text, images, out_meta
            
            loop = asyncio.get_event_loop()
            full_text, images, out_meta = await loop.run_in_executor(None, convert_pptx)
            
            # Save markdown content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return {
                "format": "pptx", 
                "slides_processed": out_meta.get("slides", 0),
                "images_extracted": len(images),
                "output_size": len(full_text),
                "metadata": out_meta,
                "success": True
            }
            
        except Exception as e:
            logger.error("Marker PPTX conversion failed", error=str(e))
            # Fallback to basic text extraction if Marker fails
            return await self._fallback_pptx_conversion(source_path, output_path)
    
    async def _convert_xlsx_with_marker(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert XLSX to Markdown using Marker or fallback."""
        logger.info("Converting XLSX to Markdown", source_path=source_path)
        
        try:
            # Try Marker first if it supports XLSX
            def convert_xlsx():
                from marker import convert_single_pdf  # May support XLSX
                full_text, images, out_meta = convert_single_pdf(
                    source_path,
                    self.marker_models
                )
                return full_text, images, out_meta
            
            loop = asyncio.get_event_loop()
            full_text, images, out_meta = await loop.run_in_executor(None, convert_xlsx)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return {
                "format": "xlsx",
                "sheets_processed": out_meta.get("sheets", 1),
                "output_size": len(full_text),
                "metadata": out_meta,
                "success": True
            }
            
        except Exception as e:
            logger.info("Marker XLSX conversion not supported, using fallback", error=str(e))
            return await self._fallback_xlsx_conversion(source_path, output_path)
    
    async def _convert_epub_with_marker(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert EPUB to Markdown using Marker."""
        logger.info("Converting EPUB to Markdown with Marker", source_path=source_path)
        
        try:
            def convert_epub():
                from marker import convert_single_pdf  # Should support EPUB
                full_text, images, out_meta = convert_single_pdf(
                    source_path,
                    self.marker_models
                )
                return full_text, images, out_meta
            
            loop = asyncio.get_event_loop()
            full_text, images, out_meta = await loop.run_in_executor(None, convert_epub)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_text)
            
            return {
                "format": "epub",
                "chapters_processed": out_meta.get("chapters", 1),
                "output_size": len(full_text),
                "metadata": out_meta,
                "success": True
            }
            
        except Exception as e:
            logger.error("Marker EPUB conversion failed", error=str(e))
            return await self._fallback_epub_conversion(source_path, output_path)

    async def _convert_docx_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert DOCX to Markdown using python-docx."""
        logger.info("Converting DOCX to Markdown", source_path=source_path)
        
        try:
            from docx import Document
            import re
            
            def convert_docx():
                doc = Document(source_path)
                markdown_content = []
                
                for paragraph in doc.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        # Simple markdown formatting based on style
                        if paragraph.style.name.startswith('Heading'):
                            level = int(paragraph.style.name.split()[-1]) if paragraph.style.name.split()[-1].isdigit() else 1
                            markdown_content.append(f"{'#' * level} {text}\n")
                        else:
                            markdown_content.append(f"{text}\n")
                
                return '\n'.join(markdown_content)
            
            loop = asyncio.get_event_loop()
            markdown_text = await loop.run_in_executor(None, convert_docx)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            
            return {
                "format": "docx",
                "output_size": len(markdown_text),
                "success": True
            }
            
        except Exception as e:
            logger.error("DOCX conversion failed", error=str(e))
            raise DocumentConversionError(f"DOCX conversion failed: {e}")

    async def _convert_text_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert plain text to Markdown (minimal processing)."""
        logger.info("Converting text to Markdown", source_path=source_path)
        
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # If it's already markdown, just copy
            if source_path.lower().endswith('.md'):
                markdown_content = content
            else:
                # Convert plain text to basic markdown
                lines = content.split('\n')
                markdown_lines = []
                for line in lines:
                    line = line.strip()
                    if line:
                        markdown_lines.append(line)
                    else:
                        markdown_lines.append('')
                markdown_content = '\n'.join(markdown_lines)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return {
                "format": "text",
                "output_size": len(markdown_content),
                "success": True
            }
            
        except Exception as e:
            logger.error("Text conversion failed", error=str(e))
            raise DocumentConversionError(f"Text conversion failed: {e}")

    async def _convert_html_to_markdown(
        self,
        source_path: str,
        output_path: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert HTML to Markdown."""
        logger.info("Converting HTML to Markdown", source_path=source_path)
        
        try:
            import html2text
            
            def convert_html():
                with open(source_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                markdown_content = h.handle(html_content)
                return markdown_content
            
            loop = asyncio.get_event_loop()
            markdown_content = await loop.run_in_executor(None, convert_html)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            return {
                "format": "html",
                "output_size": len(markdown_content),
                "success": True
            }
            
        except Exception as e:
            logger.error("HTML conversion failed", error=str(e))
            raise DocumentConversionError(f"HTML conversion failed: {e}")

    # Fallback methods for when Marker doesn't support certain formats
    async def _fallback_pptx_conversion(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Fallback PPTX conversion using python-pptx."""
        try:
            from pptx import Presentation
            
            def extract_text():
                prs = Presentation(source_path)
                text_runs = []
                
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text_runs.append(shape.text)
                
                return '\n\n'.join(text_runs)
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, extract_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "format": "pptx",
                "output_size": len(content),
                "success": True,
                "fallback": True
            }
        except Exception as e:
            raise DocumentConversionError(f"PPTX fallback conversion failed: {e}")

    async def _fallback_xlsx_conversion(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Fallback XLSX conversion using pandas."""
        try:
            import pandas as pd
            
            def extract_data():
                # Read all sheets
                excel_file = pd.ExcelFile(source_path)
                markdown_content = []
                
                for sheet_name in excel_file.sheet_names:
                    df = pd.read_excel(source_path, sheet_name=sheet_name)
                    markdown_content.append(f"## {sheet_name}\n")
                    markdown_content.append(df.to_markdown(index=False))
                    markdown_content.append("\n")
                
                return '\n'.join(markdown_content)
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, extract_data)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "format": "xlsx",
                "output_size": len(content),
                "success": True,
                "fallback": True
            }
        except Exception as e:
            raise DocumentConversionError(f"XLSX fallback conversion failed: {e}")

    async def _fallback_epub_conversion(self, source_path: str, output_path: str) -> Dict[str, Any]:
        """Fallback EPUB conversion using ebooklib."""
        try:
            import ebooklib
            from ebooklib import epub
            from bs4 import BeautifulSoup
            
            def extract_text():
                book = epub.read_epub(source_path)
                chapters = []
                
                for item in book.get_items():
                    if item.get_type() == ebooklib.ITEM_DOCUMENT:
                        soup = BeautifulSoup(item.get_content(), 'html.parser')
                        text = soup.get_text()
                        if text.strip():
                            chapters.append(text.strip())
                
                return '\n\n---\n\n'.join(chapters)
            
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, extract_text)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "format": "epub",
                "output_size": len(content),
                "success": True,
                "fallback": True
            }
        except Exception as e:
            raise DocumentConversionError(f"EPUB fallback conversion failed: {e}")

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
        
        logger.info("Document converter worker cleaned up")


async def main():
    """Main function to run the document converter worker."""
    worker = DocumentConverterWorker()
    
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
        
        logger.info("Document converter worker is ready and processing jobs...")
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