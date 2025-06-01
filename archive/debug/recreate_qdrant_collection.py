#!/usr/bin/env python3
"""
Recreate Qdrant collection with LlamaIndex-compatible configuration.
"""
import asyncio
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

from qdrant_client import QdrantClient, models

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def recreate_qdrant_collection():
    """Recreate Qdrant collection with proper LlamaIndex configuration."""
    
    try:
        logger.info("=== RECREATING QDRANT COLLECTION ===")
        
        # Initialize Qdrant client
        qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=False,
            https=False,
        )
        
        collection_name = "documents_rag"
        
        # 1. Check if collection exists
        try:
            collection_info = qdrant_client.get_collection(collection_name)
            logger.info(f"📄 Existing collection found: {collection_name}")
            logger.info(f"📊 Current points: {collection_info.points_count}")
            logger.info(f"🔧 Current config: {collection_info.config}")
        except Exception:
            logger.info(f"📄 Collection '{collection_name}' does not exist")
        
        # 2. Delete existing collection if it exists
        try:
            logger.info(f"🗑️ Deleting existing collection...")
            qdrant_client.delete_collection(collection_name)
            logger.info(f"✅ Deleted collection '{collection_name}'")
        except Exception as e:
            logger.info(f"ℹ️ Collection deletion skipped: {e}")
        
        # 3. Create new collection with LlamaIndex-compatible configuration
        logger.info(f"🔧 Creating new LlamaIndex-compatible collection...")
        
        # Based on LlamaIndex documentation: vector must be named "text-dense"
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small dimensions
                    distance=models.Distance.COSINE,
                )
            },
            optimizers_config=models.OptimizersConfigDiff(
                default_segment_number=2,
            ),
            hnsw_config=models.HnswConfigDiff(
                payload_m=16,
                m=0,
            ),
        )
        
        logger.info(f"✅ Created LlamaIndex-compatible collection '{collection_name}'")
        
        # 4. Verify the new collection
        collection_info = qdrant_client.get_collection(collection_name)
        logger.info(f"📊 New collection status:")
        logger.info(f"  Points count: {collection_info.points_count}")
        logger.info(f"  Vector config: {collection_info.config.params.vectors}")
        logger.info(f"  Distance metric: {collection_info.config.params.vectors['text-dense'].distance}")
        logger.info(f"  Vector size: {collection_info.config.params.vectors['text-dense'].size}")
        
        logger.info("=== COLLECTION RECREATION COMPLETE ===")
        logger.info("🎉 Qdrant collection is now properly configured for LlamaIndex!")
        
    except Exception as e:
        logger.error(f"❌ Collection recreation failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(recreate_qdrant_collection()) 