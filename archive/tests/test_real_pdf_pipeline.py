#!/usr/bin/env python3
"""
Test script for processing a real PDF file through the complete 4-step pipeline:
1. Document conversion (PDF -> Markdown)
2. Metadata extraction with LlamaIndex
3. Typesense indexing with auto-embedding
4. Qdrant indexing for RAG

This test uses the uploaded PDF: uploads/2025/06/01/20250601_095925_Invoice_300716_2025_04_16_1.pdf
"""

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.utils.queue_manager import queue_manager
from app.services.object_storage_service import ObjectStorageService
from app.core.logging_config import get_logger, configure_logging

# Setup logging
configure_logging()
logger = get_logger("test_real_pdf_pipeline")

# The uploaded PDF file path
PDF_FILE_PATH = "uploads/2025/06/01/20250601_095925_Invoice_300716_2025_04_16_1.pdf"

async def test_real_pdf_pipeline():
    """Test the complete pipeline with the real uploaded PDF file."""
    
    logger.info("Starting complete pipeline test with real PDF file")
    logger.info(f"Processing file: {PDF_FILE_PATH}")
    
    try:
        # Initialize object storage service
        object_storage = ObjectStorageService()
        
        # Create temporary directory for downloads
        temp_dir = tempfile.mkdtemp(prefix="real_pdf_test_")
        logger.info(f"Created temporary directory: {temp_dir}")
        
        # Download the PDF file locally (workers need local paths)
        local_pdf_path = os.path.join(temp_dir, "invoice.pdf")
        logger.info(f"Downloading PDF from object storage to: {local_pdf_path}")
        
        await object_storage.download_file(PDF_FILE_PATH, temp_dir)
        downloaded_file = os.path.join(temp_dir, os.path.basename(PDF_FILE_PATH))
        
        if not os.path.exists(downloaded_file):
            raise FileNotFoundError(f"Failed to download file to {downloaded_file}")
        
        logger.info(f"PDF downloaded successfully: {downloaded_file}")
        logger.info(f"File size: {os.path.getsize(downloaded_file)} bytes")
        
        # Job IDs for tracking
        job_id_base = f"real_pdf_test_{int(time.time() * 1000)}"
        
        # Step 1: Document Conversion (PDF -> Markdown)
        logger.info("=== STEP 1: Document Conversion ===")
        step1_job_id = f"{job_id_base}_step1"
        step1_output_path = os.path.join(temp_dir, "converted.md")
        
        step1_job_data = {
            "source_path": downloaded_file,
            "output_path": step1_output_path,
            "job_id": step1_job_id,
            "user_id": "test_user",
            "document_id": "real_pdf_doc"
        }
        
        step1_job = await queue_manager.add_job(
            queue_name="document_processing:simple_document_converter",
            job_name="convert_document",
            job_data=step1_job_data,
            options={"jobId": step1_job_id}
        )
        
        logger.info(f"Step 1 job queued: {step1_job}")
        
        # Wait for Step 1 completion
        step1_result = await wait_for_job_completion(step1_job_id, "document_processing:simple_document_converter", timeout=120)
        if not step1_result["success"]:
            raise Exception(f"Step 1 failed: {step1_result['error']}")
        
        logger.info("Step 1 completed successfully")
        if os.path.exists(step1_output_path):
            with open(step1_output_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            logger.info(f"Markdown content length: {len(markdown_content)} characters")
            logger.info(f"Markdown preview: {markdown_content[:200]}...")
        
        # Step 2: Metadata Extraction
        logger.info("=== STEP 2: Metadata Extraction ===")
        step2_job_id = f"{job_id_base}_step2"
        step2_output_path = os.path.join(temp_dir, "metadata.json")
        
        step2_job_data = {
            "source_path": step1_output_path,
            "output_path": step2_output_path,
            "job_id": step2_job_id,
            "user_id": "test_user",
            "document_id": "real_pdf_doc"
        }
        
        step2_job = await queue_manager.add_job(
            queue_name="document_processing:metadata_extractor",
            job_name="extract_metadata",
            job_data=step2_job_data,
            options={"jobId": step2_job_id}
        )
        
        logger.info(f"Step 2 job queued: {step2_job}")
        
        # Wait for Step 2 completion
        step2_result = await wait_for_job_completion(step2_job_id, "document_processing:metadata_extractor", timeout=120)
        if not step2_result["success"]:
            raise Exception(f"Step 2 failed: {step2_result['error']}")
        
        logger.info("Step 2 completed successfully")
        if os.path.exists(step2_output_path):
            import json
            with open(step2_output_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            logger.info(f"Extracted metadata: {json.dumps(metadata, indent=2)}")
        
        # Step 3: Typesense Indexing
        logger.info("=== STEP 3: Typesense Indexing ===")
        step3_job_id = f"{job_id_base}_step3"
        
        step3_job_data = {
            "source_path": step2_output_path,
            "job_id": step3_job_id,
            "user_id": "test_user",
            "document_id": "real_pdf_doc"
        }
        
        step3_job = await queue_manager.add_job(
            queue_name="document_processing:typesense_indexer",
            job_name="index_to_typesense",
            job_data=step3_job_data,
            options={"jobId": step3_job_id}
        )
        
        logger.info(f"Step 3 job queued: {step3_job}")
        
        # Wait for Step 3 completion
        step3_result = await wait_for_job_completion(step3_job_id, "document_processing:typesense_indexer", timeout=120)
        if not step3_result["success"]:
            raise Exception(f"Step 3 failed: {step3_result['error']}")
        
        logger.info("Step 3 completed successfully")
        
        # Step 4: Qdrant Indexing for RAG
        logger.info("=== STEP 4: Qdrant Indexing ===")
        step4_job_id = f"{job_id_base}_step4"
        
        step4_job_data = {
            "source_path": step1_output_path,  # Use markdown content for RAG
            "metadata_path": step2_output_path,
            "job_id": step4_job_id,
            "user_id": "test_user",
            "document_id": "real_pdf_doc"
        }
        
        step4_job = await queue_manager.add_job(
            queue_name="document_processing:qdrant_indexer",
            job_name="index_to_qdrant",
            job_data=step4_job_data,
            options={"jobId": step4_job_id}
        )
        
        logger.info(f"Step 4 job queued: {step4_job}")
        
        # Wait for Step 4 completion
        step4_result = await wait_for_job_completion(step4_job_id, "document_processing:qdrant_indexer", timeout=120)
        if not step4_result["success"]:
            raise Exception(f"Step 4 failed: {step4_result['error']}")
        
        logger.info("Step 4 completed successfully")
        
        # Verify pipeline results
        logger.info("=== PIPELINE VERIFICATION ===")
        
        # Test Typesense search
        logger.info("Testing Typesense search...")
        await test_typesense_search("invoice")
        
        # Test Qdrant RAG query
        logger.info("Testing Qdrant RAG query...")
        await test_qdrant_rag_query("What is this invoice about?")
        
        logger.info("=== COMPLETE PIPELINE TEST SUCCESSFUL ===")
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}", exc_info=True)
        raise
    finally:
        # Cleanup temporary files
        import shutil
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")

async def wait_for_job_completion(job_id: str, queue_name: str, timeout: int = 60) -> dict:
    """Wait for a job to complete and return the result."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            job_status = await queue_manager.get_job_status(queue_name, job_id)
            
            if job_status.get("status") == "not_found":
                logger.warning(f"Job {job_id} not found, waiting...")
                await asyncio.sleep(2)
                continue
            
            status = job_status.get("status", "unknown")
            logger.info(f"Job {job_id} status: {status}")
            
            if status in ["completed", "finished"]:
                return {"success": True, "result": job_status}
            elif status in ["failed", "error"]:
                return {"success": False, "error": job_status.get("failed_reason", "Unknown error")}
            
            await asyncio.sleep(2)  # Wait 2 seconds before checking again
            
        except Exception as e:
            logger.error(f"Error checking job {job_id}: {str(e)}")
            await asyncio.sleep(2)
    
    return {"success": False, "error": f"Job {job_id} timed out after {timeout} seconds"}

async def test_typesense_search(query: str):
    """Test Typesense search functionality."""
    try:
        import typesense
        
        client = typesense.Client({
            'nodes': [{
                'host': 'localhost',
                'port': '8108',
                'protocol': 'http'
            }],
            'api_key': 'xyz',  # Default development key
            'connection_timeout_seconds': 2
        })
        
        # Search in documents collection
        search_parameters = {
            'q': query,
            'query_by': 'title,description,tags',
            'limit': 5
        }
        
        results = client.collections['documents'].documents.search(search_parameters)
        logger.info(f"Typesense search results for '{query}':")
        logger.info(f"Found {results['found']} documents")
        
        for hit in results['hits']:
            doc = hit['document']
            logger.info(f"- Document ID: {doc.get('id', 'N/A')}")
            logger.info(f"  Title: {doc.get('title', 'N/A')}")
            logger.info(f"  Description: {doc.get('description', 'N/A')[:100]}...")
            
    except Exception as e:
        logger.error(f"Typesense search test failed: {str(e)}")

async def test_qdrant_rag_query(query: str):
    """Test Qdrant RAG query functionality."""
    try:
        from llama_index.core import VectorStoreIndex, StorageContext
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        from qdrant_client import QdrantClient
        
        # Initialize Qdrant client and vector store
        client = QdrantClient(host="localhost", port=6333)
        vector_store = QdrantVectorStore(client=client, collection_name="documents")
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        # Create index from existing vector store
        index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
        
        # Create query engine
        query_engine = index.as_query_engine()
        
        # Perform RAG query
        logger.info(f"Performing RAG query: '{query}'")
        response = query_engine.query(query)
        
        logger.info(f"RAG Response: {str(response)}")
        
        # Check collection status
        collection_info = client.get_collection("documents")
        logger.info(f"Qdrant collection status: {collection_info.points_count} points total")
        
    except Exception as e:
        logger.error(f"Qdrant RAG query test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_real_pdf_pipeline()) 