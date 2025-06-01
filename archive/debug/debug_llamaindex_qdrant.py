#!/usr/bin/env python3
"""
Debug script to understand what LlamaIndex is doing with Qdrant.
"""
import asyncio
import os
import sys
import uuid
import logging

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Enable debug logging for LlamaIndex
logging.getLogger("llama_index").setLevel(logging.DEBUG)

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def debug_llamaindex_qdrant():
    """Debug what LlamaIndex is doing with Qdrant."""
    
    try:
        logger.info("=== DEBUG LLAMAINDEX QDRANT ===")
        
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
        
        # Initialize Qdrant client with debug info
        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            prefer_grpc=False,
            https=False,
        )
        
        collection_name = "documents_rag"
        
        # Create vector store with debugging
        logger.info("🔧 Creating vector store...")
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            vector_name="text-dense",
        )
        
        # Create a single simple document
        document = Document(
            text="Simple test document for debugging.",
            metadata={"test": "debug"},
            id_=str(uuid.uuid4())
        )
        
        logger.info("📄 Created test document")
        logger.info(f"Document ID: {document.id_}")
        logger.info(f"Document text: {document.text}")
        logger.info(f"Document metadata: {document.metadata}")
        
        # Try to add the document directly to the vector store
        logger.info("🔍 Testing direct vector store add...")
        try:
            # First, let's see what happens when we try to add directly
            vector_store.add([document])
            logger.info("✅ Direct add completed")
        except Exception as e:
            logger.error(f"❌ Direct add failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Check collection after direct add
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Points after direct add: {collection_info.points_count}")
        
        # Try with VectorStoreIndex approach
        logger.info("🔍 Testing VectorStoreIndex approach...")
        try:
            index = VectorStoreIndex.from_documents(
                [document],
                vector_store=vector_store,
                show_progress=True
            )
            logger.info("✅ VectorStoreIndex completed")
        except Exception as e:
            logger.error(f"❌ VectorStoreIndex failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Check collection after index
        await asyncio.sleep(2)
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Points after VectorStoreIndex: {collection_info.points_count}")
        
        # Let's also check what the vector store thinks it's doing
        logger.info("🔍 Checking vector store internals...")
        logger.info(f"Vector store client: {vector_store._client}")
        logger.info(f"Vector store collection: {vector_store._collection_name}")
        logger.info(f"Vector store vector name: {vector_store._vector_name}")
        
        # Try manual inspection of the collection
        logger.info("🔍 Manual collection inspection...")
        try:
            # Try to scroll through points
            scroll_result = client.scroll(
                collection_name=collection_name,
                limit=100,
                with_payload=True,
                with_vectors=True
            )
            
            logger.info(f"Scroll result: {len(scroll_result[0])} points found")
            if scroll_result[0]:
                for point in scroll_result[0]:
                    logger.info(f"Point: {point.id}, payload: {point.payload}")
            
        except Exception as e:
            logger.error(f"❌ Manual inspection failed: {e}")
        
        logger.info("=== DEBUG COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Debug failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(debug_llamaindex_qdrant()) 