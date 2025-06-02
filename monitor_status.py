#!/usr/bin/env python3
"""
Monitor job status continuously.
"""

import requests
import time

def monitor_status(document_id, max_checks=20):
    """Monitor the status of a document processing job."""
    
    print(f"🔍 Monitoring Document: {document_id}")
    print("=" * 60)
    
    for i in range(max_checks):
        try:
            response = requests.get(
                f"http://localhost:8000/api/v1/document-processing/status/{document_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()['data']
                
                print(f"\n⏰ Check {i+1}/{max_checks} - Overall Progress: {data['overall_progress']}%")
                print(f"📊 Status: {data['status']}")
                
                steps = data['steps']
                for step_name, step_info in steps.items():
                    status_icon = "✅" if step_info['status'] == 'completed' else "🔄" if step_info['status'] == 'in_progress' else "⏳"
                    print(f"  {status_icon} {step_name}: {step_info['status']} ({step_info['progress']}%)")
                
                # Check if completed or failed
                if data['status'] in ['completed', 'failed']:
                    print(f"\n🎯 Final status: {data['status']}")
                    break
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Wait before next check
        if i < max_checks - 1:
            time.sleep(10)  # Check every 10 seconds
    
    print("\n📋 Monitoring completed")

if __name__ == "__main__":
    # Use the document ID from the recent test
    document_id = "b3805fc5-a5a7-4f72-811a-14839c258fa5"
    monitor_status(document_id) 