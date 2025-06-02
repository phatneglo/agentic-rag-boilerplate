#!/usr/bin/env python3
"""
Verify that the document processing pipeline is working.
Check Redis queues, job statuses, and worker activity.
"""
import asyncio
import os
import time
import redis.asyncio as redis
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def check_redis_connection():
    """Check Redis connection and basic info."""
    try:
        # Create Redis connection
        redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
        )
        
        # Test connection
        await redis_conn.ping()
        logger.info("✅ Redis connection successful")
        
        # Get Redis info
        info = await redis_conn.info()
        logger.info(f"📊 Redis info: {info.get('redis_version', 'unknown')} - {info.get('used_memory_human', 'unknown')} memory")
        
        return redis_conn
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        return None

async def check_queues(redis_conn):
    """Check BullMQ queue status."""
    try:
        logger.info("🔍 Checking BullMQ Queues...")
        
        queue_names = [
            "document_processing:document_converter",
            "document_processing:metadata_extractor", 
            "document_processing:typesense_indexer",
            "document_processing:qdrant_indexer"
        ]
        
        for queue_name in queue_names:
            logger.info(f"\n📋 Queue: {queue_name}")
            
            # Check waiting jobs
            waiting_key = f"bull:{queue_name}:waiting"
            waiting_count = await redis_conn.llen(waiting_key)
            logger.info(f"  ⏳ Waiting jobs: {waiting_count}")
            
            # Check active jobs  
            active_key = f"bull:{queue_name}:active"
            active_count = await redis_conn.llen(active_key)
            logger.info(f"  🔄 Active jobs: {active_count}")
            
            # Check completed jobs
            completed_key = f"bull:{queue_name}:completed"
            completed_count = await redis_conn.llen(completed_key)
            logger.info(f"  ✅ Completed jobs: {completed_count}")
            
            # Check failed jobs
            failed_key = f"bull:{queue_name}:failed"
            failed_count = await redis_conn.llen(failed_key)
            logger.info(f"  ❌ Failed jobs: {failed_count}")
            
            # Get recent job IDs
            if waiting_count > 0:
                waiting_jobs = await redis_conn.lrange(waiting_key, 0, 4)
                logger.info(f"  📝 Recent waiting: {waiting_jobs[:3]}")
                
            if active_count > 0:
                active_jobs = await redis_conn.lrange(active_key, 0, 4)
                logger.info(f"  🏃 Active jobs: {active_jobs[:3]}")
    
    except Exception as e:
        logger.error(f"❌ Queue check failed: {e}")

async def check_specific_job(redis_conn, job_id, queue_name):
    """Check status of a specific job."""
    try:
        logger.info(f"\n🔍 Checking Job {job_id} in {queue_name}")
        
        job_key = f"bull:{queue_name}:{job_id}"
        job_data = await redis_conn.hgetall(job_key)
        
        if job_data:
            logger.info(f"  📊 Job Status:")
            logger.info(f"    ID: {job_data.get('id', 'unknown')}")
            logger.info(f"    Name: {job_data.get('name', 'unknown')}")
            logger.info(f"    Timestamp: {job_data.get('timestamp', 'unknown')}")
            logger.info(f"    ProcessedOn: {job_data.get('processedOn', 'not started')}")
            logger.info(f"    FinishedOn: {job_data.get('finishedOn', 'not finished')}")
            logger.info(f"    FailedOn: {job_data.get('failedOn', 'not failed')}")
            logger.info(f"    Progress: {job_data.get('progress', 'unknown')}")
            
            if job_data.get('failedReason'):
                logger.error(f"    ❌ Failed Reason: {job_data.get('failedReason')}")
                
            return job_data
        else:
            logger.warning(f"  ⚠️ Job {job_id} not found in Redis")
            return None
            
    except Exception as e:
        logger.error(f"❌ Job check failed: {e}")
        return None

async def monitor_pipeline():
    """Monitor the pipeline activity."""
    logger.info("🚀 Document Processing Pipeline Verification")
    logger.info("=" * 60)
    
    # Check Redis connection
    redis_conn = await check_redis_connection()
    if not redis_conn:
        return
    
    try:
        # Check queues multiple times to see activity
        for round_num in range(3):
            logger.info(f"\n🔄 Monitoring Round {round_num + 1}")
            
            await check_queues(redis_conn)
            
            # Check specific recent jobs
            recent_jobs = [
                ("11", "document_processing:document_converter"),
                ("10", "document_processing:document_converter"),
            ]
            
            for job_id, queue_name in recent_jobs:
                await check_specific_job(redis_conn, job_id, queue_name)
            
            if round_num < 2:
                logger.info("\n⏳ Waiting 30 seconds...")
                await asyncio.sleep(30)
    
    finally:
        await redis_conn.close()
        logger.info("🏁 Pipeline verification complete")

if __name__ == "__main__":
    asyncio.run(monitor_pipeline()) 