"""
Metadata extractor worker.
Processes metadata extraction jobs from the Redis queue using LlamaIndex.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bullmq import Worker
import redis.asyncio as redis
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.extractors import (
    TitleExtractor,
    QuestionsAnsweredExtractor,
    SummaryExtractor,
    KeywordExtractor,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger, log_job_event
from app.utils.exceptions import FileProcessingError


# Configure logging
configure_logging()
logger = get_logger(__name__)


class DocumentMetadata(BaseModel):
    """Structured document metadata model."""
    title: str = Field(description="Document title")
    description: str = Field(description="Document description") 
    type: str = Field(description="Document type (e.g., article, report, manual)")
    category: str = Field(description="Document category")
    authors: List[str] = Field(default_factory=list, description="Document authors")
    date: Optional[str] = Field(default=None, description="Document date")
    tags: List[str] = Field(default_factory=list, description="Document tags/keywords")
    file_path: str = Field(description="Original file path")
    original_filename: str = Field(description="Original filename")
    summary: str = Field(description="Document summary")
    language: str = Field(default="en", description="Document language")
    word_count: int = Field(default=0, description="Word count")
    page_count: Optional[int] = Field(default=None, description="Number of pages")
    extracted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MetadataExtractorWorker:
    """Worker for processing metadata extraction jobs using LlamaIndex."""
    
    def __init__(self):
        self.worker = None
        self.redis_connection = None
        self.llm = None
        self.embedding_model = None
        self.extractors = None
    
    async def setup(self):
        """Setup Redis connection, worker, and LlamaIndex components."""
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
            logger.info("Redis connection established for metadata extractor worker")
            
            # Initialize OpenAI LLM
            self.llm = OpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0.1
            )
            
            # Initialize OpenAI embedding model
            self.embedding_model = OpenAIEmbedding(
                model="text-embedding-3-small",
                api_key=settings.openai_api_key
            )
            
            # Setup metadata extractors
            self.extractors = [
                TitleExtractor(nodes=5, llm=self.llm),
                SummaryExtractor(summaries=["prev", "self"], llm=self.llm),
                QuestionsAnsweredExtractor(questions=3, llm=self.llm),
                KeywordExtractor(keywords=10, llm=self.llm),
            ]
            
            logger.info("LlamaIndex components initialized successfully")
            
            # Create worker - BullMQ Python API
            self.worker = Worker(
                settings.queue_names["metadata_extractor"],
                self.process_job,
            )
            
            logger.info(
                "Metadata extractor worker initialized",
                queue_name=settings.queue_names["metadata_extractor"]
            )
            
        except Exception as e:
            logger.error("Failed to setup metadata extractor worker", error=str(e))
            raise
    
    async def process_job(self, job) -> Dict[str, Any]:
        """
        Process a metadata extraction job using LlamaIndex.
        
        Args:
            job: BullMQ job object
            
        Returns:
            Dict[str, Any]: Job result with extracted metadata
            
        Raises:
            FileProcessingError: If metadata extraction fails
        """
        job_id = job.id
        job_data = job.data
        
        try:
            logger.info(
                "Processing metadata extraction job",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                markdown_path=job_data.get("markdown_path")
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["metadata_extractor"],
                event_type="started",
                document_id=job_data.get("document_id")
            )
            
            # Extract job data
            document_id = job_data["document_id"]
            markdown_path = job_data["markdown_path"]
            original_file_path = job_data["original_file_path"]
            original_filename = job_data["original_filename"]
            extraction_options = job_data.get("extraction_options", {})
            
            # Update job progress
            await job.updateProgress(10)
            
            # Validate markdown file exists
            if not os.path.exists(markdown_path):
                raise FileProcessingError(f"Markdown file not found: {markdown_path}")
            
            # Read markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            await job.updateProgress(20)
            
            # Extract metadata using LlamaIndex
            metadata = await self._extract_metadata_with_llamaindex(
                markdown_content, original_file_path, original_filename, extraction_options
            )
            
            await job.updateProgress(80)
            
            # Generate embeddings for important metadata fields
            embeddings = await self._generate_metadata_embeddings(metadata)
            
            await job.updateProgress(90)
            
            # Prepare result
            job_result = {
                "success": True,
                "document_id": document_id,
                "metadata": metadata.model_dump(),
                "embeddings": embeddings,
                "markdown_path": markdown_path,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
            await job.updateProgress(100)
            
            logger.info(
                "Metadata extraction job completed successfully",
                job_id=job_id,
                document_id=document_id,
                metadata_fields=len(metadata.model_dump())
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["metadata_extractor"],
                event_type="completed",
                document_id=document_id,
                result=job_result
            )
            
            return job_result
            
        except Exception as e:
            logger.error(
                "Metadata extraction job failed",
                job_id=job_id,
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            log_job_event(
                job_id=job_id,
                queue_name=settings.queue_names["metadata_extractor"],
                event_type="failed",
                document_id=job_data.get("document_id"),
                error=str(e)
            )
            
            raise FileProcessingError(f"Metadata extraction failed: {e}")
    
    async def _extract_metadata_with_llamaindex(
        self,
        content: str,
        original_file_path: str,
        original_filename: str,
        options: Dict[str, Any]
    ) -> DocumentMetadata:
        """Extract metadata using LlamaIndex extractors."""
        logger.info("Extracting metadata with LlamaIndex", content_length=len(content))
        
        try:
            # Create a LlamaIndex Document
            document = Document(text=content)
            
            # Run metadata extraction in thread pool
            def extract_metadata():
                # Apply extractors to document
                for extractor in self.extractors:
                    extractor.extract([document])
                
                return document.metadata
            
            loop = asyncio.get_event_loop()
            extracted_metadata = await loop.run_in_executor(None, extract_metadata)
            
            # Use LLM to extract structured metadata
            structured_metadata = await self._extract_structured_metadata(content, extracted_metadata)
            
            # Calculate basic statistics
            word_count = len(content.split())
            
            # Create DocumentMetadata object
            metadata = DocumentMetadata(
                title=structured_metadata.get("title", os.path.splitext(original_filename)[0]),
                description=structured_metadata.get("description", ""),
                type=structured_metadata.get("type", self._infer_document_type(content)),
                category=structured_metadata.get("category", "general"),
                authors=structured_metadata.get("authors", []),
                date=structured_metadata.get("date"),
                tags=extracted_metadata.get("keywords", []) + structured_metadata.get("tags", []),
                file_path=original_file_path,
                original_filename=original_filename,
                summary=extracted_metadata.get("section_summary", structured_metadata.get("summary", "")),
                language=options.get("language", "en"),
                word_count=word_count,
                page_count=options.get("page_count"),
            )
            
            return metadata
            
        except Exception as e:
            logger.error("LlamaIndex metadata extraction failed", error=str(e))
            # Fallback to basic extraction
            return await self._basic_metadata_extraction(content, original_file_path, original_filename)
    
    async def _extract_structured_metadata(
        self,
        content: str,
        extracted_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to extract additional structured metadata."""
        prompt = f"""
        Please analyze the following document content and extract structured metadata.
        Return a JSON object with the following fields:
        - title: Document title
        - description: Brief description of the document
        - type: Document type (article, report, manual, presentation, etc.)
        - category: Subject category
        - authors: List of author names if mentioned
        - date: Publication or creation date if mentioned (ISO format)
        - tags: List of relevant tags/keywords
        - summary: Brief summary of the document

        Document content (first 2000 characters):
        {content[:2000]}
        
        Existing extracted metadata:
        {json.dumps(extracted_metadata, indent=2)}
        
        Return only valid JSON:
        """
        
        try:
            def get_structured_metadata():
                response = self.llm.complete(prompt)
                return response.text
            
            loop = asyncio.get_event_loop()
            response_text = await loop.run_in_executor(None, get_structured_metadata)
            
            # Parse JSON response
            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return {}
                    
        except Exception as e:
            logger.warning("Structured metadata extraction failed", error=str(e))
            return {}
    
    def _infer_document_type(self, content: str) -> str:
        """Infer document type from content."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ["abstract", "introduction", "methodology", "conclusion"]):
            return "academic_paper"
        elif any(word in content_lower for word in ["report", "executive summary", "findings"]):
            return "report"
        elif any(word in content_lower for word in ["manual", "instructions", "how to", "step by step"]):
            return "manual"
        elif any(word in content_lower for word in ["presentation", "slide", "agenda"]):
            return "presentation"
        elif any(word in content_lower for word in ["policy", "guidelines", "procedures"]):
            return "policy"
        else:
            return "document"
    
    async def _basic_metadata_extraction(
        self,
        content: str,
        original_file_path: str,
        original_filename: str
    ) -> DocumentMetadata:
        """Fallback basic metadata extraction."""
        logger.info("Using basic metadata extraction fallback")
        
        # Simple title extraction (first non-empty line or filename)
        lines = content.split('\n')
        title = original_filename
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                title = line[:100]  # First 100 chars of first line
                break
            elif line.startswith('# '):
                title = line[2:].strip()
                break
        
        # Basic summary (first paragraph)
        paragraphs = content.split('\n\n')
        summary = paragraphs[0][:500] if paragraphs else ""
        
        word_count = len(content.split())
        
        return DocumentMetadata(
            title=title,
            description=summary[:200],
            type=self._infer_document_type(content),
            category="general",
            authors=[],
            date=None,
            tags=[],
            file_path=original_file_path,
            original_filename=original_filename,
            summary=summary,
            word_count=word_count,
        )
    
    async def _generate_metadata_embeddings(self, metadata: DocumentMetadata) -> Dict[str, List[float]]:
        """Generate embeddings for important metadata fields using OpenAI."""
        logger.info("Generating metadata embeddings")
        
        try:
            # Combine important text fields for embedding
            embedding_texts = {
                "title": metadata.title,
                "description": metadata.description,
                "summary": metadata.summary,
                "combined": f"{metadata.title} {metadata.description} {metadata.summary} {' '.join(metadata.tags)}"
            }
            
            embeddings = {}
            
            def generate_embedding(text: str) -> List[float]:
                if not text.strip():
                    return []
                return self.embedding_model.get_text_embedding(text)
            
            loop = asyncio.get_event_loop()
            
            for field, text in embedding_texts.items():
                if text.strip():
                    embedding = await loop.run_in_executor(None, generate_embedding, text)
                    embeddings[field] = embedding
                else:
                    embeddings[field] = []
            
            return embeddings
            
        except Exception as e:
            logger.error("Metadata embedding generation failed", error=str(e))
            return {}
    
    async def start(self):
        """Start the worker."""
        if not self.worker:
            raise RuntimeError("Worker not initialized. Call setup() first.")
        
        logger.info("Starting metadata extractor worker...")
        await self.worker.run()
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.worker:
            await self.worker.close()
        
        if self.redis_connection:
            await self.redis_connection.close()
        
        logger.info("Metadata extractor worker cleaned up")


async def main():
    """Main function to run the metadata extractor worker."""
    worker = MetadataExtractorWorker()
    
    try:
        await worker.setup()
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error("Worker failed", error=str(e))
        raise
    finally:
        await worker.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 