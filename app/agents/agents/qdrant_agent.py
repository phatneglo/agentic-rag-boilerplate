"""
Qdrant Agent - Handles RAG functionality using Qdrant vector database
"""

import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool

from app.agents.base_agent import BaseAgent, AgentResponse, ArtifactType, AgentCapability
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class QdrantAgent(BaseAgent):
    """
    Qdrant Agent for RAG (Retrieval Augmented Generation) operations.
    Handles vector search, document retrieval, and knowledge-based responses.
    """
    
    def __init__(self):
        # Define capabilities for this agent
        capabilities = [
            AgentCapability(
                name="RAG Operations",
                description="Retrieval Augmented Generation using Qdrant vector database",
                artifact_types=[ArtifactType.CODE, ArtifactType.ANALYSIS],
                keywords=["rag", "retrieval", "vector", "search", "knowledge", "semantic", "similarity", "qdrant"],
                examples=["Find relevant documents", "Semantic search", "Knowledge retrieval", "Vector similarity search"]
            )
        ]
        
        super().__init__("Qdrant", capabilities)
        
        # Initialize embeddings for vector operations
        self.embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)
        
    def get_system_prompt(self) -> str:
        """Return the system prompt for the Qdrant Agent."""
        return """You are a Qdrant RAG Agent. You help users by retrieving relevant information from a knowledge base and providing comprehensive answers.

Your capabilities include:
- Vector similarity search for relevant content
- Context-aware question answering
- Document retrieval and analysis
- Knowledge synthesis from multiple sources
- Semantic search across large document collections
- Providing answers with source citations

When answering questions:
1. Retrieve relevant context from the knowledge base
2. Synthesize information from multiple sources
3. Provide comprehensive, accurate answers
4. Include source references when available
5. Explain if information is not found in the knowledge base

Always be precise and cite your sources when providing information."""
        
    async def can_handle(self, user_input: str, context: Dict[str, Any] = None) -> bool:
        """Check if this agent can handle the user's request."""
        
        # Keywords that indicate RAG/knowledge retrieval tasks
        rag_keywords = [
            "what is", "explain", "tell me about", "how does", "define",
            "based on", "according to", "retrieve information", "find information",
            "knowledge base", "vector search", "semantic search", "similarity search",
            "rag", "retrieval", "context", "relevant documents", "related content",
            "answer based on", "look up", "research", "information about"
        ]
        
        user_input_lower = user_input.lower()
        
        # Check for direct RAG keywords
        if any(keyword in user_input_lower for keyword in rag_keywords):
            return True
            
        # Check for question patterns that typically require knowledge retrieval
        question_patterns = [
            "what", "how", "why", "when", "where", "who", "which",
            "can you explain", "tell me", "describe", "provide information"
        ]
        
        # Questions longer than 4 words often need knowledge retrieval
        word_count = len(user_input.split())
        if word_count > 4 and any(pattern in user_input_lower for pattern in question_patterns):
            return True
            
        return False

    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process RAG requests with retrieval and generation."""
        
        try:
            logger.info(f"Qdrant Agent processing: {user_input}")
            
            # Use the base class generate_response method for consistent streaming
            response_content = await self.generate_response(user_input, config=config)
            
            # Determine if we need to create RAG artifacts
            artifacts = []
            
            # Check if response involves RAG operations that need artifacts
            response_lower = response_content.lower()
            if any(keyword in response_lower for keyword in ["vector", "embedding", "retrieval", "qdrant", "database"]):
                artifacts.append({
                    "type": ArtifactType.CODE,
                    "title": "Qdrant RAG Implementation",
                    "content": self._generate_rag_script(user_input, response_content),
                    "language": "python"
                })
            
            return AgentResponse(
                success=True,
                content=response_content,
                artifacts=artifacts,
                metadata={
                    "agent": "qdrant",
                    "capabilities": ["rag", "vector_search", "knowledge_retrieval", "semantic_search"],
                    "vector_backend": "qdrant"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in Qdrant Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": "qdrant"},
                error=str(e)
            )
    
    def _generate_rag_script(self, user_input: str, response_content: str) -> str:
        """Generate a RAG implementation script based on the request."""
        
        # Basic Qdrant RAG operations template
        script_template = '''"""
