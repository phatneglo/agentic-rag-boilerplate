#!/usr/bin/env python3
"""
Simple debug script to test exactly what happens with Qdrant + LlamaIndex indexing.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def debug_simple_indexing():
    """Debug simple document indexing without workers."""
    
    try:
        logger.info("=== SIMPLE QDRANT INDEXING DEBUG ===")
        
        # Configure LlamaIndex settings
        Settings.llm = OpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=0.1
        )
        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key
        )
        
        # Initialize Qdrant client
        qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=False,
            https=False,
        )
        
        # Initialize vector store
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name="documents_rag",
        )
        
        # 1. Check initial status
        collection_info = qdrant_client.get_collection("documents_rag")
        logger.info(f"📊 Initial points count: {collection_info.points_count}")
        
        # 2. Create a simple test document with UUID
        document_id = "debug_simple_test"
        doc_uuid = str(uuid.uuid4())
        
        document = Document(
            text="This is a simple test document for debugging Qdrant indexing. It contains some test content to verify storage.",
            metadata={
                "document_id": document_id,
                "title": "Debug Test Document", 
                "type": "test",
                "created_at": datetime.utcnow().isoformat()
            },
            id_=doc_uuid
        )
        
        logger.info(f"📄 Created document with UUID: {doc_uuid}")
        logger.info(f"📄 Document ID: {document_id}")
        
        # 3. Index the document
        logger.info("📝 Indexing document...")
        index = VectorStoreIndex.from_documents(
            [document],
            vector_store=vector_store,
            show_progress=True
        )
        
        # 4. Wait a moment for indexing
        await asyncio.sleep(3)
        
        # 5. Check status after indexing  
        collection_info = qdrant_client.get_collection("documents_rag")
        logger.info(f"📊 Points count after indexing: {collection_info.points_count}")
        
        # 6. Search for the document by document_id
        logger.info("🔍 Searching for the document...")
        
        # Try different metadata key patterns
        for metadata_key in ["document_id", "metadata.document_id", "_node_content", "doc_id"]:
            try:
                logger.info(f"Trying metadata key: {metadata_key}")
                points = qdrant_client.scroll(
                    collection_name="documents_rag",
                    scroll_filter={
                        "must": [
                            {
                                "key": metadata_key,
                                "match": {"value": document_id}
                            }
                        ]
                    },
                    limit=10,
                    with_payload=True,
                    with_vectors=False
                )
                
                if points[0]:
                    logger.info(f"✅ Found {len(points[0])} points with key '{metadata_key}'")
                    for point in points[0]:
                        logger.info(f"  📄 Point ID: {point.id}")
                        logger.info(f"      Payload keys: {list(point.payload.keys())}")
                        logger.info(f"      Payload: {point.payload}")
                else:
                    logger.info(f"❌ No points found with key '{metadata_key}'")
                    
            except Exception as e:
                logger.warning(f"Error with key '{metadata_key}': {e}")
        
        # 7. List all points to see what's actually stored
        logger.info("📊 Listing all points in collection...")
        all_points = qdrant_client.scroll(
            collection_name="documents_rag",
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if all_points[0]:
            logger.info(f"📄 Total points found: {len(all_points[0])}")
            for i, point in enumerate(all_points[0], 1):
                logger.info(f"  {i}. Point ID: {point.id}")
                logger.info(f"     Payload keys: {list(point.payload.keys())}")
                logger.info(f"     Payload: {point.payload}")
        else:
            logger.warning("⚠️ No points found in collection!")
        
        # 8. Test search directly  
        logger.info("🔍 Testing vector search...")
        search_results = qdrant_client.search(
            collection_name="documents_rag",
            query_vector=[0.1] * 1536,  # Dummy vector
            limit=5,
            with_payload=True
        )
        
        if search_results:
            logger.info(f"🔍 Vector search returned {len(search_results)} results")
            for i, result in enumerate(search_results, 1):
                logger.info(f"  {i}. Score: {result.score}")
                logger.info(f"     Payload: {result.payload}")
        else:
            logger.warning("⚠️ Vector search returned no results!")
        
        # 9. Test LlamaIndex query
        logger.info("🤖 Testing LlamaIndex query...")
        query_engine = index.as_query_engine(similarity_top_k=3)
        response = query_engine.query("What is this document about?")
        
        logger.info(f"🤖 LlamaIndex response: {response}")
        logger.info(f"🤖 Source nodes: {len(response.source_nodes)}")
        
        for i, node in enumerate(response.source_nodes, 1):
            logger.info(f"  {i}. Text: {node.text[:100]}...")
            logger.info(f"     Metadata: {node.metadata}")
            logger.info(f"     Score: {node.score}")
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_simple_indexing()) 