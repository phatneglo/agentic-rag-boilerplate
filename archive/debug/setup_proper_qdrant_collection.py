#!/usr/bin/env python3
"""
Setup Qdrant collection following LlamaIndex documentation recommendations.
Based on: https://docs.llamaindex.ai/en/stable/examples/vector_stores/qdrant_hybrid/
"""
import asyncio
import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

from qdrant_client import QdrantClient, models
from llama_index.core import Document, VectorStoreIndex, Settings, StorageContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.qdrant import QdrantVectorStore

# Configure logging
configure_logging()
logger = get_logger(__name__)

async def setup_proper_qdrant():
    """Setup Qdrant collection following LlamaIndex documentation."""
    
    try:
        logger.info("=== SETTING UP QDRANT FOR LLAMAINDEX ===")
        
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
        Settings.chunk_size = 512  # Following documentation
        
        # Initialize Qdrant client
        client = QdrantClient(host="localhost", port=6333)
        
        collection_name = "documents_rag"
        
        logger.info(f"🗑️ Deleting existing collection '{collection_name}'...")
        try:
            client.delete_collection(collection_name)
            logger.info("✅ Existing collection deleted")
        except Exception as e:
            logger.info(f"Collection doesn't exist or error: {e}")
        
        logger.info("🏗️ Creating new collection with basic vector configuration...")
        
        # Create collection with simple configuration first
        # Following the LlamaIndex docs approach - let LlamaIndex handle collection creation
        vector_store = QdrantVectorStore(
            collection_name=collection_name,
            client=client,
            # No hybrid for now to avoid PyTorch conflicts
        )
        
        # Create storage context
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        logger.info("📄 Testing with a simple document...")
        
        # Create test documents
        documents = [
            Document(
                text="This is a test document about SSRDMS beneficiaries management system. The system provides AI-powered assistance for administrative tasks in social services.",
                metadata={
                    "document_id": "test_doc_1",
                    "title": "SSRDMS Test Document",
                    "type": "test",
                    "category": "system"
                }
            ),
            Document(
                text="The beneficiaries management system handles registration, verification, and assistance distribution for social service recipients.",
                metadata={
                    "document_id": "test_doc_2", 
                    "title": "Beneficiaries Management",
                    "type": "test",
                    "category": "documentation"
                }
            )
        ]
        
        logger.info(f"📝 Indexing {len(documents)} test documents...")
        
        # Create index with explicit storage context
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            show_progress=True
        )
        
        logger.info("✅ Index created successfully")
        
        # Wait a moment for indexing to complete
        await asyncio.sleep(3)
        
        # Check collection status
        try:
            collection_info = client.get_collection(collection_name)
            points_count = collection_info.points_count
            logger.info(f"📊 Points in collection: {points_count}")
            
            if points_count > 0:
                logger.info("🎉 SUCCESS! Documents are stored in Qdrant!")
                
                # Test querying
                logger.info("🔍 Testing query...")
                query_engine = index.as_query_engine(similarity_top_k=2)
                response = query_engine.query("What is the SSRDMS system about?")
                
                logger.info(f"🤖 Query Response: {response}")
                logger.info(f"📚 Number of sources: {len(response.source_nodes)}")
                
                # List some points for verification
                points = client.scroll(
                    collection_name=collection_name,
                    limit=5,
                    with_payload=True,
                    with_vectors=False
                )
                
                if points[0]:
                    logger.info(f"✅ Found {len(points[0])} points in collection:")
                    for i, point in enumerate(points[0], 1):
                        payload = point.payload
                        doc_id = payload.get('doc_id', 'Unknown')
                        text_preview = payload.get('text', '')[:100] + "..." if len(payload.get('text', '')) > 100 else payload.get('text', '')
                        logger.info(f"  {i}. ID: {doc_id}, Text: {text_preview}")
                
            else:
                logger.warning("⚠️ No points found in collection")
                
        except Exception as e:
            logger.error(f"❌ Error checking collection: {e}")
        
        logger.info("=== SETUP COMPLETE ===")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(setup_proper_qdrant()) 