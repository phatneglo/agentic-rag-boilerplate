#!/usr/bin/env python3
"""
Document Processing Pipeline Test Script.
Tests the complete 4-step pipeline end-to-end.
"""
import asyncio
import os
import sys
import json
import httpx
from pathlib import Path

# Add app to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings


async def test_pipeline():
    """Test the complete document processing pipeline."""
    
    base_url = f"http://{settings.api_host}:{settings.api_port}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print("🚀 Testing Document Processing Pipeline")
        print("=" * 50)
        
        # 1. Test health check
        print("\n1. Testing API Health...")
        try:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ API Health: {health_data.get('status', 'unknown')}")
                print(f"   Dependencies: {health_data.get('dependencies', {})}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return
        
        # 2. Test document processing health
        print("\n2. Testing Document Processing Health...")
        try:
            response = await client.get(f"{base_url}/api/v1/document-processing/health")
            if response.status_code == 200:
                health_data = response.json()
                print("✅ Document Processing Service: healthy")
                print(f"   Components: {health_data.get('components', {})}")
            else:
                print(f"❌ Document processing health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Document processing health error: {e}")
        
        # 3. Test API info
        print("\n3. Testing API Info...")
        try:
            response = await client.get(f"{base_url}/api")
            if response.status_code == 200:
                api_data = response.json()
                print(f"✅ API Info: {api_data.get('name', 'Unknown')}")
                print(f"   Version: {api_data.get('version', 'Unknown')}")
                
                # Show document processing endpoints
                doc_proc_endpoints = api_data.get('endpoints', {}).get('document_processing', {})
                if doc_proc_endpoints:
                    print("   Document Processing Endpoints:")
                    for endpoint, url in doc_proc_endpoints.items():
                        print(f"     - {endpoint}: {url}")
                else:
                    print("   ⚠️ Document processing endpoints not found")
            else:
                print(f"❌ API info failed: {response.status_code}")
        except Exception as e:
            print(f"❌ API info error: {e}")
        
        # 4. Create a test document
        print("\n4. Creating Test Document...")
        test_content = """
# Test Document

This is a test document for the processing pipeline.

## Introduction

This document demonstrates the capabilities of our document processing system.

## Key Features

- Document-to-Markdown conversion using Marker
- Metadata extraction using LlamaIndex
- Typesense indexing with embeddings
- Qdrant integration for RAG

## Summary

This pipeline provides a complete solution for document processing and indexing.
        """.strip()
        
        test_file_path = "test_document.md"
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        print(f"✅ Created test document: {test_file_path}")
        
        # 5. Test document processing by file path
        print("\n5. Testing Document Processing by File Path...")
        try:
            request_data = {
                "file_path": os.path.abspath(test_file_path),
                "processing_options": {
                    "conversion": {
                        "max_pages": 10
                    },
                    "metadata": {
                        "language": "en"
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}/api/v1/document-processing/process-file-path",
                json=request_data
            )
            
            if response.status_code == 202:
                result_data = response.json()
                document_id = result_data.get('data', {}).get('document_id')
                print(f"✅ Document processing started")
                print(f"   Document ID: {document_id}")
                print(f"   Status: {result_data.get('data', {}).get('pipeline_status')}")
                
                # Test status checking
                if document_id:
                    print(f"\n6. Testing Status Checking...")
                    try:
                        status_response = await client.get(
                            f"{base_url}/api/v1/document-processing/status/{document_id}"
                        )
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"✅ Status retrieved for document {document_id}")
                            print(f"   Status: {status_data.get('data', {}).get('status', 'unknown')}")
                        else:
                            print(f"❌ Status check failed: {status_response.status_code}")
                    except Exception as e:
                        print(f"❌ Status check error: {e}")
                
            else:
                print(f"❌ Document processing failed: {response.status_code}")
                if response.content:
                    print(f"   Error: {response.text}")
                    
        except Exception as e:
            print(f"❌ Document processing error: {e}")
        
        # 6. Test file upload processing
        print("\n7. Testing Document Processing via Upload...")
        try:
            files = {"file": ("test_upload.md", test_content, "text/markdown")}
            data = {
                "processing_options": json.dumps({
                    "conversion": {"max_pages": 5}
                })
            }
            
            response = await client.post(
                f"{base_url}/api/v1/document-processing/process",
                files=files,
                data=data
            )
            
            if response.status_code == 202:
                result_data = response.json()
                document_id = result_data.get('data', {}).get('document_id')
                print(f"✅ Upload processing started")
                print(f"   Document ID: {document_id}")
            else:
                print(f"❌ Upload processing failed: {response.status_code}")
                if response.content:
                    print(f"   Error: {response.text}")
                    
        except Exception as e:
            print(f"❌ Upload processing error: {e}")
        
        # Cleanup
        try:
            os.remove(test_file_path)
            print(f"\n🧹 Cleaned up test file: {test_file_path}")
        except:
            pass
        
        print("\n" + "=" * 50)
        print("🎉 Pipeline Testing Complete!")
        print("\nNext Steps:")
        print("1. Start the Redis server if not running")
        print("2. Start the worker processes:")
        print("   python -m app.workers.document_converter_worker")
        print("   python -m app.workers.metadata_extractor_worker") 
        print("   python -m app.workers.typesense_indexer_worker")
        print("   python -m app.workers.qdrant_indexer_worker")
        print("3. Set up your API keys in .env:")
        print("   OPENAI_API_KEY=your_openai_key")
        print("   TYPESENSE_API_KEY=your_typesense_key")
        print("   QDRANT_API_KEY=your_qdrant_key (optional)")


async def main():
    """Main test function."""
    await test_pipeline()


if __name__ == "__main__":
    asyncio.run(main()) 