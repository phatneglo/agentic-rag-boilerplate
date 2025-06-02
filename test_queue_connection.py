#!/usr/bin/env python3
"""
Test BullMQ queue connection and job processing.
"""

import asyncio
import redis
from bullmq import Queue, Worker, Job
from app.core.config import settings

async def test_simple_job_processing():
    """Test if BullMQ can process a simple job."""
    print("🧪 Testing BullMQ Job Processing")
    print("=" * 50)
    
    # Create Redis connection string
    if settings.redis_password:
        redis_connection = f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    else:
        redis_connection = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    
    print(f"📡 Redis Connection: {redis_connection}")
    
    # Test basic Redis connection first
    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True
        )
        redis_client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return
    
    # Test BullMQ Queue
    try:
        queue = Queue("test_queue", {"connection": redis_connection})
        print("✅ BullMQ queue created")
    except Exception as e:
        print(f"❌ BullMQ queue creation failed: {e}")
        return
    
    # Add a test job
    try:
        job = await queue.add("test_job", {"message": "Hello World!"})
        print(f"✅ Test job added: {job.id}")
    except Exception as e:
        print(f"❌ Failed to add test job: {e}")
        return
    
    # Create a simple worker
    async def process_test_job(job: Job, job_token: str):
        print(f"🔄 Processing job {job.id}: {job.data}")
        await asyncio.sleep(1)  # Simulate work
        print(f"✅ Job {job.id} completed!")
        return {"result": "success"}
    
    try:
        worker = Worker("test_queue", process_test_job, {"connection": redis_connection})
        print("✅ Test worker created and started")
        
        # Wait a bit for job processing
        await asyncio.sleep(5)
        
        print("🏁 Test completed")
        
    except Exception as e:
        print(f"❌ Worker creation failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_job_processing()) 