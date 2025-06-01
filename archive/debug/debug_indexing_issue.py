#!/usr/bin/env python3
"""
Debug script to test direct indexing to Qdrant and identify the issue.
"""
import asyncio
import os
import sys
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def debug_qdrant_indexing():
    """Debug Qdrant indexing directly."""
    
    try:
        # Initialize Qdrant client
        qdrant_url = f"http://localhost:6333"
        client = QdrantClient(url=qdrant_url, prefer_grpc=False)
        
        logger.info("=== QDRANT DIRECT INDEXING DEBUG ===")
        
        # 1. Check collection status
        logger.info("📊 Checking collection status...")
        collection_info = client.get_collection("documents_rag")
        logger.info(f"Points before indexing: {collection_info.points_count}")
        
        # 2. Create a simple test document
        test_document_id = f"debug_test_{int(datetime.now().timestamp())}"
        test_chunk_id = f"{test_document_id}_chunk_0"
        
        logger.info(f"🧪 Creating test document: {test_document_id}")
        
        # Create a simple embedding (1536 dimensions filled with 0.1)
        test_embedding = [0.1] * 1536
        
        # Create test point
        test_point = PointStruct(
            id=test_chunk_id,
            vector=test_embedding,
            payload={
                "document_id": test_document_id,
                "chunk_id": test_chunk_id,
                "title": "Debug Test Document",
                "content": "This is a debug test document to verify Qdrant indexing.",
                "created_at": datetime.utcnow().isoformat()
            }
        )
        
        # 3. Index the test point
        logger.info("📝 Indexing test point...")
        result = client.upsert(
            collection_name="documents_rag",
            points=[test_point],
            wait=True
        )
        
        logger.info(f"✅ Upsert result: {result}")
        
        # 4. Wait a moment for indexing
        await asyncio.sleep(2)
        
        # 5. Check collection status again
        logger.info("📊 Checking collection status after indexing...")
        collection_info = client.get_collection("documents_rag")
        logger.info(f"Points after indexing: {collection_info.points_count}")
        
        # 6. Try to retrieve the point directly
        logger.info("🔍 Searching for the test document...")
        points = client.scroll(
            collection_name="documents_rag",
            scroll_filter={
                "must": [
                    {
                        "key": "document_id",
                        "match": {"value": test_document_id}
                    }
                ]
            },
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if points[0]:
            logger.info(f"✅ Found {len(points[0])} points for test document")
            for point in points[0]:
                logger.info(f"  📄 Point ID: {point.id}")
                logger.info(f"      Document ID: {point.payload.get('document_id')}")
                logger.info(f"      Title: {point.payload.get('title')}")
        else:
            logger.warning("⚠️ Test document not found!")
        
        # 7. Test search
        logger.info("🔍 Testing vector search...")
        search_results = client.search(
            collection_name="documents_rag",
            query_vector=test_embedding,
            limit=5,
            with_payload=True
        )
        
        logger.info(f"🔍 Search returned {len(search_results)} results")
        for i, result in enumerate(search_results, 1):
            logger.info(f"  {i}. Score: {result.score}")
            logger.info(f"     Document ID: {result.payload.get('document_id')}")
            logger.info(f"     Title: {result.payload.get('title')}")
        
        # 8. Check if there are any points at all
        logger.info("📊 Checking all points in collection...")
        all_points = client.scroll(
            collection_name="documents_rag",
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if all_points[0]:
            logger.info(f"📄 Total points in collection: {len(all_points[0])}")
            for i, point in enumerate(all_points[0], 1):
                logger.info(f"  {i}. Point ID: {point.id}")
                logger.info(f"     Document ID: {point.payload.get('document_id', 'Unknown')}")
                logger.info(f"     Created: {point.payload.get('created_at', 'Unknown')}")
        else:
            logger.warning("⚠️ No points found in collection!")
        
        # 9. Test with the previous document ID
        previous_doc_id = "ssrdms_frontend_20250601_092712"
        logger.info(f"🔍 Searching for previous document: {previous_doc_id}")
        
        prev_points = client.scroll(
            collection_name="documents_rag",
            scroll_filter={
                "must": [
                    {
                        "key": "document_id",
                        "match": {"value": previous_doc_id}
                    }
                ]
            },
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if prev_points[0]:
            logger.info(f"✅ Found {len(prev_points[0])} points for previous document")
        else:
            logger.warning(f"⚠️ Previous document {previous_doc_id} not found!")
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_qdrant_indexing()) 