Qdrant RAG Implementation Script
Generated based on: {user_input}
"""

import asyncio
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
import numpy as np
import os

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

class QdrantRAGManager:
    def __init__(self):
        # Initialize Qdrant client
        self.client = QdrantClient(
            host=QDRANT_HOST,
            port=QDRANT_PORT,
            api_key=QDRANT_API_KEY if QDRANT_API_KEY else None
        )
        
        # Initialize embeddings and LLM
        self.embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,
            api_key=OPENAI_API_KEY
        )
        
        # Text splitter for documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def create_collection(self, collection_name: str, vector_size: int = 1536):
        """Create a new collection in Qdrant."""
        try:
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"Created collection: {{collection_name}}")
            return True
        except Exception as e:
            print(f"Error creating collection: {{e}}")
            return False
    
    def index_documents(self, collection_name: str, documents: List[str], 
                       metadata: List[Dict] = None):
        """Index documents into the Qdrant collection."""
        try:
            # Split documents into chunks
            all_chunks = []
            all_metadata = []
            
            for i, doc in enumerate(documents):
                chunks = self.text_splitter.split_text(doc)
                all_chunks.extend(chunks)
                
                # Add metadata for each chunk
                doc_metadata = metadata[i] if metadata and i < len(metadata) else {{}}
                for j, chunk in enumerate(chunks):
                    chunk_metadata = doc_metadata.copy()
                    chunk_metadata.update({{
                        "document_id": i,
                        "chunk_id": j,
                        "text": chunk
                    }})
                    all_metadata.append(chunk_metadata)
            
            # Generate embeddings
            embeddings = self.embeddings.embed_documents(all_chunks)
            
            # Create points for Qdrant
            points = []
            for i, (embedding, metadata) in enumerate(zip(embeddings, all_metadata)):
                points.append(PointStruct(
                    id=i,
                    vector=embedding,
                    payload=metadata
                ))
            
            # Upload to Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            print(f"Indexed {{len(points)}} chunks in collection {{collection_name}}")
            return True
            
        except Exception as e:
            print(f"Error indexing documents: {{e}}")
            return False
    
    def similarity_search(self, collection_name: str, query: str, top_k: int = 5):
        """Perform similarity search in the collection."""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search in Qdrant
            search_result = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k
            )
            
            # Extract results
            results = []
            for point in search_result:
                results.append({{
                    "text": point.payload.get("text", ""),
                    "score": point.score,
                    "metadata": point.payload
                }})
            
            return results
            
        except Exception as e:
            print(f"Error in similarity search: {{e}}")
            return []
    
    async def rag_query(self, collection_name: str, question: str, top_k: int = 5):
        """Perform RAG query: retrieve relevant documents and generate answer."""
        try:
            # Retrieve relevant documents
            relevant_docs = self.similarity_search(collection_name, question, top_k)
            
            if not relevant_docs:
                return "No relevant information found in the knowledge base."
            
            # Prepare context from retrieved documents
            context = "\\n\\n".join([
                f"Document {{i+1}}:\\n{{doc['text']}}"
                for i, doc in enumerate(relevant_docs)
            ])
            
            # Create RAG prompt
            rag_prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant that answers questions based on the provided context.
                Use only the information from the context to answer the question.
                If the answer is not in the context, say so clearly.
                Provide specific, accurate answers and cite relevant parts of the context."""),
                ("human", """Context:
{{context}}

Question: {{question}}

Answer:""")
            ])
            
            # Generate answer
            chain = rag_prompt | self.llm
            response = await chain.ainvoke({{
                "context": context,
                "question": question
            }})
            
            return {{
                "answer": response.content,
                "sources": relevant_docs,
                "context_used": context
            }}
            
        except Exception as e:
            print(f"Error in RAG query: {{e}}")
            return "Error processing your question."

# Example usage
async def main():
    manager = QdrantRAGManager()
    
    # Create collection
    # manager.create_collection("knowledge_base")
    
    # Index sample documents
    # sample_docs = [
    #     "Artificial Intelligence is the simulation of human intelligence processes by machines.",
    #     "Machine Learning is a subset of AI that enables systems to learn from data.",
    #     "Natural Language Processing helps computers understand human language."
    # ]
    # metadata = [
    #     {{"source": "AI_guide.pdf", "topic": "AI"}},
    #     {{"source": "ML_basics.pdf", "topic": "ML"}},
    #     {{"source": "NLP_intro.pdf", "topic": "NLP"}}
    # ]
    # manager.index_documents("knowledge_base", sample_docs, metadata)
    
    # Perform RAG query
    # result = await manager.rag_query("knowledge_base", "What is machine learning?")
    # print("Answer:", result["answer"])

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        return script_template.format(user_input=user_input)

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return [
            "vector_search",
            "semantic_search",
            "document_retrieval",
            "knowledge_qa",
            "rag_generation",
            "context_synthesis",
            "similarity_matching",
            "source_citation"
        ] 