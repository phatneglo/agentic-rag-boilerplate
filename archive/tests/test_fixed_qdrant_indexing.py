#!/usr/bin/env python3
"""
Test script following the exact LlamaIndex Qdrant documentation pattern.
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
from qdrant_client import QdrantClient, models

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def test_fixed_qdrant_indexing():
    """Test Qdrant indexing following the exact documentation pattern."""
    
    try:
        logger.info("=== FIXED QDRANT INDEXING TEST ===")
        
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
        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=False,
            https=False,
        )
        
        collection_name = "documents_rag"
        
        # 1. Check initial status
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Initial points count: {collection_info.points_count}")
        
        # 2. Create vector store following documentation pattern
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            vector_name="text-dense",  # Specify named vector
        )
        
        # 3. Create test documents
        documents = [
            Document(
                text="This is a test document about SSRDMS beneficiaries management system. It handles AI assistants and user interactions.",
                metadata={
                    "document_id": "test_doc_fixed_1",
                    "title": "SSRDMS Test Document", 
                    "type": "test"
                },
                id_=str(uuid.uuid4())
            ),
            Document(
                text="The system provides AI-powered assistance for managing beneficiaries and handling various administrative tasks.",
                metadata={
                    "document_id": "test_doc_fixed_2",
                    "title": "AI Assistant Features",
                    "type": "documentation"
                },
                id_=str(uuid.uuid4())
            )
        ]
        
        logger.info(f"📄 Created {len(documents)} test documents")
        
        # 4. Index documents using VectorStoreIndex
        logger.info("📝 Indexing documents...")
        try:
            index = VectorStoreIndex.from_documents(
                documents,
                vector_store=vector_store,
                show_progress=True
            )
            logger.info("✅ Documents indexed successfully")
        except Exception as e:
            logger.error(f"❌ Indexing failed: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return
        
        # 5. Wait and check status
        await asyncio.sleep(3)
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Points count after indexing: {collection_info.points_count}")
        
        # 6. List all points to verify storage
        points = client.scroll(
            collection_name=collection_name,
            limit=10,
            with_payload=True,
            with_vectors=False
        )
        
        if points[0]:
            logger.info(f"✅ Found {len(points[0])} points in collection")
            for i, point in enumerate(points[0], 1):
                logger.info(f"  {i}. Point ID: {point.id}")
                logger.info(f"     Document ID: {point.payload.get('document_id', 'Unknown')}")
                logger.info(f"     Title: {point.payload.get('title', 'No title')}")
        else:
            logger.warning("⚠️ No points found after indexing")
        
        # 7. Test search with proper vector name
        logger.info("🔍 Testing vector search with named vector...")
        try:
            search_results = client.search(
                collection_name=collection_name,
                query_vector=[0.1] * 1536,
                using="text-dense",  # Specify vector name
                limit=5,
                with_payload=True
            )
            
            if search_results:
                logger.info(f"✅ Search returned {len(search_results)} results")
                for i, result in enumerate(search_results, 1):
                    logger.info(f"  {i}. Score: {result.score}")
                    logger.info(f"     Document ID: {result.payload.get('document_id')}")
            else:
                logger.warning("⚠️ Search returned no results")
                
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
        
        # 8. Test LlamaIndex query
        logger.info("🤖 Testing LlamaIndex query...")
        try:
            query_engine = index.as_query_engine(similarity_top_k=3)
            response = query_engine.query("What is the SSRDMS system about?")
            
            logger.info(f"🤖 Response: {response}")
            logger.info(f"🤖 Source nodes: {len(response.source_nodes)}")
            
            for i, node in enumerate(response.source_nodes, 1):
                logger.info(f"  {i}. Score: {node.score}")
                logger.info(f"     Text: {node.text[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ LlamaIndex query failed: {e}")
        
        logger.info("=== TEST COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_fixed_qdrant_indexing()) 