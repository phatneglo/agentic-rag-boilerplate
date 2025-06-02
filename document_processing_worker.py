#!/usr/bin/env python3
"""
Simplified Document Processing Worker

A single worker that handles all 4 steps of document processing:
1. Document-to-Markdown conversion using Marker
2. Metadata extraction using LlamaIndex tree summarizer  
3. Typesense indexing with embeddings and content
4. Qdrant indexing for RAG

Combines the proven, working code from all individual workers in app/workers/.
"""

import asyncio
import json
import os
import sys
import tempfile
import uuid
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Force CPU-only processing for Marker
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TORCH_DEVICE"] = "cpu"

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis
from bullmq import Queue, Worker, Job

# Document processing imports - from working document_converter_worker.py
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

# LlamaIndex imports - from working metadata_extractor_worker.py
from llama_index.core import SimpleDirectoryReader, Document, VectorStoreIndex, Settings, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import (
    SummaryExtractor,
    QuestionsAnsweredExtractor,
    TitleExtractor,
    KeywordExtractor,
)
from llama_index.core.ingestion import IngestionPipeline
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from pydantic import BaseModel, Field

# Typesense imports - from working typesense_indexer_worker.py
import typesense

# Qdrant imports - from working qdrant_indexer_worker.py
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models

# Our services
from app.services.object_storage_service import ObjectStorageService
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DocumentMetadata(BaseModel):
    """Structured document metadata model from metadata_extractor_worker.py."""
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


