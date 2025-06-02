#!/usr/bin/env python3
"""
Check API server and pipeline logs for Job 14 processing.
"""
import requests
import time

def check_job_14_status():
    """Check if Job 14 is being processed correctly."""
    
    print("🔍 Checking Job 14 Status and Pipeline Activity")
    print("=" * 60)
    
    # Check the latest document status
    document_id = "cd9d5e13-9302-4f23-a189-975d4f52eadc"
    
    try:
        url = f"http://localhost:8000/api/v1/document-processing/status/{document_id}"
        response = requests.get(url, timeout=10)
        
        print(f"📋 Document Status API Response:")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            print(f"Document ID: {data.get('document_id')}")
            print(f"Pipeline Status: {data.get('status')}")
            print(f"Overall Progress: {data.get('overall_progress', 0)}%")
            
            steps = data.get("steps", {})
            print("\n🔄 Current Pipeline Steps:")
            for step_name, step_info in steps.items():
                status = step_info.get("status", "unknown")
                progress = step_info.get("progress", 0)
                print(f"  {step_name}: {status} ({progress}%)")
        else:
            print(f"❌ Error: {response.text}")
    
    except Exception as e:
        print(f"❌ Error checking status: {e}")
    
    print("\n" + "=" * 60)
    print("💡 Expected Behavior:")
    print("- Step 1 should complete (convert_document)")
    print("- Pipeline monitoring should automatically trigger Step 2")
    print("- Step 2 should queue metadata extraction")
    print("- Steps 3 & 4 should queue after Step 2 completes")
    
    print("\n🚨 If Steps 2-4 are still 'queued' with 0% progress,")
    print("   it means the pipeline monitoring is not working!")

def check_api_health():
    """Check if API server is responding properly."""
    try:
        url = "http://localhost:8000/health"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            print("✅ API Server: Healthy")
            return True
        else:
            print(f"❌ API Server: Error {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API Server: Connection failed - {e}")
        return False

if __name__ == "__main__":
    print("🏥 Health Check:")
    if check_api_health():
        print("\n📊 Pipeline Status Check:")
        check_job_14_status()
    else:
        print("⚠️ API server is not responding. Please start it first.") 