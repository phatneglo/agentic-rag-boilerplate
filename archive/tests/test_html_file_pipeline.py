#!/usr/bin/env python3
"""
Test script to process the HTML file through the document conversion pipeline.
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

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def test_html_conversion():
    """Test the HTML file conversion to markdown."""
    
    # Source file path
    source_file = "/Users/phatneglo/Documents/Projects/CEBU/SSRDMS-AI-AGENT/chat-frontend/index.html"
    
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return
    
    # Generate unique document ID
    document_id = f"test_html_{uuid.uuid4().hex[:8]}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    logger.info("Starting HTML conversion test", 
                source_file=source_file, 
                document_id=document_id)
    
    try:
        # Step 1: Test document conversion worker directly
        logger.info("=== Step 1: HTML to Markdown Conversion ===")
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, f"{timestamp}_index.md")
            
            # Initialize converter worker
            converter = SimpleDocumentConverterWorker()
            await converter.setup()
            
            # Create mock job data
            class MockJob:
                def __init__(self, job_data):
                    self.id = f"test_job_{int(datetime.now().timestamp())}"
                    self.data = job_data
                
                async def updateProgress(self, progress):
                    logger.info(f"Job progress: {progress}%")
            
            job_data = {
                "document_id": document_id,
                "source_path": source_file,
                "output_path": output_path,
                "conversion_options": {}
            }
            
            mock_job = MockJob(job_data)
            
            # Process the conversion
            result = await converter.process_job(mock_job)
            
            logger.info("Document conversion completed", result=result)
            
            # Read the converted markdown
            with open(output_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            logger.info(f"Converted content length: {len(markdown_content)} characters")
            logger.info(f"Converted content preview (first 1000 chars):\n{markdown_content[:1000]}...")
            
            # Save a copy for inspection
            final_output = f"converted_index_{timestamp}.md"
            with open(final_output, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            logger.info(f"Saved converted file to: {final_output}")
            
            await converter.cleanup()
            
            # Step 2: Test Typesense indexing with the converted content
            logger.info("=== Step 2: Testing Typesense Indexing ===")
            
            try:
                from app.workers.typesense_indexer_worker import TypesenseIndexerWorker
                
                # Create metadata for Typesense indexing
                metadata = {
                    "document_id": document_id,
                    "title": "SSRDMS AI Agent Chat Frontend",
                    "description": "HTML page for SSRDMS AI Agent chat interface",
                    "type": "webpage", 
                    "category": "frontend",
                    "authors": ["Unknown"],
                    "tags": ["html", "chat", "frontend", "ai-agent"],
                    "language": "en",
                    "source_file": "index.html",
                    "word_count": len(markdown_content.split()),
                    "page_count": 1,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Test Typesense indexing
                typesense_worker = TypesenseIndexerWorker()
                await typesense_worker.setup()
                
                # Create job data for Typesense
                typesense_job_data = {
                    "document_id": document_id,
                    "metadata": metadata,
                    "content": markdown_content,
                    "file_path": f"test/{document_id}/index.md"
                }
                
                typesense_job = MockJob(typesense_job_data)
                
                typesense_result = await typesense_worker.process_job(typesense_job)
                logger.info("Typesense indexing completed", result=typesense_result)
                
                # Test search
                logger.info("=== Step 3: Testing Typesense Search ===")
                
                from app.services.typesense_service import TypesenseService
                
                typesense_service = TypesenseService()
                
                # Search for the indexed document
                search_queries = ["chat frontend", "SSRDMS", "AI agent", "html"]
                
                for query in search_queries:
                    search_results = await typesense_service.search_documents(
                        query=query,
                        collection="documents"
                    )
                    
                    hits = search_results.get('hits', [])
                    logger.info(f"Search results for '{query}': {len(hits)} hits")
                    
                    if hits:
                        for i, hit in enumerate(hits[:2]):  # Show first 2 results
                            doc = hit['document']
                            score = hit.get('text_match_info', {}).get('score', 'N/A')
                            logger.info(f"  {i+1}. {doc.get('title', 'No title')} (Score: {score})")
                    
                await typesense_worker.cleanup()
                
            except Exception as e:
                logger.error(f"Typesense processing failed: {e}")
                logger.info("Continuing without Typesense indexing...")
        
        logger.info("=== Conversion Test Completed Successfully ===")
        
    except Exception as e:
        logger.error(f"Conversion test failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(test_html_conversion()) 