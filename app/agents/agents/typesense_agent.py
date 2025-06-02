"""
TypeSense Agent - Enhanced with intelligent document search and structured results
"""

import asyncio
import re
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.base_agent import BaseAgent, AgentResponse, ArtifactType, AgentCapability
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

import typesense
import json
from datetime import datetime
import os

# TypeSense Configuration
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_COLLECTION_NAME = os.getenv("TYPESENSE_COLLECTION_NAME", "documents")

class TypeSenseAgent(BaseAgent):
    """
    Enhanced TypeSense Agent for intelligent document search with structured results.
    Detects search requests and returns interactive search results as artifacts.
    """
    
    def __init__(self):
        # Define capabilities for this agent
        capabilities = [
            AgentCapability(
                name="Document Search",
                description="Intelligent document search with structured, interactive results",
                artifact_types=[ArtifactType.ANALYSIS, ArtifactType.CODE],
                keywords=[
                    "search", "find", "look for", "search documents", "search knowledge base",
                    "find documents", "search files", "document search", "knowledge search",
                    "search my documents", "find in documents", "search content"
                ],
                examples=[
                    "Search for documents about machine learning",
                    "Find documents related to Python programming",
                    "Search my knowledge base for API documentation",
                    "Look for documents containing 'database design'"
                ]
            ),
            AgentCapability(
                name="Search Operations",
                description="Advanced search operations and indexing",
                artifact_types=[ArtifactType.CODE, ArtifactType.ANALYSIS],
                keywords=["index", "query", "filter", "facet", "typesense", "full-text", "schema"],
                examples=["Index new documents", "Create search schema", "Configure search filters"]
            )
        ]
        
        super().__init__("TypeSense", capabilities)
        
        # Initialize TypeSense client
        self.typesense_client = None
        self._init_typesense()
    
    def _init_typesense(self):
        """Initialize TypeSense client."""
        try:
            self.typesense_client = typesense.Client({
                'nodes': [{
                    'host': TYPESENSE_HOST,
                    'port': TYPESENSE_PORT,
                    'protocol': TYPESENSE_PROTOCOL
                }],
                'api_key': TYPESENSE_API_KEY,
                'connection_timeout_seconds': 2
            })
            logger.info("TypeSense client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TypeSense client: {e}")
            self.typesense_client = None
    
    def get_system_prompt(self) -> str:
        """Return the system prompt for TypeSense agent."""
        return """You are an intelligent Document Search Agent powered by TypeSense. You help users find and explore documents in their knowledge base.

Your capabilities include:
- Intelligent document search with natural language queries
- Structured search results with titles, descriptions, and metadata
- Interactive document listings that users can click to open
- Advanced search with filters, facets, and sorting
- Search analytics and suggestions
- Document indexing and schema management

When users ask to search for documents or information, you should:
1. Understand their search intent and extract key search terms
2. Perform the actual search using TypeSense
3. Return structured search results as interactive artifacts
4. Provide helpful context about the search results

For document search requests, always return results in a structured format that the frontend can render as an interactive document list with clickable items.

Focus on helping users discover and access relevant documents efficiently."""
        
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user's request."""
        
        # Enhanced patterns for document search detection
        search_patterns = [
            # Direct search requests
            r"search\s+(for\s+)?documents?\s+about",
            r"find\s+(me\s+)?documents?\s+(about|on|related\s+to)",
            r"search\s+(my\s+)?(knowledge\s+base|documents?|files?)",
            r"look\s+for\s+documents?",
            r"find\s+(in\s+)?(my\s+)?documents?",
            
            # Knowledge base specific
            r"search\s+(my\s+)?knowledge\s+base",
            r"find\s+(in\s+)?(my\s+)?knowledge\s+base",
            r"search\s+(through\s+)?(my\s+)?files?",
            
            # Content search
            r"search\s+(for\s+)?.*\s+(documents?|files?|content)",
            r"find\s+.*\s+(documents?|files?|content)",
            r"documents?\s+(about|on|containing|with)",
            
            # Implicit search requests
            r"what\s+documents?\s+do\s+(I|we)\s+have\s+(about|on)",
            r"show\s+me\s+(documents?|files?)\s+(about|on|containing)",
            r"list\s+(documents?|files?)\s+(about|on|related\s+to)",
        ]
        
        user_input_lower = user_input.lower()
        
        # Check for search patterns
        for pattern in search_patterns:
            if re.search(pattern, user_input_lower):
                return True
        
        # Simple keyword checks
        search_keywords = [
            "search documents", "find documents", "search knowledge base",
            "search files", "document search", "search content",
            "search my documents", "find in documents"
        ]
        
        return any(keyword in user_input_lower for keyword in search_keywords)

    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process search requests with intelligent document search."""
        
        try:
            logger.info(f"TypeSense Agent processing: {user_input}")
            
            # Detect if this is a document search request
            if self._is_document_search_request(user_input):
                return await self._handle_document_search(user_input, context, config)
            else:
                return await self._handle_general_request(user_input, context, config)
                
        except Exception as e:
            logger.error(f"Error in TypeSense Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": "typesense"},
                error=str(e)
            )
    
    def _is_document_search_request(self, user_input: str) -> bool:
        """Determine if the request is for document search."""
        search_indicators = [
            "search", "find", "look for", "documents", "knowledge base",
            "search for", "find me", "search documents", "find documents"
        ]
        
        user_input_lower = user_input.lower()
        search_count = sum(1 for indicator in search_indicators if indicator in user_input_lower)
        
        # If we have multiple search indicators, it's likely a search request
        return search_count >= 2 or any(phrase in user_input_lower for phrase in [
            "search documents", "find documents", "search knowledge base",
            "search my documents", "document search", "search for documents"
        ])
    
    async def _handle_document_search(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Handle document search requests with structured results."""
        
        # Extract search query from user input
        search_query = self._extract_search_query(user_input)
        logger.info(f"Extracted search query: '{search_query}'")
        
        # Perform the actual search
        search_results = await self._perform_document_search(search_query)
        
        if search_results is None:
            return AgentResponse(
                success=False,
                content="I encountered an error while searching the documents. The TypeSense search service might not be available.",
                artifacts=[],
                metadata={"agent": "typesense", "error": "search_service_unavailable"}
            )
        
        # Generate response content
        response_content = self._generate_search_response(search_query, search_results)
        
        # Create structured search results artifact
        artifacts = []
        if search_results.get('hits'):
            search_artifact = self._create_search_results_artifact(search_query, search_results)
            artifacts.append(search_artifact)
        
        return AgentResponse(
            success=True,
            content=response_content,
            artifacts=artifacts,
            metadata={
                "agent": "typesense",
                "search_query": search_query,
                "total_results": search_results.get('found', 0),
                "search_type": "document_search"
            }
        )
    
    def _extract_search_query(self, user_input: str) -> str:
        """Extract the actual search query from user input."""
        
        # Remove common search prefixes
        patterns_to_remove = [
            r"^(search\s+(for\s+)?(documents?\s+)?(about\s+)?)",
            r"^(find\s+(me\s+)?(documents?\s+)?(about\s+|on\s+|related\s+to\s+)?)",
            r"^(look\s+for\s+(documents?\s+)?(about\s+)?)",
            r"^(search\s+(my\s+)?(knowledge\s+base|documents?)\s+(for\s+|about\s+)?)",
            r"^(show\s+me\s+(documents?\s+)?(about\s+|on\s+)?)",
            r"^(what\s+documents?\s+.*?(about\s+|on\s+))",
        ]
        
        query = user_input.strip()
        
        for pattern in patterns_to_remove:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()
        
        # Remove trailing question marks and clean up
        query = re.sub(r"[?!.]*$", "", query).strip()
        
        # If query is empty or too short, use original input
        if len(query) < 2:
            query = user_input
        
        return query
    
    async def _perform_document_search(self, query: str, max_results: int = 10) -> Optional[Dict]:
        """Perform the actual document search using TypeSense."""
        
        if not self.typesense_client:
            logger.error("TypeSense client not available")
            return None
        
        try:
            search_parameters = {
                'q': query,
                'query_by': 'title,content,description,tags',
                'per_page': max_results,
                'highlight_full_fields': 'title,content,description',
                'snippet_threshold': 30,
                'num_typos': 2,
                'prefix': True,
                'sort_by': '_text_match:desc',
                'facet_by': 'category,tags,file_type'
            }
            
            results = self.typesense_client.collections[TYPESENSE_COLLECTION_NAME].documents.search(search_parameters)
            logger.info(f"TypeSense search found {results.get('found', 0)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error performing TypeSense search: {e}")
            return None
    
    def _generate_search_response(self, query: str, results: Dict) -> str:
        """Generate a natural language response about the search results."""
        
        total_found = results.get('found', 0)
        hits = results.get('hits', [])
        
        if total_found == 0:
            return f"I couldn't find any documents matching '{query}' in your knowledge base. You might want to try different keywords or check if the documents are properly indexed."
        
        response_parts = [
            f"I found {total_found} document{'s' if total_found != 1 else ''} matching '{query}' in your knowledge base."
        ]
        
        if hits:
            response_parts.append(f"Here are the top {len(hits)} results:")
            
            # Add brief descriptions of top results
            for i, hit in enumerate(hits[:3], 1):
                doc = hit['document']
                title = doc.get('title', 'Untitled Document')
                snippet = doc.get('content', '')[:100] + '...' if len(doc.get('content', '')) > 100 else doc.get('content', '')
                response_parts.append(f"{i}. **{title}** - {snippet}")
        
        response_parts.append("You can click on any document below to open it in a new window.")
        
        return "\n\n".join(response_parts)
    
    def _create_search_results_artifact(self, query: str, results: Dict) -> Dict:
        """Create a structured search results artifact."""
        
        hits = results.get('hits', [])
        facets = results.get('facet_counts', [])
        
        # Format search results for the frontend
        formatted_results = []
        for hit in hits:
            doc = hit['document']
            highlight = hit.get('highlight', {})
            
            # Extract highlighted snippets
            title_highlight = highlight.get('title', {}).get('snippet', doc.get('title', 'Untitled'))
            content_snippet = highlight.get('content', {}).get('snippet', doc.get('content', ''))[:200] + '...'
            
            result_item = {
                "id": doc.get('id', ''),
                "title": doc.get('title', 'Untitled Document'),
                "titleHighlight": title_highlight,
                "description": doc.get('description', content_snippet),
                "contentSnippet": content_snippet,
                "category": doc.get('category', 'General'),
                "tags": doc.get('tags', []),
                "fileType": doc.get('file_type', 'document'),
                "createdAt": doc.get('created_at', ''),
                "url": doc.get('url', ''),
                "filePath": doc.get('file_path', ''),
                "score": hit.get('text_match', 1.0),
                "metadata": {
                    "size": doc.get('file_size', 0),
                    "lastModified": doc.get('last_modified', ''),
                    "author": doc.get('author', ''),
                    "language": doc.get('language', 'en')
                }
            }
            formatted_results.append(result_item)
        
        # Format facets for filtering
        formatted_facets = {}
        for facet in facets:
            field_name = facet.get('field_name', '')
            counts = facet.get('counts', [])
            formatted_facets[field_name] = [
                {"value": item.get('value', ''), "count": item.get('count', 0)}
                for item in counts
            ]
        
        artifact_data = {
            "query": query,
            "totalResults": results.get('found', 0),
            "resultsShown": len(formatted_results),
            "searchTime": results.get('search_time_ms', 0),
            "results": formatted_results,
            "facets": formatted_facets,
            "searchParams": {
                "collection": TYPESENSE_COLLECTION_NAME,
                "queryBy": "title,content,description,tags"
            }
        }
        
        return {
            "type": "document_search_results",
            "title": f"Search Results: {query}",
            "content": json.dumps(artifact_data, indent=2),
            "data": artifact_data,
            "template": "search_results_grid"
        }
    
    async def _handle_general_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Handle general TypeSense-related requests."""
        
        # Generate response using the base class method
        response_content = await self.generate_response(user_input, config=config)
        
        # Determine if we need to create artifacts
        artifacts = []
        response_lower = response_content.lower()
        
        if any(keyword in response_lower for keyword in ["search", "query", "index", "schema", "config"]):
            artifacts.append({
                "type": ArtifactType.CODE,
                "title": "TypeSense Configuration Script",
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
    
    def _generate_search_script(self, user_input: str, response_content: str) -> str:
        """Generate a search script based on the request."""
        
        # Enhanced script template with real search functionality
        script_template = '''"""
