#!/usr/bin/env python3
"""
Real-time pipeline monitor.
Watch all 4 queues for job activity and pipeline progression.
"""
import asyncio
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
import time

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def monitor_realtime():
    """Monitor pipeline activity in real-time."""
    try:
        # Create Redis connection
        redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
        )
        
        await redis_conn.ping()
        logger.info("🔍 Real-time Pipeline Monitor Started")
        logger.info("=" * 60)
        
        queue_names = [
            "document_processing:document_converter",
            "document_processing:metadata_extractor", 
            "document_processing:typesense_indexer",
            "document_processing:qdrant_indexer"
        ]
        
        # Monitor for 5 minutes
        start_time = time.time()
        monitor_duration = 300  # 5 minutes
        
        while time.time() - start_time < monitor_duration:
            current_time = time.strftime("%H:%M:%S")
            logger.info(f"\n⏰ {current_time} - Queue Status Check")
            
            total_activity = 0
            
            for i, queue_name in enumerate(queue_names, 1):
                step_name = {
                    1: "Step 1 (Document Conversion)",
                    2: "Step 2 (Metadata Extraction)",
                    3: "Step 3 (Typesense Indexing)",
                    4: "Step 4 (Qdrant Indexing)"
                }[i]
                
                try:
                    # Check queue activity
                    waiting_key = f"bull:{queue_name}:waiting"
                    active_key = f"bull:{queue_name}:active"
                    completed_key = f"bull:{queue_name}:completed"
                    failed_key = f"bull:{queue_name}:failed"
                    
                    waiting = await redis_conn.llen(waiting_key)
                    active = await redis_conn.llen(active_key)
                    
                    # Get counts more safely
                    try:
                        completed = await redis_conn.zcard(completed_key)
                    except:
                        completed = 0
                    
                    try:
                        failed = await redis_conn.zcard(failed_key)
                    except:
                        failed = 0
                    
                    activity = waiting + active
                    total_activity += activity
                    
                    # Color coding
                    if active > 0:
                        status = f"🔄 ACTIVE ({active})"
                    elif waiting > 0:
                        status = f"⏳ WAITING ({waiting})"
                    elif completed > 0:
                        status = f"✅ COMPLETED ({completed})"
                    else:
                        status = "💤 IDLE"
                    
                    logger.info(f"  {step_name}: {status}")
                    
                    # Show recent active jobs
                    if active > 0:
                        active_jobs = await redis_conn.lrange(active_key, 0, 2)
                        if active_jobs:
                            logger.info(f"    Active jobs: {active_jobs}")
                    
                except Exception as e:
                    logger.warning(f"  {step_name}: ⚠️ Error checking - {e}")
            
            # Summary
            if total_activity > 0:
                logger.info(f"🚀 Pipeline Activity Detected: {total_activity} jobs")
            else:
                logger.info("😴 No current pipeline activity")
            
            # Check specific recent jobs
            recent_jobs = ["13", "12", "11"]
            for job_id in recent_jobs:
                await check_job_quick(redis_conn, job_id, "document_processing:document_converter")
            
            await asyncio.sleep(10)  # Check every 10 seconds
            
        logger.info("🏁 Real-time monitoring completed")
        
    except Exception as e:
        logger.error(f"❌ Monitor failed: {e}")
    finally:
        if 'redis_conn' in locals():
            await redis_conn.aclose()

async def check_job_quick(redis_conn, job_id, queue_name):
    """Quick job status check."""
    try:
        job_key = f"bull:{queue_name}:{job_id}"
        job_data = await redis_conn.hgetall(job_key)
        
        if job_data:
            name = job_data.get('name', 'unknown')
            finished = job_data.get('finishedOn', None)
            failed = job_data.get('failedOn', None)
            progress = job_data.get('progress', 'unknown')
            
            if finished:
                logger.info(f"    Job {job_id}: ✅ {name} - COMPLETED (Progress: {progress})")
            elif failed:
                logger.info(f"    Job {job_id}: ❌ {name} - FAILED")
            else:
                logger.info(f"    Job {job_id}: 🔄 {name} - IN PROGRESS (Progress: {progress})")
                
    except Exception as e:
        # Don't log errors for missing jobs
        pass

if __name__ == "__main__":
    asyncio.run(monitor_realtime()) 