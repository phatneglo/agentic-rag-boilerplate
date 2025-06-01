#!/usr/bin/env python3
"""
Recreate Qdrant collection with proper hybrid search configuration.
Following the LlamaIndex documentation for Qdrant hybrid search.
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

async def recreate_hybrid_qdrant_collection():
    """Recreate Qdrant collection with proper hybrid search configuration."""
    
    try:
        logger.info("=== RECREATING QDRANT COLLECTION FOR HYBRID SEARCH ===")
        
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
        except Exception:
            logger.info(f"📄 Collection '{collection_name}' does not exist")
        
        # 2. Delete existing collection if it exists
        try:
            logger.info(f"🗑️ Deleting existing collection...")
            qdrant_client.delete_collection(collection_name)
            logger.info(f"✅ Deleted collection '{collection_name}'")
        except Exception as e:
            logger.info(f"ℹ️ Collection deletion skipped: {e}")
        
        # 3. Create new collection with HYBRID configuration
        logger.info(f"🔧 Creating new HYBRID collection...")
        
        # Based on LlamaIndex documentation: needs both text-dense and text-sparse
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small dimensions
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams()
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
        
        logger.info(f"✅ Created HYBRID collection '{collection_name}'")
        
        # 4. Verify the new collection
        collection_info = qdrant_client.get_collection(collection_name)
        logger.info(f"📊 New hybrid collection status:")
        logger.info(f"  Points count: {collection_info.points_count}")
        logger.info(f"  Dense vector config: {collection_info.config.params.vectors}")
        logger.info(f"  Sparse vector config: {collection_info.config.params.sparse_vectors}")
        logger.info(f"  Distance metric: {collection_info.config.params.vectors['text-dense'].distance}")
        logger.info(f"  Vector size: {collection_info.config.params.vectors['text-dense'].size}")
        
        logger.info("=== HYBRID COLLECTION RECREATION COMPLETE ===")
        logger.info("🎉 Qdrant collection is now properly configured for HYBRID search!")
        logger.info("📋 Features enabled:")
        logger.info("  ✅ Dense vectors (text-dense) - OpenAI embeddings")
        logger.info("  ✅ Sparse vectors (text-sparse) - BM25/SPLADE")
        logger.info("  ✅ Hybrid search capabilities")
        
    except Exception as e:
        logger.error(f"❌ Hybrid collection recreation failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(recreate_hybrid_qdrant_collection()) 