TypeSense Search Script
Generated based on: {user_input}
"""

import typesense
import json
from datetime import datetime
import os
from typing import Dict, List, Any, Optional

# TypeSense Configuration
TYPESENSE_HOST = os.getenv("TYPESENSE_HOST", "localhost")
TYPESENSE_PORT = os.getenv("TYPESENSE_PORT", "8108")
TYPESENSE_API_KEY = os.getenv("TYPESENSE_API_KEY", "xyz")
TYPESENSE_PROTOCOL = os.getenv("TYPESENSE_PROTOCOL", "http")
TYPESENSE_COLLECTION_NAME = os.getenv("TYPESENSE_COLLECTION_NAME", "documents")

class EnhancedTypeSenseManager:
    def __init__(self):
        self.client = typesense.Client({{
            'nodes': [{{
                'host': TYPESENSE_HOST,
                'port': TYPESENSE_PORT,
                'protocol': TYPESENSE_PROTOCOL
            }}],
            'api_key': TYPESENSE_API_KEY,
            'connection_timeout_seconds': 5
        }})
    
    def intelligent_search(self, query: str, max_results: int = 10) -> Optional[Dict]:
        """Perform intelligent document search with enhanced features."""
        search_parameters = {{
            'q': query,
            'query_by': 'title,content,description,tags',
            'per_page': max_results,
            'highlight_full_fields': 'title,content,description',
            'snippet_threshold': 30,
            'num_typos': 2,
            'prefix': True,
            'sort_by': '_text_match:desc',
            'facet_by': 'category,tags,file_type'
        }}
        
        try:
            results = self.client.collections[TYPESENSE_COLLECTION_NAME].documents.search(search_parameters)
            return self._format_search_results(results)
        except Exception as e:
            print(f"Search error: {{e}}")
            return None
    
    def _format_search_results(self, results: Dict) -> Dict:
        """Format search results for better presentation."""
        formatted = {{
            "total_found": results.get('found', 0),
            "search_time_ms": results.get('search_time_ms', 0),
            "documents": []
        }}
        
        for hit in results.get('hits', []):
            doc = hit['document']
            highlight = hit.get('highlight', {{}})
            
            formatted_doc = {{
                "id": doc.get('id'),
                "title": doc.get('title', 'Untitled'),
                "description": doc.get('description', ''),
                "category": doc.get('category', 'General'),
                "tags": doc.get('tags', []),
                "file_type": doc.get('file_type', 'document'),
                "url": doc.get('url', ''),
                "score": hit.get('text_match', 0),
                "highlights": {{
                    "title": highlight.get('title', {{}}).get('snippet', ''),
                    "content": highlight.get('content', {{}}).get('snippet', '')
                }}
            }}
            formatted['documents'].append(formatted_doc)
        
        return formatted
    
    def create_document_schema(self):
        """Create an enhanced document schema."""
        schema = {{
            'name': TYPESENSE_COLLECTION_NAME,
            'fields': [
                {{'name': 'id', 'type': 'string'}},
                {{'name': 'title', 'type': 'string'}},
                {{'name': 'content', 'type': 'string'}},
                {{'name': 'description', 'type': 'string', 'optional': True}},
                {{'name': 'category', 'type': 'string', 'facet': True}},
                {{'name': 'tags', 'type': 'string[]', 'facet': True}},
                {{'name': 'file_type', 'type': 'string', 'facet': True}},
                {{'name': 'created_at', 'type': 'int64'}},
                {{'name': 'last_modified', 'type': 'int64', 'optional': True}},
                {{'name': 'author', 'type': 'string', 'optional': True}},
                {{'name': 'file_size', 'type': 'int32', 'optional': True}},
                {{'name': 'url', 'type': 'string', 'optional': True}},
                {{'name': 'file_path', 'type': 'string', 'optional': True}},
                {{'name': 'language', 'type': 'string', 'optional': True, 'facet': True}}
            ],
            'default_sorting_field': 'created_at'
        }}
        
        try:
            # Delete existing collection if it exists
            self.client.collections[TYPESENSE_COLLECTION_NAME].delete()
        except:
            pass
        
        result = self.client.collections.create(schema)
        print(f"Created enhanced document collection: {{TYPESENSE_COLLECTION_NAME}}")
        return result

# Example usage
if __name__ == "__main__":
    manager = EnhancedTypeSenseManager()
    
    # Example search
    query = "machine learning algorithms"
    results = manager.intelligent_search(query)
    
    if results:
        print(f"Found {{results['total_found']}} documents in {{results['search_time_ms']}}ms")
        for doc in results['documents'][:5]:
            print(f"\\n📄 {{doc['title']}}")
            print(f"   Category: {{doc['category']}}")
            print(f"   Score: {{doc['score']:.2f}}")
            if doc['highlights']['content']:
                print(f"   Snippet: ...{{doc['highlights']['content']}}...")
'''
        
        return script_template.format(user_input=user_input)

    async def get_capabilities(self) -> List[str]:
        """Return list of agent capabilities."""
        return [
            "intelligent_document_search",
            "structured_search_results",
            "interactive_document_listing",
            "full_text_search",
            "faceted_search",
            "search_analytics",
            "document_indexing",
            "auto_complete",
            "search_suggestions", 
            "real_time_search",
            "schema_management"
        ] 