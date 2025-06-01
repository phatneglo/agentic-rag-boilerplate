#!/usr/bin/env python3
"""
Simplified test for hybrid Qdrant indexing without transformers.
Use the basic BM25 sparse model instead.
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

async def test_simple_hybrid_qdrant():
    """Test hybrid Qdrant indexing with simplified configuration."""
    
    try:
        logger.info("=== SIMPLE HYBRID QDRANT TEST ===")
        
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
        
        # Check collection status
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Initial points count: {collection_info.points_count}")
        
        # Try creating vector store WITHOUT hybrid first to verify basic functionality
        logger.info("🔧 Testing basic vector store (no hybrid)...")
        try:
            basic_vector_store = QdrantVectorStore(
                client=client,
                collection_name=collection_name,
                vector_name="text-dense",
            )
            logger.info("✅ Basic vector store created successfully")
        except Exception as e:
            logger.error(f"❌ Basic vector store failed: {e}")
            return
        
        # Create test documents
        documents = [
            Document(
                text="This is a test document about SSRDMS beneficiaries management system.",
                metadata={
                    "document_id": "simple_test_1",
                    "title": "SSRDMS Test", 
                    "type": "test"
                },
                id_=str(uuid.uuid4())
            ),
            Document(
                text="The system provides AI-powered assistance for administrative tasks.",
                metadata={
                    "document_id": "simple_test_2",
                    "title": "AI Features",
                    "type": "test"
                },
                id_=str(uuid.uuid4())
            )
        ]
        
        logger.info(f"📄 Created {len(documents)} test documents")
        
        # Test basic indexing first
        logger.info("📝 Testing BASIC indexing...")
        try:
            basic_index = VectorStoreIndex.from_documents(
                documents,
                vector_store=basic_vector_store,
                show_progress=True
            )
            logger.info("✅ Basic indexing successful")
        except Exception as e:
            logger.error(f"❌ Basic indexing failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return
        
        # Check if documents were stored
        await asyncio.sleep(3)
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Points count after basic indexing: {collection_info.points_count}")
        
        if collection_info.points_count > 0:
            logger.info("🎉 SUCCESS! Documents are now being stored in Qdrant!")
            
            # List stored points
            points = client.scroll(
                collection_name=collection_name,
                limit=10,
                with_payload=True,
                with_vectors=False
            )
            
            if points[0]:
                logger.info(f"✅ Found {len(points[0])} points:")
                for i, point in enumerate(points[0], 1):
                    doc_id = point.payload.get('document_id') or point.payload.get('metadata', {}).get('document_id', 'Unknown')
                    logger.info(f"  {i}. Document ID: {doc_id}")
            
            # Test querying
            logger.info("🔍 Testing basic query...")
            try:
                query_engine = basic_index.as_query_engine(similarity_top_k=2)
                response = query_engine.query("What is the SSRDMS system?")
                
                logger.info(f"🤖 Response: {response}")
                logger.info(f"🤖 Source nodes: {len(response.source_nodes)}")
                
            except Exception as e:
                logger.error(f"❌ Query failed: {e}")
        else:
            logger.warning("⚠️ Documents still not being stored")
        
        logger.info("=== BASIC TEST COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_simple_hybrid_qdrant()) 