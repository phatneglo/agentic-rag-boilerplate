#!/usr/bin/env python3
"""
Start all document processing pipeline workers.
This script starts all 4 workers needed for the complete pipeline:
1. Document Converter Worker
2. Metadata Extractor Worker  
3. Typesense Indexer Worker
4. Qdrant Indexer Worker
"""
import asyncio
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from app.workers.document_converter_worker import DocumentConverterWorker
from app.workers.metadata_extractor_worker import MetadataExtractorWorker
from app.workers.typesense_indexer_worker import TypesenseIndexerWorker
from app.workers.qdrant_indexer_worker import QdrantIndexerWorker
from app.core.logging_config import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Global workers list
workers = []
shutdown_event = asyncio.Event()

async def start_worker(worker_class, worker_name):
    """Start a single worker."""
    try:
        logger.info(f"Starting {worker_name}...")
        worker = worker_class()
        await worker.setup()
        workers.append(worker)
        logger.info(f"✅ {worker_name} started successfully")
        
        # Keep the worker running
        while not shutdown_event.is_set():
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Failed to start {worker_name}: {e}")
        raise

async def start_all_workers():
    """Start all pipeline workers."""
    logger.info("🚀 Starting Document Processing Pipeline Workers")
    logger.info("=" * 60)
    
    try:
        # Start all workers concurrently
        tasks = [
            start_worker(DocumentConverterWorker, "Document Converter Worker"),
            start_worker(MetadataExtractorWorker, "Metadata Extractor Worker"),
            start_worker(TypesenseIndexerWorker, "Typesense Indexer Worker"),
            start_worker(QdrantIndexerWorker, "Qdrant Indexer Worker"),
        ]
        
        logger.info("⏳ Starting all workers...")
        await asyncio.gather(*tasks)
        
    except KeyboardInterrupt:
        logger.info("🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Worker startup failed: {e}")
    finally:
        await shutdown_workers()

async def shutdown_workers():
    """Gracefully shutdown all workers."""
    logger.info("🔄 Shutting down workers...")
    shutdown_event.set()
    
    for worker in workers:
        try:
            if hasattr(worker, 'stop'):
                await worker.stop()
            logger.info(f"✅ Worker stopped: {type(worker).__name__}")
        except Exception as e:
            logger.error(f"❌ Error stopping worker {type(worker).__name__}: {e}")
    
    logger.info("🏁 All workers shut down")

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"📡 Received signal {signum}")
    asyncio.create_task(shutdown_workers())

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(start_all_workers())
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1) 