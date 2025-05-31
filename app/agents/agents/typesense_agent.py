"""
TypeSense Agent - Handles search functionality using TypeSense search engine
"""

import asyncio
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.base_agent import BaseAgent, AgentResponse, ArtifactType, AgentCapability
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


class TypeSenseAgent(BaseAgent):
    """
    TypeSense Agent for search and indexing operations.
    Handles document search, indexing, and search analytics.
    """
    
    def __init__(self):
        # Define capabilities for this agent
        capabilities = [
            AgentCapability(
                name="Search Operations",
                description="Search and indexing using TypeSense search engine",
                artifact_types=[ArtifactType.CODE, ArtifactType.ANALYSIS],
                keywords=["search", "find", "query", "index", "filter", "facet", "typesense", "full-text", "lookup"],
                examples=["Search documents", "Full-text search", "Index content", "Search analytics"]
            )
        ]
        
        super().__init__("TypeSense", capabilities)
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for TypeSense agent."""
        return """You are a TypeSense Search Agent. You help users with search, indexing, and information retrieval tasks.

Your capabilities include:
- Full-text search across documents and files
- Advanced search queries with filters and facets
- Search indexing and schema management
- Search analytics and performance optimization
- Auto-complete and search suggestions
- Faceted search and filtering
- Real-time search updates

Provide helpful responses about search operations. When users need to search for information, guide them through effective search strategies and explain search results.

Always focus on helping users find the information they're looking for efficiently."""
        
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user's request."""
        
        # Keywords that indicate search-related tasks
        search_keywords = [
            "search for", "find", "look for", "search", "query", "filter",
            "search files", "find documents", "search content", "full text search",
            "search index", "indexing", "search results", "search analytics",
            "faceted search", "search suggestions", "auto complete", "search filters",
            "search by", "search within", "search across", "typesense"
        ]
        
        user_input_lower = user_input.lower()
        
        # Check for direct search keywords
        if any(keyword in user_input_lower for keyword in search_keywords):
            return True
            
        # Check for search patterns
        search_patterns = [
            "how to find", "where is", "show me", "list all", "get all",
            "find me", "search through", "look through", "browse"
        ]
        
        return any(pattern in user_input_lower for pattern in search_patterns)

    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process search and indexing requests."""
        
        try:
            logger.info(f"TypeSense Agent processing: {user_input}")
            
            # Generate response using the base class method with streaming support
            response_content = await self.generate_response(user_input, config=config)
            
            # Determine if we need to create search artifacts
            artifacts = []
            
            # Check if response involves search operations that need artifacts
            response_lower = response_content.lower()
            if any(keyword in response_lower for keyword in ["search", "query", "index", "schema", "config"]):
                artifacts.append({
                    "type": ArtifactType.CODE,
                    "title": "TypeSense Search Script",
                    "content": self._generate_search_script(user_input, response_content),
                    "language": "python"
                })
            
            return AgentResponse(
                success=True,
                content=response_content,
                artifacts=artifacts,
                metadata={
                    "agent": "typesense",
                    "capabilities": ["search", "indexing", "full_text_search", "faceted_search"],
                    "search_backend": "typesense"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in TypeSense Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": "typesense"},
                error=str(e)
            )
    
    def _generate_search_script(self, user_input: str, response_content: str) -> str:
        """Generate a search script based on the request."""
        
        # Basic TypeSense operations template
        script_template = '''"""
TypeSense Search Script
Generated based on: {user_input}
"""

import typesense
import json
from datetime import datetime
import os

# TypeSense Configuration
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")

class TypeSenseManager:
    def __init__(self):
        self.client = typesense.Client({{
            'nodes': [{{
                'host': TYPESENSE_HOST,
                'port': TYPESENSE_PORT,
                'protocol': TYPESENSE_PROTOCOL
            }}],
            'api_key': TYPESENSE_API_KEY,
            'connection_timeout_seconds': 2
        }})
    
    def create_collection(self, collection_name: str, schema: dict):
        """Create a new collection with the given schema."""
        try:
            self.client.collections[collection_name].delete()
        except:
            pass  # Collection might not exist
        
        try:
            result = self.client.collections.create(schema)
            print(f"Created collection: {{collection_name}}")
            return result
        except Exception as e:
            print(f"Error creating collection: {{e}}")
            return None
    
    def index_document(self, collection_name: str, document: dict):
        """Index a single document."""
        try:
            result = self.client.collections[collection_name].documents.create(document)
            print(f"Indexed document with ID: {{document.get('id', 'unknown')}}")
            return result
        except Exception as e:
            print(f"Error indexing document: {{e}}")
            return None
    
    def search_documents(self, collection_name: str, query: str, 
                        filter_by: str = None, facet_by: str = None, 
                        per_page: int = 10):
        """Search documents in the collection."""
        search_parameters = {{
            'q': query,
            'query_by': 'title,content',
            'per_page': per_page
        }}
        
        if filter_by:
            search_parameters['filter_by'] = filter_by
        
        if facet_by:
            search_parameters['facet_by'] = facet_by
        
        try:
            results = self.client.collections[collection_name].documents.search(search_parameters)
            print(f"Found {{results['found']}} results for query: '{{query}}'")
            return results
        except Exception as e:
            print(f"Error searching documents: {{e}}")
            return None
    
    def get_collection_info(self, collection_name: str):
        """Get information about a collection."""
        try:
            info = self.client.collections[collection_name].retrieve()
            print(f"Collection {{collection_name}} info:")
            print(json.dumps(info, indent=2))
            return info
        except Exception as e:
            print(f"Error getting collection info: {{e}}")
            return None

# Example schema for documents
DOCUMENT_SCHEMA = {{
    'name': 'documents',
    'fields': [
        {{'name': 'id', 'type': 'string'}},
        {{'name': 'title', 'type': 'string'}},
        {{'name': 'content', 'type': 'string'}},
        {{'name': 'category', 'type': 'string', 'facet': True}},
        {{'name': 'created_at', 'type': 'int64'}},
        {{'name': 'tags', 'type': 'string[]', 'facet': True}},
    ],
    'default_sorting_field': 'created_at'
}}

# Example usage
if __name__ == "__main__":
    manager = TypeSenseManager()
    
    # Create collection
    # manager.create_collection('documents', DOCUMENT_SCHEMA)
    
    # Index a document
    # sample_doc = {{
    #     'id': '1',
    #     'title': 'Sample Document',
    #     'content': 'This is a sample document for testing search functionality.',
    #     'category': 'test',
    #     'created_at': int(datetime.now().timestamp()),
    #     'tags': ['sample', 'test', 'document']
    # }}
    # manager.index_document('documents', sample_doc)
    
    # Search documents
    # results = manager.search_documents('documents', 'sample', facet_by='category,tags')
    # if results:
    #     for hit in results['hits']:
    #         print(f"{{hit['document']['title']}}: {{hit['document']['content'][:100]}}")
    
    # Get collection info
    # manager.get_collection_info('documents')
'''
        
        return script_template.format(user_input=user_input)

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return [
            "full_text_search",
            "document_indexing",
            "faceted_search",
            "search_analytics",
            "auto_complete",
            "search_suggestions", 
            "real_time_search",
            "schema_management"
        ] 