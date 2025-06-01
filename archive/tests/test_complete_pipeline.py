#!/usr/bin/env python3
"""
Complete 4-step document processing pipeline test:
1. Convert document to Markdown using simple converter
2. Extract structured metadata using LlamaIndex
3. Save to Typesense with embeddings for key fields (title, description, tags)
4. Store in Qdrant using Typesense document ID as unique identifier for RAG
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime
import uuid

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.workers.simple_document_converter_worker import SimpleDocumentConverterWorker
from app.workers.metadata_extractor_worker import MetadataExtractorWorker
from app.workers.typesense_indexer_worker import TypesenseIndexerWorker
from app.workers.qdrant_indexer_worker import QdrantIndexerWorker

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def test_complete_pipeline():
    """Test the complete 4-step document processing pipeline."""
    
    # Source file path
    source_file = "/Users/phatneglo/Documents/Projects/CEBU/SSRDMS-AI-AGENT/chat-frontend/index.html"
    
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return
    
    # Generate unique document ID for the entire pipeline
    document_id = f"ssrdms_chat_frontend_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("=== Starting Complete Document Processing Pipeline ===")
    logger.info("Pipeline Configuration", 
                document_id=document_id,
                source_file=source_file,
                timestamp=timestamp)
    
    try:
        # Create mock job class for all workers
        class MockJob:
            def __init__(self, job_data):
                self.id = f"pipeline_job_{int(datetime.now().timestamp())}"
                self.data = job_data
            
            async def updateProgress(self, progress):
                logger.info(f"Job progress: {progress}%")
        
        # Step 1: Document Conversion (HTML to Markdown)
        logger.info("=== STEP 1: Document Conversion (HTML → Markdown) ===")
        
        # Create temporary directory for the entire pipeline
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Convert document
            markdown_path = os.path.join(temp_dir, f"{timestamp}_converted.md")
            
            converter = SimpleDocumentConverterWorker()
            await converter.setup()
            
            conversion_job_data = {
                "document_id": document_id,
                "source_path": source_file,
                "output_path": markdown_path,
                "conversion_options": {}
            }
            
            conversion_job = MockJob(conversion_job_data)
            conversion_result = await converter.process_job(conversion_job)
            
            logger.info("✅ Step 1 Completed - Document Conversion", result=conversion_result)
            await converter.cleanup()
            
            # Step 2: Metadata Extraction using LlamaIndex
            logger.info("=== STEP 2: Metadata Extraction (LlamaIndex) ===")
            
            metadata_extractor = MetadataExtractorWorker()
            await metadata_extractor.setup()
            
            metadata_job_data = {
                "document_id": document_id,
                "markdown_path": markdown_path,
                "original_file_path": source_file,
                "original_filename": os.path.basename(source_file),
                "extraction_options": {
                    "language": "en",
                    "page_count": 1
                }
            }
            
            metadata_job = MockJob(metadata_job_data)
            metadata_result = await metadata_extractor.process_job(metadata_job)
            
            logger.info("✅ Step 2 Completed - Metadata Extraction", 
                       extracted_fields=len(metadata_result["metadata"]))
            
            # Display extracted metadata
            extracted_metadata = metadata_result["metadata"]
            logger.info("Extracted Metadata Summary:")
            for key, value in extracted_metadata.items():
                if key not in ["summary"]:  # Skip long summary for display
                    logger.info(f"  {key}: {value}")
            
            await metadata_extractor.cleanup()
            
            # Step 3: Typesense Indexing with Auto-Embeddings
            logger.info("=== STEP 3: Typesense Indexing (Search + Auto-Embeddings) ===")
            
            typesense_worker = TypesenseIndexerWorker()
            await typesense_worker.setup()
            
            # Use the extracted metadata for Typesense indexing
            typesense_job_data = {
                "document_id": document_id,
                "metadata": extracted_metadata,
                "embeddings": metadata_result.get("embeddings", {}),
                "indexing_options": {
                    "auto_embed": True,  # Use Typesense auto-embedding
                    "collection": "documents"
                }
            }
            
            typesense_job = MockJob(typesense_job_data)
            typesense_result = await typesense_worker.process_job(typesense_job)
            
            logger.info("✅ Step 3 Completed - Typesense Indexing", result=typesense_result)
            
            # Test Typesense search
            logger.info("Testing Typesense Search Capabilities:")
            
            from app.services.typesense_indexer_service import TypesenseIndexerService
            typesense_service = TypesenseIndexerService()
            
            search_queries = [
                "SSRDMS chat frontend",
                "beneficiaries management",
                "AI assistants",
                "database expert"
            ]
            
            for query in search_queries:
                try:
                    search_results = await typesense_service.search_documents(
                        collection="documents",
                        query=query,
                        query_by="title,description,summary",
                        limit=3
                    )
                    
                    hits = search_results.get("hits", [])
                    logger.info(f"  🔍 '{query}': {len(hits)} hits found")
                    
                    for hit in hits[:1]:  # Show first hit
                        doc = hit["document"]
                        score = hit.get("text_match_info", {}).get("score", "N/A")
                        logger.info(f"    📄 {doc.get('title', 'No title')} (Score: {score})")
                        
                except Exception as e:
                    logger.warning(f"Search failed for '{query}': {e}")
            
            await typesense_worker.cleanup()
            
            # Step 4: Qdrant Indexing for RAG (using Typesense document ID)
            logger.info("=== STEP 4: Qdrant Indexing (RAG with Typesense ID Link) ===")
            
            qdrant_worker = QdrantIndexerWorker()
            await qdrant_worker.setup()
            
            # Use Typesense document ID as the unique identifier in Qdrant
            qdrant_job_data = {
                "document_id": document_id,  # This links to Typesense document
                "markdown_path": markdown_path,
                "metadata": extracted_metadata,
                "indexing_options": {
                    "chunk_size": 1024,
                    "chunk_overlap": 200,
                    "collection": "documents_rag"
                }
            }
            
            qdrant_job = MockJob(qdrant_job_data)
            qdrant_result = await qdrant_worker.process_job(qdrant_job)
            
            logger.info("✅ Step 4 Completed - Qdrant RAG Indexing", result=qdrant_result)
            
            # Test RAG Query
            logger.info("Testing RAG Query Capabilities:")
            
            rag_queries = [
                "What is the purpose of this system?",
                "How do I register a new beneficiary?", 
                "What types of agents are available?",
                "Explain the authentication process"
            ]
            
            for query in rag_queries:
                try:
                    rag_result = await qdrant_worker.query_documents(
                        query=query,
                        document_id=document_id,
                        top_k=3
                    )
                    
                    logger.info(f"  🤖 RAG Query: '{query}'")
                    logger.info(f"    💬 Answer: {rag_result['response'][:200]}...")
                    logger.info(f"    📚 Sources: {len(rag_result['source_nodes'])} chunks")
                    
                except Exception as e:
                    logger.warning(f"RAG query failed for '{query}': {e}")
            
            await qdrant_worker.cleanup()
            
            # Pipeline Summary
            logger.info("=== PIPELINE COMPLETION SUMMARY ===")
            logger.info("📋 Document Processing Results:")
            logger.info(f"  📄 Document ID: {document_id}")
            logger.info(f"  📁 Source File: {os.path.basename(source_file)}")
            logger.info(f"  📝 Title: {extracted_metadata.get('title', 'N/A')}")
            logger.info(f"  📊 Word Count: {extracted_metadata.get('word_count', 'N/A')}")
            logger.info(f"  🏷️ Tags: {', '.join(extracted_metadata.get('tags', []))}")
            logger.info(f"  📂 Category: {extracted_metadata.get('category', 'N/A')}")
            
            logger.info("🔧 Processing Steps Completed:")
            logger.info(f"  ✅ Step 1: HTML → Markdown conversion")
            logger.info(f"  ✅ Step 2: LlamaIndex metadata extraction")
            logger.info(f"  ✅ Step 3: Typesense indexing with auto-embeddings")
            logger.info(f"  ✅ Step 4: Qdrant RAG indexing with shared document ID")
            
            logger.info("🔗 Integration Features:")
            logger.info(f"  🔍 Full-text search available in Typesense")
            logger.info(f"  🤖 RAG queries available in Qdrant") 
            logger.info(f"  🆔 Shared document ID: {document_id}")
            logger.info(f"  📈 Auto-embeddings: title, description, summary")
            
            logger.info("=== 🎉 PIPELINE COMPLETED SUCCESSFULLY! 🎉 ===")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_complete_pipeline()) 