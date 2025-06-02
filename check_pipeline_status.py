import requests
import json
import time

def check_pipeline_status(document_id):
    """Check the status of a document processing pipeline."""
    
    url = f"http://localhost:8000/api/v1/document-processing/status/{document_id}"
    
    try:
        print(f"Checking pipeline status for document: {document_id}")
        print("=" * 60)
        
        for i in range(10):  # Check 10 times with delay
            print(f"\n📊 Status Check #{i+1}")
            
            response = requests.get(url, timeout=10)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})
                
                print(f"Document ID: {data.get('document_id')}")
                print(f"Status: {data.get('status')}")
                print(f"Overall Progress: {data.get('overall_progress', 0)}%")
                
                steps = data.get("steps", {})
                print("\n🔄 Pipeline Steps:")
                for step_name, step_info in steps.items():
                    status = step_info.get("status", "unknown")
                    progress = step_info.get("progress", 0)
                    print(f"  {step_name}: {status} ({progress}%)")
                
                print(f"Last Updated: {data.get('last_updated')}")
                
                # Check if pipeline is completed
                if data.get("status") == "completed":
                    print("\n🎉 Pipeline completed successfully!")
                    break
                elif data.get("status") == "failed":
                    print("\n❌ Pipeline failed!")
                    break
                    
            else:
                print(f"Error response: {response.text}")
            
            print("\n⏳ Waiting 30 seconds before next check...")
            time.sleep(30)
        
        print("\n📋 Final Status Check Complete")
                
    except Exception as e:
        print(f"Error checking pipeline status: {e}")

if __name__ == "__main__":
    # Use the document ID from the recent test
    document_id = "06df03b1-1b18-4c45-becf-8fa2499ea532"
    check_pipeline_status(document_id) 