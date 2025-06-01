#!/usr/bin/env python3
"""
Check Qdrant status and collections.
"""
import asyncio
import sys
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import json

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def check_qdrant_status():
    """Check the current status of Qdrant."""
    
    try:
        # Initialize Qdrant client with proper URL
        qdrant_url = f"{settings.qdrant_protocol}://{settings.qdrant_host}:{settings.qdrant_port}"
        
        logger.info(f"Connecting to Qdrant at: {qdrant_url}")
        
        client = QdrantClient(
            url=qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            timeout=60,
            prefer_grpc=False  # Use REST API instead of gRPC
        )
        
        logger.info("=== QDRANT STATUS CHECK ===")
        
        # 1. Check Qdrant connection
        try:
            collections = client.get_collections()
            logger.info(f"✅ Qdrant connection successful")
            logger.info(f"📊 Total collections: {len(collections.collections)}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            return
        
        # 2. List all collections
        logger.info("\n📁 Available Collections:")
        for collection in collections.collections:
            logger.info(f"  - {collection.name}")
        
        # 3. Check documents_rag collection specifically
        collection_name = "documents_rag"
        logger.info(f"\n🔍 Checking '{collection_name}' collection:")
        
        try:
            collection_info = client.get_collection(collection_name)
            logger.info(f"✅ Collection '{collection_name}' exists")
            logger.info(f"📊 Points count: {collection_info.points_count}")
            logger.info(f"🎯 Vector size: {collection_info.config.params.vectors.size}")
            logger.info(f"📏 Distance metric: {collection_info.config.params.vectors.distance}")
            
            if collection_info.points_count > 0:
                logger.info(f"\n📄 Collection has {collection_info.points_count} points")
                
                # Get some example points
                try:
                    points = client.scroll(
                        collection_name=collection_name,
                        limit=5,
                        with_payload=True,
                        with_vectors=False
                    )
                    
                    logger.info("🔍 Sample points:")
                    for i, point in enumerate(points[0], 1):
                        payload = point.payload or {}
                        document_id = payload.get('document_id', 'Unknown')
                        chunk_id = payload.get('chunk_id', 'Unknown')
                        title = payload.get('title', 'No title')
                        logger.info(f"  {i}. Point ID: {point.id}")
                        logger.info(f"     Document ID: {document_id}")
                        logger.info(f"     Chunk ID: {chunk_id}")
                        logger.info(f"     Title: {title}")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to retrieve points: {e}")
                    
            else:
                logger.warning("⚠️ Collection is empty (0 points)")
                
        except Exception as e:
            logger.error(f"❌ Collection '{collection_name}' not found or error: {e}")
        
        # 4. Check for documents collection in Typesense
        logger.info(f"\n🔍 Checking Typesense integration:")
        try:
            from app.services.typesense_indexer_service import TypesenseIndexerService
            
            typesense_service = TypesenseIndexerService()
            
            # Check if documents collection exists
            try:
                # Try to search for any documents
                search_results = await typesense_service.search_documents(
                    collection="documents",
                    query="*",
                    query_by="title,description",
                    limit=5
                )
                
                hits = search_results.get("hits", [])
                logger.info(f"📊 Typesense 'documents' collection has {len(hits)} documents")
                
                if hits:
                    logger.info("🔍 Sample Typesense documents:")
                    for i, hit in enumerate(hits[:3], 1):
                        doc = hit["document"]
                        logger.info(f"  {i}. ID: {doc.get('id', 'Unknown')}")
                        logger.info(f"     Title: {doc.get('title', 'No title')}")
                        logger.info(f"     Type: {doc.get('type', 'Unknown')}")
                        
            except Exception as e:
                logger.warning(f"⚠️ Typesense search failed: {e}")
                
        except Exception as e:
            logger.warning(f"⚠️ Typesense service check failed: {e}")
        
        # 5. Search for our specific document
        logger.info(f"\n🔍 Searching for SSRDMS document:")
        try:
            # Search for documents with 'ssrdms' in the document_id
            points = client.scroll(
                collection_name=collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"text": "ssrdms"}
                        }
                    ]
                },
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if points[0]:
                logger.info(f"✅ Found {len(points[0])} SSRDMS-related points")
                for point in points[0]:
                    payload = point.payload or {}
                    logger.info(f"  - Point ID: {point.id}")
                    logger.info(f"    Document ID: {payload.get('document_id', 'Unknown')}")
                    logger.info(f"    Title: {payload.get('title', 'No title')}")
            else:
                logger.warning("⚠️ No SSRDMS-related documents found")
                
        except Exception as e:
            logger.error(f"❌ Search for SSRDMS documents failed: {e}")
        
        # 6. Check for any recent documents
        logger.info(f"\n🔍 Checking for recent documents:")
        try:
            points = client.scroll(
                collection_name=collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if points[0]:
                logger.info(f"📄 Found {len(points[0])} total points in collection")
                for point in points[0]:
                    payload = point.payload or {}
                    created_at = payload.get('created_at', 'Unknown')
                    logger.info(f"  - Document: {payload.get('document_id', 'Unknown')}")
                    logger.info(f"    Created: {created_at}")
            else:
                logger.warning("⚠️ No points found in collection")
                
        except Exception as e:
            logger.error(f"❌ Failed to check recent documents: {e}")
        
        logger.info("\n=== END QDRANT STATUS CHECK ===")
        
    except Exception as e:
        logger.error(f"❌ Qdrant status check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_qdrant_status()) 