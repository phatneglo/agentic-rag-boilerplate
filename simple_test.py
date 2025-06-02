#!/usr/bin/env python3
"""
Simple test for document processing endpoint.
"""

import requests

def test_upload():
    """Test uploading a file to the document processing endpoint."""
    
    print("🧪 Testing Document Processing Upload")
    
    try:
        with open("sample.txt", 'rb') as f:
            files = {'file': ('sample.txt', f, 'text/plain')}
            
            response = requests.post(
                "http://localhost:8000/api/v1/document-processing/process",
                files=files,
                timeout=30
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 202:
            result = response.json()
            print(f"✅ Success! Document ID: {result['data']['document_id']}")
            return result['data']['document_id']
        else:
            print(f"❌ Failed with status {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_upload() 