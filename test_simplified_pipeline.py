#!/usr/bin/env python3
"""
Test the simplified document processing pipeline.
"""

import requests
import time
import json

def test_pipeline():
    """Test the simplified document processing pipeline."""
    
    print("🧪 Testing Simplified Document Processing Pipeline")
    print("=" * 60)
    
    # Test file (you can change this to any PDF/text file)
    test_file_path = "sample.txt"  # Make sure this file exists
    
    try:
        # Upload and process document
        print(f"📤 Uploading file: {test_file_path}")
        
        with open(test_file_path, 'rb') as f:
            files = {'file': (test_file_path, f, 'text/plain')}
            
            response = requests.post(
                "http://localhost:8000/api/v1/document-processing/process",
                files=files,
                timeout=30
            )
        
        if response.status_code == 202:
            result = response.json()
            document_id = result['data']['document_id']
            print(f"✅ Document queued successfully!")
            print(f"📋 Document ID: {document_id}")
            print(f"🆔 Job ID: {result['data']['job_id']}")
            print(f"📁 S3 Path: {result['data']['s3_file_path']}")
            
            # Monitor progress
            print("\n🔍 Monitoring Progress:")
            print("-" * 40)
            
            for i in range(30):  # Monitor for up to 15 minutes (30 * 30 seconds)
                try:
                    status_response = requests.get(
                        f"http://localhost:8000/api/v1/document-processing/status/{document_id}",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()['data']
                        
                        print(f"\n⏰ Check {i+1}/30 - Overall Progress: {status_data['overall_progress']}%")
                        print(f"📊 Status: {status_data['status']}")
                        
                        steps = status_data['steps']
                        for step_name, step_info in steps.items():
                            status_icon = "✅" if step_info['status'] == 'completed' else "🔄" if step_info['status'] == 'in_progress' else "⏳"
                            print(f"  {status_icon} {step_name}: {step_info['status']} ({step_info['progress']}%)")
                        
                        # Check if completed
                        if status_data['status'] == 'completed':
                            print("\n🎉 PIPELINE COMPLETED SUCCESSFULLY!")
                            break
                        elif status_data['status'] == 'failed':
                            print("\n❌ PIPELINE FAILED!")
                            break
                    else:
                        print(f"❌ Error checking status: {status_response.status_code}")
                
                except Exception as e:
                    print(f"❌ Error monitoring: {e}")
                
                # Wait before next check
                time.sleep(30)
            
            print("\n📋 Final Summary:")
            if status_data['status'] == 'completed':
                print("✅ SUCCESS: Complete 4-step pipeline working!")
                print("\nSteps completed:")
                print("1. ✅ Document-to-Markdown conversion using Marker")
                print("2. ✅ Metadata extraction using LlamaIndex")
                print("3. ✅ Typesense indexing with embeddings and content")
                print("4. ✅ Qdrant indexing for RAG")
            else:
                print("⚠️ Pipeline did not complete within monitoring period")
                
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"Response: {response.text}")
    
    except FileNotFoundError:
        print(f"❌ Test file not found: {test_file_path}")
        print("Please create a sample PDF file or update the file path")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def check_health():
    """Check if the API is healthy."""
    try:
        response = requests.get("http://localhost:8000/api/v1/document-processing/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✅ API Health Check: Healthy")
            print(f"🔗 Redis: {health_data['services']['redis']}")
            print(f"🗄️ S3: {health_data['services']['s3']}")
            return True
        else:
            print(f"❌ API Health Check: Unhealthy ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ API Health Check: Failed - {e}")
        return False

if __name__ == "__main__":
    print("🏥 Checking API Health First...")
    if check_health():
        print("\n" + "=" * 60)
        test_pipeline()
    else:
        print("⚠️ API is not healthy. Please start the API server and worker first.")
        print("\nTo start:")
        print("1. Start API: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("2. Start Worker: python document_processing_worker.py") 