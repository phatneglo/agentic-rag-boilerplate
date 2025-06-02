import requests
import json

def test_document_processing():
    """Test the document processing API endpoint."""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/document-processing/process"
    
    # File to upload
    file_path = "uploads/E-Notary-System-vs-Rules-on-Electronic-Notarization-Technical-Implementation-Guide.md.pdf"
    
    # Options
    options = {
        "extract_metadata": True,
        "save_images": False
    }
    
    try:
        # Prepare the request
        with open(file_path, 'rb') as f:
            files = {
                'file': ('test.pdf', f, 'application/pdf')
            }
            data = {
                'options': json.dumps(options)
            }
            
            # Make the request
            print("Submitting document for processing...")
            response = requests.post(url, files=files, data=data, timeout=30)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"Job ID: {result.get('job_id')}")
                print(f"Document ID: {result.get('document_id')}")
                print("Document submitted successfully!")
            else:
                print(f"Error: {response.text}")
                
    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_document_processing() 