class DocumentProcessingWorker:
    """Simplified worker that handles all 4 document processing steps."""
    
    def __init__(self):
        # Redis connection
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Object storage service
        self.storage_service = ObjectStorageService()
        
        # Shutdown event for graceful shutdown
        self.shutdown_event = asyncio.Event()
        self.is_running = False
        
        # Initialize processing components
        self._init_marker()
        self._init_llama_index()
        self._init_typesense()
        
        # Try to initialize Qdrant (make it optional)
        try:
            self._init_qdrant()
            self.qdrant_enabled = True
        except Exception as e:
            logger.warning(f"⚠️ Qdrant initialization failed (will skip step 4): {e}")
            self.qdrant_enabled = False
        
        logger.info("Document processing worker initialized")

    def _init_marker(self):
        """Initialize Marker components for PDF conversion - from document_converter_worker.py."""
        try:
            logger.info("Loading Marker models...")
            
            # Create model dict with CPU device
            model_dict = create_model_dict()
            
            self.marker_converter = PdfConverter(
                artifact_dict=model_dict,
            )
            logger.info("✅ Marker PDF converter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Marker: {e}")
            raise

    def _init_llama_index(self):
        """Initialize LlamaIndex components - from metadata_extractor_worker.py."""
        try:
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
            
            # Node parser for chunking
            self.node_parser = SentenceSplitter(
                chunk_size=512,  # Default chunk size
                chunk_overlap=200  # Default chunk overlap
            )
            
            logger.info("✅ LlamaIndex metadata extractor initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LlamaIndex: {e}")
            raise

    def _init_typesense(self):
        """Initialize Typesense client - from typesense_indexer_worker.py."""
        try:
            self.typesense_client = typesense.Client({
                'nodes': [{
                    'host': settings.typesense_host,
                    'port': settings.typesense_port,
                    'protocol': settings.typesense_protocol
                }],
                'api_key': settings.typesense_api_key,
                'connection_timeout_seconds': 60
            })
            
            # Ensure collection exists
            self._ensure_typesense_collection()
            logger.info("✅ Typesense client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Typesense: {e}")
            raise

    def _ensure_typesense_collection(self):
        """Ensure the documents collection exists - from typesense_indexer_worker.py."""
        collection_name = settings.typesense_collection_name
        
        try:
            # Check if collection exists
            self.typesense_client.collections[collection_name].retrieve()
            logger.info(f"Typesense collection '{collection_name}' already exists")
        except typesense.exceptions.ObjectNotFound:
            # Create collection with auto-embedding using OpenAI API
            collection_schema = {
                'name': collection_name,
                'fields': [
                    {'name': 'id', 'type': 'string'},
                    {'name': 'title', 'type': 'string'},
                    {'name': 'description', 'type': 'string'},
                    {'name': 'summary', 'type': 'string'},
                    {'name': 'type', 'type': 'string', 'facet': True},
                    {'name': 'category', 'type': 'string', 'facet': True},
                    {'name': 'authors', 'type': 'string[]', 'facet': True},
                    {'name': 'tags', 'type': 'string[]', 'facet': True},
                    {'name': 'date', 'type': 'string', 'optional': True},
                    {'name': 'language', 'type': 'string', 'facet': True},
                    {'name': 'word_count', 'type': 'int32'},
                    {'name': 'page_count', 'type': 'int32', 'optional': True},
                    {'name': 'file_path', 'type': 'string'},
                    {'name': 'original_filename', 'type': 'string'},
                    {'name': 'created_at', 'type': 'int64'},
                    {'name': 'updated_at', 'type': 'int64'},
                    # Auto-embedding field using OpenAI API
                    {
                        'name': 'content_embedding',
                        'type': 'float[]',
                        'embed': {
                            'from': ['title', 'description', 'authors', 'type', 'category', 'tags'],
                            'model_config': {
                                'model_name': 'openai/text-embedding-3-small',
                                'api_key': settings.openai_api_key
                            }
                        }
                    },
                ],
                'default_sorting_field': 'created_at'
            }
            
            self.typesense_client.collections.create(collection_schema)
            logger.info(f"✅ Created Typesense collection '{collection_name}' with OpenAI auto-embedding")

    def _init_qdrant(self):
        """Initialize Qdrant client - from setup_proper_qdrant_collection.py."""
        try:
            # Only initialize the basic Qdrant client - no LlamaIndex components yet
            # This avoids the Pydantic validation issues during initialization
            
            self.qdrant_client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                https=False,
                prefer_grpc=False,
            )
            
            logger.info("✅ Qdrant client initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Qdrant: {e}")
            raise

    async def download_file_from_s3(self, s3_path: str) -> str:
        """Download file from S3 to temporary location."""
        try:
            # Create temporary file
            temp_dir = tempfile.mkdtemp()
            temp_file_path = os.path.join(temp_dir, os.path.basename(s3_path))
            
            # Download from S3
            response = self.storage_service.s3_client.get_object(
                Bucket=self.storage_service.bucket,
                Key=s3_path
            )
            
            with open(temp_file_path, 'wb') as f:
                f.write(response['Body'].read())
            
            logger.info(f"✅ Downloaded file from S3: {s3_path} -> {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"❌ Failed to download file from S3: {e}")
            raise

    async def step1_convert_to_markdown(self, file_path: str) -> str:
        """Step 1: Convert document to markdown - from document_converter_worker.py."""
        try:
            logger.info(f"📄 Step 1: Converting document to markdown: {file_path}")
            
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Use Marker for PDF conversion
                def convert_pdf():
                    # Use the new Marker API
                    rendered = self.marker_converter(file_path)
                    return text_from_rendered(rendered)
                
                loop = asyncio.get_event_loop()
                markdown_content = await loop.run_in_executor(None, convert_pdf)
                
            elif file_ext in ['.txt', '.md']:
                # Read text files directly
                with open(file_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
            else:
                # For other formats, read as text (basic fallback)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                markdown_content = f"# {Path(file_path).name}\n\n{content}"
            
            logger.info(f"✅ Step 1 completed: {len(markdown_content)} characters extracted")
            return markdown_content
            
        except Exception as e:
            logger.error(f"❌ Step 1 failed: {e}")
            raise

    async def step2_extract_metadata(self, markdown_content: str, document_id: str, s3_file_path: str, original_filename: str) -> DocumentMetadata:
        """Step 2: Extract metadata - from metadata_extractor_worker.py."""
        try:
            logger.info(f"🔍 Step 2: Extracting metadata for document {document_id}")
            
            def extract_metadata():
                # Create document
                document = Document(text=markdown_content, id_=document_id)
                
                # Apply extractors to document
                extraction_pipeline = IngestionPipeline(
                    transformations=[self.node_parser] + self.extractors
                )
                
                # Process the document
                processed_nodes = extraction_pipeline.run(documents=[document])
                
                # Aggregate extracted metadata
                extracted_metadata = {}
                for node in processed_nodes:
                    for key, value in node.metadata.items():
                        if key not in extracted_metadata:
                            extracted_metadata[key] = []
                        extracted_metadata[key].append(value)
                
                return extracted_metadata
            
            loop = asyncio.get_event_loop()
            extracted_metadata = await loop.run_in_executor(None, extract_metadata)
            
            # Build structured metadata
            title = extracted_metadata.get("document_title", [original_filename])[0]
            summary = " ".join(extracted_metadata.get("section_summary", ["No summary available"])[:3])
            keywords = []
            if "excerpt_keywords" in extracted_metadata:
                for keyword_str in extracted_metadata["excerpt_keywords"]:
                    keywords.extend([k.strip() for k in keyword_str.split(",") if k.strip()])
            
            metadata = DocumentMetadata(
                title=title,
                description=summary,
                type=self._infer_document_type(markdown_content),
                category="document",
                authors=[],
                tags=list(set(keywords))[:10],  # Unique keywords, max 10
                file_path=s3_file_path,
                original_filename=original_filename,
                summary=summary,
                word_count=len(markdown_content.split()),
                page_count=None
            )
            
            logger.info(f"✅ Step 2 completed: Extracted metadata")
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Step 2 failed: {e}")
            raise

    def _infer_document_type(self, content: str) -> str:
        """Infer document type from content - from metadata_extractor_worker.py."""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['report', 'analysis', 'findings', 'conclusion']):
            return 'report'
        elif any(word in content_lower for word in ['manual', 'guide', 'instructions', 'how to']):
            return 'manual'
        elif any(word in content_lower for word in ['article', 'paper', 'research', 'study']):
            return 'article'
        elif any(word in content_lower for word in ['specification', 'requirements', 'specs']):
            return 'specification'
        else:
            return 'document'

    async def step3_index_to_typesense(self, metadata: DocumentMetadata, document_id: str) -> None:
        """Step 3: Index to Typesense - from typesense_indexer_worker.py."""
        try:
            logger.info(f"🔍 Step 3: Indexing to Typesense for document {document_id}")
            
            # Prepare document for Typesense
            current_timestamp = int(datetime.utcnow().timestamp())
            
            typesense_document = {
                'id': document_id,
                'title': metadata.title,
                'description': metadata.description,
                'summary': metadata.summary,
                'type': metadata.type,
                'category': metadata.category,
                'authors': metadata.authors,
                'tags': metadata.tags,
                'date': metadata.date,
                'language': metadata.language,
                'word_count': metadata.word_count,
                'page_count': metadata.page_count,
                'file_path': metadata.file_path,
                'original_filename': metadata.original_filename,
                'created_at': current_timestamp,
                'updated_at': current_timestamp,
            }
            
            def index_document():
                # Upsert document (create or update)
                return self.typesense_client.collections[settings.typesense_collection_name].documents.upsert(
                    typesense_document
                )
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, index_document)
            
            logger.info(f"✅ Step 3 completed: Indexed document to Typesense")
            
        except Exception as e:
            logger.error(f"❌ Step 3 failed: {e}")
            raise

    async def step4_index_to_qdrant(self, markdown_content: str, metadata: DocumentMetadata, document_id: str) -> None:
        """Step 4: Index to Qdrant - from setup_proper_qdrant_collection.py."""
        try:
            logger.info(f"🔍 Step 4: Indexing to Qdrant for document {document_id}")
            
            def create_and_index():
                # Configure LlamaIndex settings - following setup_proper_qdrant_collection.py pattern
                Settings.llm = OpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.openai_api_key,
                    temperature=0.1
                )
                Settings.embed_model = OpenAIEmbedding(
                    model="text-embedding-3-small", 
                    api_key=settings.openai_api_key
                )
                Settings.chunk_size = 512  # Following documentation
                
                # Create vector store and storage context at processing time
                vector_store = QdrantVectorStore(
                    collection_name=settings.qdrant_collection_name,
                    client=self.qdrant_client,
                    # No hybrid for now to avoid PyTorch conflicts
                )
                
                # Create storage context
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                
                # Create LlamaIndex document with metadata
                doc_metadata = {
                    "document_id": document_id,
                    "title": metadata.title,
                    "type": metadata.type,
                    "category": metadata.category,
                    "authors": ", ".join(metadata.authors),
                    "file_path": metadata.file_path,
                    "original_filename": metadata.original_filename,
                    "summary": metadata.summary,
                    "tags": ", ".join(metadata.tags),
                }
                
                # Create document
                document = Document(
                    text=markdown_content,
                    metadata=doc_metadata
                )
                
                # Create index with explicit storage context - following the working pattern
                index = VectorStoreIndex.from_documents(
                    [document],
                    storage_context=storage_context,
                    show_progress=True
                )
                
                return 1  # One document processed
            
            loop = asyncio.get_event_loop()
            chunks_created = await loop.run_in_executor(None, create_and_index)
            
            logger.info(f"✅ Step 4 completed: Indexed {chunks_created} document to Qdrant")
            
        except Exception as e:
            logger.error(f"❌ Step 4 failed: {e}")
            raise

    def update_job_progress(self, document_id: str, step: int, progress: int, status: str = "in_progress"):
        """Update job progress in Redis."""
        try:
            key = f"document_processing:{document_id}"
            progress_data = {
                f"step_{step}_status": status,
                f"step_{step}_progress": progress,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            self.redis_client.hset(key, mapping=progress_data)
            logger.info(f"📊 Updated progress: Document {document_id}, Step {step}: {progress}% ({status})")
            
        except Exception as e:
            logger.error(f"❌ Failed to update progress: {e}")

    async def process_document(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a document through all 4 steps."""
        s3_file_path = job_data['s3_file_path']
        document_id = job_data['document_id']
        file_name = job_data.get('file_name', os.path.basename(s3_file_path))
        
        temp_file_path = None
        
        try:
            logger.info(f"🚀 Starting document processing: {document_id}")
            
            # Initialize job progress
            self.update_job_progress(document_id, 1, 0, "in_progress")
            
            # Download file from S3
            temp_file_path = await self.download_file_from_s3(s3_file_path)
            
            # Step 1: Convert to markdown
            self.update_job_progress(document_id, 1, 25, "in_progress")
            markdown_content = await self.step1_convert_to_markdown(temp_file_path)
            self.update_job_progress(document_id, 1, 100, "completed")
            
            # Step 2: Extract metadata
            self.update_job_progress(document_id, 2, 0, "in_progress")
            metadata = await self.step2_extract_metadata(markdown_content, document_id, s3_file_path, file_name)
            self.update_job_progress(document_id, 2, 100, "completed")
            
            # Step 3: Index to Typesense
            self.update_job_progress(document_id, 3, 0, "in_progress")
            await self.step3_index_to_typesense(metadata, document_id)
            self.update_job_progress(document_id, 3, 100, "completed")
            
            # Step 4: Index to Qdrant
            if self.qdrant_enabled:
                self.update_job_progress(document_id, 4, 0, "in_progress")
                await self.step4_index_to_qdrant(markdown_content, metadata, document_id)
                self.update_job_progress(document_id, 4, 100, "completed")
            else:
                logger.warning(f"⚠️ Skipping Step 4 (Qdrant) - not available")
                self.update_job_progress(document_id, 4, 100, "skipped")
            
            # Mark overall job as completed
            self.redis_client.hset(
                f"document_processing:{document_id}",
                mapping={
                    "status": "completed",
                    "overall_progress": 100,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(f"🎉 Document processing completed: {document_id}")
            
            return {
                "document_id": document_id,
                "status": "completed",
                "title": metadata.title
            }
            
        except Exception as e:
            logger.error(f"❌ Document processing failed for {document_id}: {e}")
            
            # Mark job as failed
            self.redis_client.hset(
                f"document_processing:{document_id}",
                mapping={
                    "status": "failed",
                    "error": str(e),
                    "failed_at": datetime.utcnow().isoformat()
                }
            )
            
            raise
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    # Remove temp directory if empty
                    temp_dir = os.path.dirname(temp_file_path)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
                    logger.info(f"🧹 Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to clean up temp file {temp_file_path}: {e}")

    async def process_job(self, job: Job, job_token: str):
        """Process a single job from the queue."""
        try:
            job_data = job.data
            document_id = job_data.get('document_id')
            
            logger.info(f"📝 Processing job {job.id} for document {document_id}")
            
            # Process the document
            result = await self.process_document(job_data)
            
            logger.info(f"✅ Job {job.id} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job {job.id} failed: {e}")
            raise

    async def start_worker(self):
        """Start the worker."""
        logger.info("🚀 Starting document processing worker...")
        
        # Create Redis connection string
        if settings.redis_password:
            redis_connection = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        else:
            redis_connection = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        
        self.worker = Worker(
            "document_processing",
            self.process_job,
            {"connection": redis_connection}
        )
        
        self.is_running = True
        logger.info("✅ Document processing worker started and waiting for jobs...")
        
        # Wait until the shutdown event is set to keep worker alive
        await self.shutdown_event.wait()


if __name__ == "__main__":
    # Create and start worker
    async def main():
        worker = DocumentProcessingWorker()
        
        try:
            # Set up signal handlers for graceful shutdown
            def signal_handler(signum, frame):
                logger.info("Signal received, shutting down.")
                worker.shutdown_event.set()
            
            # Assign signal handlers to SIGTERM and SIGINT
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
            
            logger.info("Document processing worker is running. Press Ctrl+C to stop.")
            
            # Start the worker (this will wait until shutdown)
            await worker.start_worker()
            
        except KeyboardInterrupt:
            logger.info("Document processing worker stopped by user")
        except Exception as e:
            logger.error(f"Document processing worker error: {e}")
        finally:
            # Close the worker
            logger.info("Cleaning up worker...")
            if hasattr(worker, 'worker') and worker.worker:
                await worker.worker.close()
            logger.info("Worker shut down successfully.")
    
    asyncio.run(main()) 