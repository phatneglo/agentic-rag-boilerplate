#!/usr/bin/env python3
"""
Monitor both active pipeline jobs to see complete 4-step execution.
"""
import requests
import time

def check_pipeline_status(document_id, job_name):
    """Check the status of a specific pipeline."""
    try:
        url = f"http://localhost:8000/api/v1/document-processing/status/{document_id}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            data = result.get("data", {})
            
            print(f"\n📋 {job_name} ({document_id[:8]}...)")
            print(f"Status: {data.get('status')} | Progress: {data.get('overall_progress', 0)}%")
            
            steps = data.get("steps", {})
            for step_name, step_info in steps.items():
                status = step_info.get("status", "unknown")
                progress = step_info.get("progress", 0)
                
                # Color coding
                if status == "completed":
                    icon = "✅"
                elif status == "in_progress":
                    icon = "🔄"
                elif status == "queued":
                    icon = "⏳"
                else:
                    icon = "❓"
                
                print(f"  {icon} {step_name}: {status} ({progress}%)")
            
            return data.get('status')
        else:
            print(f"❌ Error checking {job_name}: {response.status_code}")
            return "error"
    
    except Exception as e:
        print(f"❌ Error checking {job_name}: {e}")
        return "error"

def monitor_active_pipelines():
    """Monitor both active pipelines."""
    print("🔍 Monitoring Active Document Processing Pipelines")
    print("=" * 70)
    
    # Two active pipelines
    pipelines = [
        ("cd9d5e13-9302-4f23-a189-975d4f52eadc", "Job 14 Pipeline"),  # In Step 2
        ("14d56377-c8e6-41fc-871e-7a4b5c3c9c2e", "Job 15 Pipeline"),  # Just started
    ]
    
    completed_pipelines = set()
    
    for round_num in range(20):  # Monitor for up to 20 rounds (10 minutes)
        current_time = time.strftime("%H:%M:%S")
        print(f"\n⏰ {current_time} - Round {round_num + 1}/20")
        
        active_count = 0
        
        for document_id, job_name in pipelines:
            if document_id not in completed_pipelines:
                status = check_pipeline_status(document_id, job_name)
                
                if status == "completed":
                    print(f"🎉 {job_name} COMPLETED!")
                    completed_pipelines.add(document_id)
                elif status in ["in_progress", "queued"]:
                    active_count += 1
        
        # Check if all pipelines are done
        if len(completed_pipelines) == len(pipelines):
            print("\n🎊 ALL PIPELINES COMPLETED! 🎊")
            break
        
        if active_count == 0:
            print("\n😴 No active pipelines detected")
        else:
            print(f"\n🚀 {active_count} pipeline(s) still active")
        
        print("\n" + "-" * 70)
        time.sleep(30)  # Wait 30 seconds between checks
    
    print("\n📋 Final Summary:")
    print(f"✅ Completed: {len(completed_pipelines)}/{len(pipelines)} pipelines")
    
    if len(completed_pipelines) == len(pipelines):
        print("🎉 SUCCESS: Complete 4-step pipeline is working perfectly!")
        print("\nWhat happened:")
        print("1. ✅ Document-to-Markdown conversion using Marker")
        print("2. ✅ Metadata extraction using LlamaIndex")  
        print("3. ✅ Typesense indexing with embeddings")
        print("4. ✅ Qdrant indexing for RAG")
    else:
        print("⚠️ Some pipelines may still be in progress")

if __name__ == "__main__":
    monitor_active_pipelines() 