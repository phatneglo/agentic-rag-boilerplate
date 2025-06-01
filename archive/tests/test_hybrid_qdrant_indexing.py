#!/usr/bin/env python3
"""
Test script to verify hybrid Qdrant indexing works correctly.
Following the LlamaIndex documentation for Qdrant hybrid search.
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

async def test_hybrid_qdrant_indexing():
    """Test hybrid Qdrant indexing following the documentation pattern."""
    
    try:
        logger.info("=== HYBRID QDRANT INDEXING TEST ===")
        
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
        logger.info(f"🔍 Dense vectors: {collection_info.config.params.vectors}")
        logger.info(f"🔍 Sparse vectors: {collection_info.config.params.sparse_vectors}")
        
        # 2. Create vector store with HYBRID enabled
        vector_store = QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            vector_name="text-dense",  # Specify dense vector name
            enable_hybrid=True,  # Enable hybrid search
            fastembed_sparse_model="Qdrant/bm25",  # Use BM25 for sparse vectors
            batch_size=20,  # Batch size for sparse vector generation
        )
        
        logger.info("✅ Vector store configured with hybrid search enabled")
        
        # 3. Create test documents
        documents = [
            Document(
                text="This is a test document about SSRDMS beneficiaries management system. It handles AI assistants and user interactions for administrative tasks.",
                metadata={
                    "document_id": "hybrid_test_doc_1",
                    "title": "SSRDMS Management System", 
                    "type": "documentation",
                    "category": "system"
                },
                id_=str(uuid.uuid4())
            ),
            Document(
                text="The system provides AI-powered assistance for managing beneficiaries and handling various administrative workflows efficiently.",
                metadata={
                    "document_id": "hybrid_test_doc_2",
                    "title": "AI Assistant Features",
                    "type": "documentation",
                    "category": "features"
                },
                id_=str(uuid.uuid4())
            ),
            Document(
                text="Frontend interface built with HTML, CSS, and JavaScript provides user-friendly access to the SSRDMS platform.",
                metadata={
                    "document_id": "hybrid_test_doc_3",
                    "title": "Frontend Interface",
                    "type": "technical",
                    "category": "frontend"
                },
                id_=str(uuid.uuid4())
            )
        ]
        
        logger.info(f"📄 Created {len(documents)} test documents")
        
        # 4. Index documents using hybrid VectorStoreIndex
        logger.info("📝 Indexing documents with HYBRID search...")
        try:
            index = VectorStoreIndex.from_documents(
                documents,
                vector_store=vector_store,
                show_progress=True
            )
            logger.info("✅ Documents indexed successfully with HYBRID search")
        except Exception as e:
            logger.error(f"❌ Hybrid indexing failed: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return
        
        # 5. Wait and check status
        await asyncio.sleep(5)
        collection_info = client.get_collection(collection_name)
        logger.info(f"📊 Points count after HYBRID indexing: {collection_info.points_count}")
        
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
                doc_id = point.payload.get('document_id') or point.payload.get('metadata', {}).get('document_id', 'Unknown')
                title = point.payload.get('title') or point.payload.get('metadata', {}).get('title', 'No title')
                logger.info(f"     Document ID: {doc_id}")
                logger.info(f"     Title: {title}")
        else:
            logger.warning("⚠️ No points found after indexing")
            return
        
        # 7. Test HYBRID search functionality
        logger.info("🔍 Testing HYBRID search functionality...")
        try:
            # Test with hybrid query engine
            hybrid_query_engine = index.as_query_engine(
                similarity_top_k=2,  # Final number of returned nodes
                sparse_top_k=5,  # Number of nodes from each sparse/dense query
                vector_store_query_mode="hybrid"  # Enable hybrid mode
            )
            
            response = hybrid_query_engine.query("What is the SSRDMS system about?")
            
            logger.info(f"🤖 HYBRID Response: {response}")
            logger.info(f"🤖 Source nodes: {len(response.source_nodes)}")
            
            for i, node in enumerate(response.source_nodes, 1):
                logger.info(f"  {i}. Score: {node.score}")
                logger.info(f"     Text: {node.text[:100]}...")
                
        except Exception as e:
            logger.error(f"❌ HYBRID query failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 8. Compare with dense-only search
        logger.info("🔍 Testing dense-only search for comparison...")
        try:
            dense_query_engine = index.as_query_engine(
                similarity_top_k=2,
                # No sparse parameters = dense only
            )
            
            response = dense_query_engine.query("What is the SSRDMS system about?")
            
            logger.info(f"🤖 DENSE-ONLY Response: {response}")
            logger.info(f"🤖 Source nodes: {len(response.source_nodes)}")
            
        except Exception as e:
            logger.error(f"❌ Dense-only query failed: {e}")
        
        logger.info("=== HYBRID TEST COMPLETE ===")
        logger.info("🎉 Hybrid search is now working!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_hybrid_qdrant_indexing()) 