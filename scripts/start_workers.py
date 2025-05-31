#!/usr/bin/env python3
"""
Script to start all document processing workers.
"""
import asyncio
import signal
import sys
import os
from typing import List

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workers.document_converter_worker import DocumentConverterWorker
from app.workers.typesense_indexer_worker import TypesenseIndexerWorker
from app.workers.qdrant_indexer_worker import QdrantIndexerWorker
from app.workers.document_sync_worker import DocumentSyncWorker
from app.core.logging_config import configure_logging, get_logger


# Configure logging
configure_logging()
logger = get_logger(__name__)


class WorkerManager:
    """Manager for all document processing workers."""
    
    def __init__(self):
        self.workers = []
        self.tasks = []
        self.shutdown_event = asyncio.Event()
    
    async def start_all_workers(self):
        """Start all workers."""
        logger.info("Starting all document processing workers")
        
        # Initialize workers
        self.workers = [
            DocumentConverterWorker(),
            TypesenseIndexerWorker(),
            QdrantIndexerWorker(),
            DocumentSyncWorker(),
        ]
        
        # Start each worker in a separate task
        for worker in self.workers:
            task = asyncio.create_task(worker.start())
            self.tasks.append(task)
            logger.info(f"Started {worker.__class__.__name__}")
        
        logger.info("All workers started successfully")
        
        # Wait for shutdown signal
        await self.shutdown_event.wait()
        
        # Cleanup
        await self.stop_all_workers()
    
    async def stop_all_workers(self):
        """Stop all workers."""
        logger.info("Stopping all workers")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Cleanup workers
        for worker in self.workers:
            try:
                await worker.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up {worker.__class__.__name__}", error=str(e))
        
        logger.info("All workers stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown")
        self.shutdown_event.set()


async def start_specific_worker(worker_name: str):
    """Start a specific worker by name."""
    worker_classes = {
        "converter": DocumentConverterWorker,
        "typesense": TypesenseIndexerWorker,
        "qdrant": QdrantIndexerWorker,
        "sync": DocumentSyncWorker,
    }
    
    if worker_name not in worker_classes:
        logger.error(f"Unknown worker: {worker_name}")
        logger.info(f"Available workers: {', '.join(worker_classes.keys())}")
        return
    
    worker_class = worker_classes[worker_name]
    worker = worker_class()
    
    logger.info(f"Starting {worker_class.__name__}")
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info(f"{worker_class.__name__} stopped by user")
    except Exception as e:
        logger.error(f"{worker_class.__name__} error", error=str(e))
    finally:
        await worker.cleanup()


async def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start document processing workers")
    parser.add_argument(
        "--worker",
        choices=["converter", "typesense", "qdrant", "sync", "all"],
        default="all",
        help="Which worker(s) to start"
    )
    
    args = parser.parse_args()
    
    if args.worker == "all":
        # Start all workers
        manager = WorkerManager()
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, manager.signal_handler)
        signal.signal(signal.SIGTERM, manager.signal_handler)
        
        try:
            await manager.start_all_workers()
        except KeyboardInterrupt:
            logger.info("Shutdown initiated by user")
        except Exception as e:
            logger.error("Worker manager error", error=str(e))
    else:
        # Start specific worker
        await start_specific_worker(args.worker)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error("Application error", error=str(e))
        sys.exit(1) 