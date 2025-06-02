#!/usr/bin/env python3
"""
Check job status.
"""

import requests
import json

def check_status(document_id):
    """Check the status of a document processing job."""
    
    try:
        response = requests.get(
            f"http://localhost:8000/api/v1/document-processing/status/{document_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()['data']
            print(f"📋 Document ID: {document_id}")
            print(f"📊 Status: {data['status']}")
            print(f"📈 Overall Progress: {data['overall_progress']}%")
            print(f"📁 File: {data['file_name']}")
            print(f"🗂️ S3 Path: {data['s3_file_path']}")
            
            print("\n🔍 Step Details:")
            steps = data['steps']
            for step_name, step_info in steps.items():
                status_icon = "✅" if step_info['status'] == 'completed' else "🔄" if step_info['status'] == 'in_progress' else "⏳"
                print(f"  {status_icon} {step_name}: {step_info['status']} ({step_info['progress']}%)")
            
            return data
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    # Use the document ID from the previous test
    document_id = "1958ff20-c414-40d9-a528-db3848d02d48"
    check_status(document_id) 