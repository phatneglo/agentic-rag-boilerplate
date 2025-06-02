#!/usr/bin/env python3
"""Test PDF upload to verify Marker tuple fix."""

import requests
import tempfile
import os

def test_pdf_upload():
    print("🧪 Testing PDF Document Processing Upload")
    
    # Create a simple PDF content (actually just a text file with .pdf extension for testing)
    test_pdf_content = b"""# Test PDF Document

This is a test PDF document to verify that the Marker processing works correctly.

## Section 1
Some content here to test metadata extraction.

## Section 2  
More content to ensure we have enough text for processing.

Keywords: test, pdf, document, processing, marker
"""
    
    # Create temporary PDF file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(test_pdf_content)
        temp_file_path = temp_file.name
    
    try:
        # Upload the file
        with open(temp_file_path, 'rb') as f:
            files = {'file': ('test_document.pdf', f, 'application/pdf')}
            response = requests.post(
                "http://localhost:8000/api/v1/document-processing/process",
                files=files,
                timeout=30
            )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 202:
            data = response.json()['data']
            document_id = data['document_id']
            print(f"✅ Success! Document ID: {document_id}")
            return document_id
        else:
            print(f"❌ Error: {response.status_code}")
            return None
            
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    test_pdf_upload() 