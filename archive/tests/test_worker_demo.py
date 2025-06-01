#!/usr/bin/env python3
"""
Test Worker Demo Script.
Demonstrates uploading files and processing them with the test worker.
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


async def demo_test_worker():
    """Demo the test worker functionality."""
    
    base_url = f"http://{settings.api_host}:{settings.api_port}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        print("🧪 Test Worker Demo")
        print("=" * 50)
        
        # 1. Test health check
        print("\n1. Testing Test API Health...")
        try:
            response = await client.get(f"{base_url}/api/v1/test/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Test API Health: {health_data.get('status', 'unknown')}")
                print(f"   Redis: {health_data.get('redis', 'unknown')}")
            else:
                print(f"❌ Test health check failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Test health error: {e}")
        
        # 2. Create test files
        print("\n2. Creating Test Files...")
        test_files = {}
        
        # Create a text file
        text_content = """
# Test Document

This is a test document for the test worker.

## Content

The test worker will:
1. Download this file from object storage
2. Extract text content
3. Analyze the text
4. Clean up temporary files

## Sample Text

Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco.

## Conclusion

This demonstrates the test worker functionality.
        """.strip()
        
        text_file_path = "test_sample.txt"
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        test_files["text"] = text_file_path
        
        # Create a JSON file
        json_content = {
            "test": "data",
            "worker": "demo",
            "features": ["upload", "download", "extract", "analyze", "cleanup"],
            "numbers": [1, 2, 3, 4, 5],
            "description": "This is test JSON data for the worker demo"
        }
        
        json_file_path = "test_sample.json"
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f, indent=2)
        test_files["json"] = json_file_path
        
        # Create a markdown file
        md_content = """
# Test Markdown Document

This is a **markdown** file for testing.

## Features

- *Italic text*
- **Bold text**
- `Code snippets`

### Code Block

```python
def test_function():
    return "Hello, Test Worker!"
```

### List

1. First item
2. Second item
3. Third item

> This is a blockquote for testing purposes.
        """.strip()
        
        md_file_path = "test_sample.md"
        with open(md_file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        test_files["markdown"] = md_file_path
        
        print(f"✅ Created {len(test_files)} test files:")
        for file_type, file_path in test_files.items():
            print(f"   - {file_type}: {file_path}")
        
        # 3. Upload files and trigger test worker
        print("\n3. Uploading Files and Triggering Test Worker...")
        try:
            files = []
            for file_type, file_path in test_files.items():
                with open(file_path, 'rb') as f:
                    files.append(("files", (file_path, f.read(), "text/plain")))
            
            response = await client.post(
                f"{base_url}/api/v1/test/worker",
                files=files
            )
            
            if response.status_code == 201:
                result_data = response.json()
                print(f"✅ Test worker jobs created successfully")
                print(f"   Total files: {result_data.get('total_files', 0)}")
                print(f"   Successful uploads: {result_data.get('successful_uploads', 0)}")
                print(f"   Successful jobs: {result_data.get('successful_jobs', 0)}")
                
                # Show job details
                jobs = result_data.get('jobs', [])
                if jobs:
                    print("\n   Job Details:")
                    for job in jobs:
                        print(f"     - Job ID: {job.get('job_id', 'unknown')}")
                        print(f"       File: {job.get('original_filename', 'unknown')}")
                        print(f"       Status: {job.get('status', 'unknown')}")
                        print(f"       Path: {job.get('file_path', 'unknown')}")
                        print()
                
            else:
                print(f"❌ Test worker failed: {response.status_code}")
                if response.content:
                    print(f"   Error: {response.text}")
                    
        except Exception as e:
            print(f"❌ Test worker error: {e}")
        
        # 4. Check worker queue status
        print("\n4. Checking Worker Queue Status...")
        try:
            response = await client.get(f"{base_url}/api/v1/test/worker/status")
            if response.status_code == 200:
                status_data = response.json()
                print(f"✅ Queue Status Retrieved")
                print(f"   Queue: {status_data.get('queue_name', 'unknown')}")
                print(f"   Length: {status_data.get('queue_length', 0)}")
                
                recent_jobs = status_data.get('recent_jobs', [])
                if recent_jobs:
                    print(f"   Recent jobs ({len(recent_jobs)}):")
                    for job in recent_jobs:
                        print(f"     - {job}")
                else:
                    print("   No recent jobs in queue")
                    
            else:
                print(f"❌ Queue status check failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Queue status error: {e}")
        
        # Cleanup test files
        print("\n5. Cleaning Up Test Files...")
        try:
            for file_type, file_path in test_files.items():
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"   ✅ Removed {file_path}")
        except Exception as e:
            print(f"   ⚠️ Cleanup error: {e}")
        
        print("\n" + "=" * 50)
        print("🎉 Test Worker Demo Complete!")
        print("\nTo see the worker in action:")
        print("1. Make sure Redis is running")
        print("2. Start the test worker:")
        print("   python -m app.workers.test_worker")
        print("3. Watch the worker logs for processing results")
        print("\nThe worker will:")
        print("- Download files from object storage")
        print("- Extract text content")
        print("- Analyze text statistics")
        print("- Clean up temporary files")


async def main():
    """Main demo function."""
    await demo_test_worker()


if __name__ == "__main__":
    asyncio.run(main()) 