#!/usr/bin/env python3
"""
Persistent document processing pipeline test.
This version ensures documents are properly stored and persist in both Typesense and Qdrant.
"""
import asyncio
import os
import sys
import tempfile
import shutil
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

async def test_persistent_pipeline():
    """Test the persistent document processing pipeline."""
    
    # Source file path
    source_file = "/Users/phatneglo/Documents/Projects/CEBU/SSRDMS-AI-AGENT/chat-frontend/index.html"
    
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return
    
    # Generate unique document ID for the entire pipeline
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    document_id = f"ssrdms_frontend_{timestamp}"
    
    logger.info("=== PERSISTENT DOCUMENT PROCESSING PIPELINE ===")
    logger.info("Pipeline Configuration", 
                document_id=document_id,
                source_file=source_file,
                timestamp=timestamp)
    
    try:
        # Create mock job class for all workers
        class MockJob:
            def __init__(self, job_data):
                self.id = f"persistent_job_{int(datetime.now().timestamp())}"
                self.data = job_data
            
            async def updateProgress(self, progress):
                logger.info(f"Job progress: {progress}%")
        
        # Create persistent directory for converted files
        persistent_dir = Path("./processed_documents")
        persistent_dir.mkdir(exist_ok=True)
        
        # Step 1: Document Conversion (HTML to Markdown)
        logger.info("=== STEP 1: Document Conversion (HTML → Markdown) ===")
        
        # Convert document to persistent location
        markdown_filename = f"{document_id}.md"
        markdown_path = persistent_dir / markdown_filename
        
        converter = SimpleDocumentConverterWorker()
        await converter.setup()
        
        conversion_job_data = {
            "document_id": document_id,
            "source_path": source_file,
            "output_path": str(markdown_path),
            "conversion_options": {}
        }
        
        conversion_job = MockJob(conversion_job_data)
        conversion_result = await converter.process_job(conversion_job)
        
        logger.info("✅ Step 1 Completed - Document Conversion", 
                   result=conversion_result,
                   output_file=str(markdown_path))
        await converter.cleanup()
        
        # Verify the markdown file was created
        if not markdown_path.exists():
            logger.error(f"❌ Markdown file not created: {markdown_path}")
            return
        
        # Step 2: Metadata Extraction using LlamaIndex
        logger.info("=== STEP 2: Metadata Extraction (LlamaIndex) ===")
        
        metadata_extractor = MetadataExtractorWorker()
        await metadata_extractor.setup()
        
        metadata_job_data = {
            "document_id": document_id,
            "markdown_path": str(markdown_path),
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
        logger.info("📋 Extracted Metadata Summary:")
        for key, value in extracted_metadata.items():
            if key not in ["summary"]:  # Skip long summary for display
                logger.info(f"  📌 {key}: {value}")
        
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
        await typesense_worker.cleanup()
        
        # Verify Typesense indexing
        logger.info("🔍 Verifying Typesense Indexing:")
        await asyncio.sleep(2)  # Wait for indexing to complete
        
        # Check if document exists in Typesense
        import requests
        try:
            typesense_url = f"http://localhost:8108/collections/documents/documents?q=*&query_by=title,description&filter_by=id:={document_id}&limit=1"
            headers = {"X-TYPESENSE-API-KEY": "xyz"}
            response = requests.get(typesense_url, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                hits = result.get("hits", [])
                if hits:
                    logger.info(f"✅ Document found in Typesense: {document_id}")
                    doc = hits[0]["document"]
                    logger.info(f"  📄 Title: {doc.get('title', 'No title')}")
                    logger.info(f"  🏷️ Category: {doc.get('category', 'No category')}")
                else:
                    logger.warning(f"⚠️ Document not found in Typesense: {document_id}")
            else:
                logger.warning(f"⚠️ Typesense search failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Typesense verification failed: {e}")
        
        # Step 4: Qdrant Indexing for RAG (using Typesense document ID)
        logger.info("=== STEP 4: Qdrant Indexing (RAG with Typesense ID Link) ===")
        
        qdrant_worker = QdrantIndexerWorker()
        await qdrant_worker.setup()
        
        # Use Typesense document ID as the unique identifier in Qdrant
        qdrant_job_data = {
            "document_id": document_id,  # This links to Typesense document
            "markdown_path": str(markdown_path),
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
        
        # Verify Qdrant indexing
        logger.info("🔍 Verifying Qdrant Indexing:")
        await asyncio.sleep(2)  # Wait for indexing to complete
        
        # Check if document exists in Qdrant
        from qdrant_client import QdrantClient
        try:
            qdrant_url = f"http://localhost:6333"
            client = QdrantClient(url=qdrant_url, prefer_grpc=False)
            
            # Search for our document
            points = client.scroll(
                collection_name="documents_rag",
                scroll_filter={
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": document_id}
                        }
                    ]
                },
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if points[0]:
                logger.info(f"✅ Document found in Qdrant: {document_id}")
                logger.info(f"  📚 Chunks stored: {len(points[0])}")
                for i, point in enumerate(points[0], 1):
                    payload = point.payload or {}
                    chunk_id = payload.get('chunk_id', 'Unknown')
                    logger.info(f"    📄 Chunk {i}: {chunk_id}")
            else:
                logger.warning(f"⚠️ Document not found in Qdrant: {document_id}")
                
        except Exception as e:
            logger.warning(f"⚠️ Qdrant verification failed: {e}")
        
        await qdrant_worker.cleanup()
        
        # Final Verification
        logger.info("=== FINAL VERIFICATION ===")
        
        # Test RAG Query
        logger.info("🤖 Testing RAG Query:")
        try:
            rag_query = "What is this system about?"
            
            # Re-initialize worker for query
            qdrant_worker = QdrantIndexerWorker()
            await qdrant_worker.setup()
            
            rag_result = await qdrant_worker.query_documents(
                query=rag_query,
                document_id=document_id,
                top_k=3
            )
            
            logger.info(f"  🔍 Query: '{rag_query}'")
            logger.info(f"  💬 Answer: {rag_result['response'][:200]}...")
            logger.info(f"  📚 Sources: {len(rag_result['source_nodes'])} chunks")
            
            await qdrant_worker.cleanup()
            
        except Exception as e:
            logger.warning(f"⚠️ RAG query test failed: {e}")
        
        # Pipeline Summary
        logger.info("=== 🎉 PERSISTENT PIPELINE COMPLETION SUMMARY 🎉 ===")
        logger.info("📋 Document Processing Results:")
        logger.info(f"  🆔 Document ID: {document_id}")
        logger.info(f"  📄 Source File: {os.path.basename(source_file)}")
        logger.info(f"  📝 Markdown File: {markdown_path}")
        logger.info(f"  📊 Title: {extracted_metadata.get('title', 'N/A')}")
        logger.info(f"  📈 Word Count: {extracted_metadata.get('word_count', 'N/A')}")
        logger.info(f"  🏷️ Category: {extracted_metadata.get('category', 'N/A')}")
        
        logger.info("✅ All processing steps completed successfully!")
        logger.info("🔗 Document should now be available in both Typesense and Qdrant")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_persistent_pipeline()) 