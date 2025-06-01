#!/usr/bin/env python3
"""
Full end-to-end test: Upload PDF → Complete 4-step pipeline → Verify results
Tests the entire document processing pipeline with a real PDF upload.
"""
import asyncio
import os
import sys
import requests
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.workers.simple_document_converter_worker import SimpleDocumentConverterWorker
from app.workers.metadata_extractor_worker import MetadataExtractorWorker
from app.workers.typesense_indexer_worker import TypesenseIndexerWorker
from app.workers.qdrant_indexer_worker import QdrantIndexerWorker
from app.services.object_storage_service import ObjectStorageService

# Configure logging
configure_logging()
logger = get_logger(__name__)

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port
UPLOAD_ENDPOINT = f"{API_BASE_URL}/api/v1/files/upload"

async def create_test_pdf():
    """Create a simple test PDF for upload."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        pdf_path = "test_document.pdf"
        
        # Create a simple PDF
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Add content
        c.drawString(100, height - 100, "Test PDF Document for Pipeline Testing")
        c.drawString(100, height - 130, "")
        c.drawString(100, height - 160, "This is a sample PDF document created for testing the")
        c.drawString(100, height - 180, "complete 4-step document processing pipeline.")
        c.drawString(100, height - 210, "")
        c.drawString(100, height - 240, "Content includes:")
        c.drawString(120, height - 270, "• Document conversion (PDF to Markdown)")
        c.drawString(120, height - 290, "• Metadata extraction using LlamaIndex")
        c.drawString(120, height - 310, "• Typesense indexing with auto-embedding")
        c.drawString(120, height - 330, "• Qdrant vector storage for RAG")
        c.drawString(100, height - 370, "")
        c.drawString(100, height - 400, "Keywords: AI, document processing, RAG, vector search")
        c.drawString(100, height - 430, "Category: Technical Documentation")
        c.drawString(100, height - 460, "Author: Test System")
        c.drawString(100, height - 490, f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
        logger.info(f"✅ Created test PDF: {pdf_path}")
        return pdf_path
        
    except ImportError:
        logger.warning("⚠️ reportlab not available, creating simple text file instead")
        # Fallback to text file
        txt_path = "test_document.txt"
        with open(txt_path, 'w') as f:
            f.write("Test Document for Pipeline Testing\n\n")
            f.write("This is a sample document created for testing the complete 4-step document processing pipeline.\n\n")
            f.write("Content includes:\n")
            f.write("• Document conversion to Markdown\n")
            f.write("• Metadata extraction using LlamaIndex\n")
            f.write("• Typesense indexing with auto-embedding\n")
            f.write("• Qdrant vector storage for RAG\n\n")
            f.write("Keywords: AI, document processing, RAG, vector search\n")
            f.write("Category: Technical Documentation\n")
            f.write("Author: Test System\n")
            f.write(f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        logger.info(f"✅ Created test file: {txt_path}")
        return txt_path

async def upload_file_via_api(file_path: str):
    """Upload file via the API endpoint."""
    try:
        logger.info(f"📤 Uploading file via API: {file_path}")
        
        with open(file_path, 'rb') as f:
            # API expects 'files' (plural) with multiple files support
            files = {'files': (os.path.basename(file_path), f, 'application/pdf')}
            
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                timeout=30
            )
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"✅ File uploaded successfully: {result}")
            
            # Extract the first file info from the response
            if 'files' in result and len(result['files']) > 0:
                return result['files'][0]  # Return first file info
            else:
                return result
        else:
            logger.error(f"❌ Upload failed: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return None

async def download_file_locally(file_path: str, filename: str) -> str:
    """Download file from object storage to local temporary directory."""
    try:
        logger.info(f"📥 Downloading file from object storage: {file_path}")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Use object storage service to download
        storage_service = ObjectStorageService()
        await storage_service.download_file(file_path, temp_dir)
        
        # Find the downloaded file
        local_file_path = os.path.join(temp_dir, filename)
        
        if os.path.exists(local_file_path):
            logger.info(f"✅ File downloaded to: {local_file_path}")
            return local_file_path
        else:
            # Try to find any file in the temp directory
            files = os.listdir(temp_dir)
            if files:
                local_file_path = os.path.join(temp_dir, files[0])
                logger.info(f"✅ File downloaded to: {local_file_path}")
                return local_file_path
            else:
                raise FileNotFoundError("No file found after download")
                
    except Exception as e:
        logger.error(f"❌ Failed to download file: {e}")
        raise

async def process_through_pipeline(file_info: dict):
    """Process the uploaded file through the complete 4-step pipeline."""
    
    try:
        logger.info("=== STARTING COMPLETE PIPELINE PROCESSING ===")
        
        # Extract file information
        file_path = file_info.get('file_path') or file_info.get('path')
        filename = file_info.get('filename') or file_info.get('original_filename') or file_info.get('name')
        document_id = f"pipeline_test_{int(time.time())}"
        
        logger.info(f"📄 Processing file: {filename}")
        logger.info(f"🆔 Document ID: {document_id}")
        logger.info(f"📂 File path: {file_path}")
        
        # Download file locally first (since workers expect local files)
        logger.info("📥 Downloading file locally for processing...")
        local_file_path = await download_file_locally(file_path, filename)
        logger.info(f"✅ File downloaded locally: {local_file_path}")
        
        # === STEP 1: Document Conversion ===
        logger.info("=== STEP 1: Document Conversion ===")
        
        converter_worker = SimpleDocumentConverterWorker()
        await converter_worker.setup()
        
        # Create conversion job - use local file path
        output_filename = f"{document_id}.md"
        output_path = f"processed_documents/{output_filename}"
        
        conversion_job_data = {
            "document_id": document_id,
            "source_path": local_file_path,  # Use local downloaded file
            "output_path": output_path,  # Worker expects 'output_path'
            "conversion_options": {"target_format": "markdown"}
        }
        
        # Mock job object for testing
        class MockJob:
            def __init__(self, data):
                self.data = data
                self.id = f"job_{document_id}"
                self.progress = 0
            
            async def updateProgress(self, progress):
                self.progress = progress
                logger.info(f"Job progress: {progress}%")
        
        conversion_job = MockJob(conversion_job_data)
        conversion_result = await converter_worker.process_job(conversion_job)
        
        if not conversion_result["success"]:
            raise Exception(f"Document conversion failed: {conversion_result}")
        
        markdown_path = conversion_result["markdown_path"]
        logger.info(f"✅ Step 1 Completed - Markdown saved: {markdown_path}")
        
        # === STEP 2: Metadata Extraction ===
        logger.info("=== STEP 2: Metadata Extraction ===")
        
        metadata_worker = MetadataExtractorWorker()
        await metadata_worker.setup()
        
        metadata_job_data = {
            "document_id": document_id,
            "markdown_path": markdown_path,
            "original_filename": filename,
            "extraction_options": {}
        }
        
        metadata_job = MockJob(metadata_job_data)
        metadata_result = await metadata_worker.process_job(metadata_job)
        
        if not metadata_result["success"]:
            raise Exception(f"Metadata extraction failed: {metadata_result}")
        
        extracted_metadata = metadata_result["metadata"]
        logger.info(f"✅ Step 2 Completed - Metadata extracted: {len(extracted_metadata)} fields")
        
        # === STEP 3: Typesense Indexing ===
        logger.info("=== STEP 3: Typesense Indexing ===")
        
        typesense_worker = TypesenseIndexerWorker()
        await typesense_worker.setup()
        
        typesense_job_data = {
            "document_id": document_id,
            "markdown_path": markdown_path,
            "metadata": extracted_metadata,
            "indexing_options": {}
        }
        
        typesense_job = MockJob(typesense_job_data)
        typesense_result = await typesense_worker.process_job(typesense_job)
        
        if not typesense_result["success"]:
            raise Exception(f"Typesense indexing failed: {typesense_result}")
        
        logger.info(f"✅ Step 3 Completed - Typesense Indexing")
        
        # === STEP 4: Qdrant Indexing ===
        logger.info("=== STEP 4: Qdrant Indexing (RAG) ===")
        
        qdrant_worker = QdrantIndexerWorker()
        await qdrant_worker.setup()
        
        qdrant_job_data = {
            "document_id": document_id,
            "markdown_path": markdown_path,
            "metadata": extracted_metadata,
            "indexing_options": {}
        }
        
        qdrant_job = MockJob(qdrant_job_data)
        qdrant_result = await qdrant_worker.process_job(qdrant_job)
        
        if not qdrant_result["success"]:
            raise Exception(f"Qdrant indexing failed: {qdrant_result}")
        
        logger.info(f"✅ Step 4 Completed - Qdrant RAG Indexing")
        
        # === VERIFICATION ===
        logger.info("=== VERIFICATION ===")
        
        # Test RAG query
        logger.info("🔍 Testing RAG Query...")
        query_result = await qdrant_worker.query_documents(
            query="What is this document about?",
            top_k=3
        )
        
        logger.info(f"🤖 RAG Response: {query_result['response']}")
        logger.info(f"📚 Sources: {len(query_result['source_nodes'])} chunks")
        
        # Cleanup workers
        await converter_worker.cleanup()
        await metadata_worker.cleanup()  
        await typesense_worker.cleanup()
        await qdrant_worker.cleanup()
        
        # Cleanup temporary file
        try:
            temp_dir = os.path.dirname(local_file_path)
            shutil.rmtree(temp_dir)
            logger.info(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to cleanup temporary directory: {e}")
        
        logger.info("=== 🎉 COMPLETE PIPELINE SUCCESS! 🎉 ===")
        logger.info(f"📄 Document: {filename}")
        logger.info(f"🆔 Document ID: {document_id}")
        logger.info(f"📝 Markdown: {markdown_path}")
        logger.info(f"📊 Metadata Fields: {len(extracted_metadata)}")
        logger.info(f"🔍 Typesense: Indexed with auto-embedding")
        logger.info(f"🤖 Qdrant: Ready for RAG queries")
        
        return {
            "success": True,
            "document_id": document_id,
            "markdown_path": markdown_path,
            "metadata": extracted_metadata,
            "typesense_result": typesense_result,
            "qdrant_result": qdrant_result,
            "rag_query": query_result
        }
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

async def test_full_pdf_pipeline():
    """Run the complete end-to-end test."""
    
    try:
        logger.info("🚀 STARTING FULL PDF PIPELINE TEST")
        
        # 1. Create test file
        test_file_path = await create_test_pdf()
        
        # 2. Check if API is running
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ API is running")
                
                # 3. Upload via API
                upload_result = await upload_file_via_api(test_file_path)
                if upload_result:
                    # 4. Process through pipeline
                    pipeline_result = await process_through_pipeline(upload_result)
                    
                    if pipeline_result["success"]:
                        logger.info("🎉 FULL PIPELINE TEST COMPLETED SUCCESSFULLY!")
                    else:
                        logger.error(f"❌ Pipeline processing failed: {pipeline_result.get('error')}")
                else:
                    logger.error("❌ File upload failed")
                    
        except requests.exceptions.RequestException:
            logger.warning("⚠️ API not running, testing pipeline directly")
            
            # Direct pipeline test without API upload
            file_info = {
                'file_path': test_file_path,
                'filename': os.path.basename(test_file_path)
            }
            
            pipeline_result = await process_through_pipeline(file_info)
            
            if pipeline_result["success"]:
                logger.info("🎉 DIRECT PIPELINE TEST COMPLETED SUCCESSFULLY!")
            else:
                logger.error(f"❌ Pipeline processing failed: {pipeline_result.get('error')}")
        
        # Cleanup test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            logger.info(f"🧹 Cleaned up test file: {test_file_path}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_full_pdf_pipeline()) 