"""
Multi-Agent Chat Service
Provides both console and WebSocket interfaces for the multi-agent system.
"""

from dotenv import load_dotenv
load_dotenv()

from llama_index.llms.openai import OpenAI
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    AgentOutput,
    ToolCall,
    ToolCallResult,
    FunctionAgent,
    AgentInput,
    AgentStream,
)
from llama_index.core.memory import Memory
from llama_index.core.llms import ChatMessage
import os
import asyncio
import json
import typesense
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from llama_index.core.tools import FunctionTool
import logging
import structlog
import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Initialize OpenAI LLM
llm = OpenAI(model="gpt-4o-mini", temperature=0.7)

# Database configuration for memory (using your existing database)
DB_CONFIG = {
    'host': 'localhost',
    'database': 'standard_db_eassist',
    'user': 'postgres',
    'password': '0yq5h3to9',
    'port': 5432
}

# Typesense configuration
TYPESENSE_CONFIG = {
    'nodes': [{
        'host': os.getenv('TYPESENSE_HOST', 'localhost'),
        'port': int(os.getenv('TYPESENSE_PORT', '8108')),
        'protocol': os.getenv('TYPESENSE_PROTOCOL', 'http')
    }],
    'api_key': os.getenv('TYPESENSE_API_KEY', 'your-api-key'),
    'connection_timeout_seconds': 10
}

TYPESENSE_COLLECTION = os.getenv('TYPESENSE_COLLECTION_NAME', 'documents')

try:
    typesense_client = typesense.Client(TYPESENSE_CONFIG)
    logger.info("Typesense client initialized for chat service")
except Exception as e:
    logger.error("Failed to initialize Typesense client for chat", error=str(e))
    typesense_client = None


class ChatEvent:
    """Structured chat event for streaming"""
    
    def __init__(self, event_type: str, content: str, agent: str = None, tool: str = None, mode: str = "output"):
        self.timestamp = datetime.now().isoformat()
        self.user = agent or "system"
        self.tool = tool or "none"
        self.mode = mode  # thinking|output|error
        self.event_type = event_type
        self.content = content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "user": self.user,
            "tool": self.tool,
            "mode": self.mode,
            "event_type": self.event_type,
            "content": self.content
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())


class DatabaseChatMemory:
    """Enhanced memory using PostgreSQL database for chat"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.connection = None
        self._connect()
        self._ensure_tables()
    
    def _connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logger.info("Chat database connection established", session_id=self.session_id)
        except Exception as e:
            logger.error("Chat database connection failed", error=str(e), session_id=self.session_id)
            self.connection = None
    
    def _ensure_tables(self):
        """Ensure chat memory tables exist"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                # Create chat history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        role VARCHAR(50) NOT NULL,
                        content TEXT NOT NULL,
                        agent_name VARCHAR(100),
                        tool_used VARCHAR(100),
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create user facts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_facts (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        fact TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(session_id, fact)
                    )
                """)
                
                # Create chat sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id SERIAL PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        user_name VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                self.connection.commit()
                logger.info("Chat database tables ensured", session_id=self.session_id)
        except Exception as e:
            logger.error("Failed to create chat tables", error=str(e), session_id=self.session_id)
    
    def add_message(self, role: str, content: str, agent_name: str = None, tool_used: str = None):
        """Add message to chat history"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO chat_history (session_id, role, content, agent_name, tool_used)
                    VALUES (%s, %s, %s, %s, %s)
                """, (self.session_id, role, content, agent_name, tool_used))
                
                # Update session activity
                cursor.execute("""
                    INSERT INTO chat_sessions (session_id, last_activity)
                    VALUES (%s, CURRENT_TIMESTAMP)
                    ON CONFLICT (session_id) 
                    DO UPDATE SET last_activity = CURRENT_TIMESTAMP
                """, (self.session_id,))
                
                self.connection.commit()
        except Exception as e:
            logger.error("Failed to add chat message", error=str(e), session_id=self.session_id)
    
    def get_recent_messages(self, limit: int = 20) -> List[Dict]:
        """Get recent chat messages"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT role, content, agent_name, tool_used, timestamp 
                    FROM chat_history 
                    WHERE session_id = %s 
                    ORDER BY timestamp DESC 
                    LIMIT %s
                """, (self.session_id, limit))
                return list(reversed(cursor.fetchall()))
        except Exception as e:
            logger.error("Failed to get chat messages", error=str(e), session_id=self.session_id)
            return []
    
    def add_user_fact(self, fact: str):
        """Add a fact about the user"""
        if not self.connection:
            return
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_facts (session_id, fact)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id, fact) DO NOTHING
                """, (self.session_id, fact))
                self.connection.commit()
        except Exception as e:
            logger.error("Failed to add user fact", error=str(e), session_id=self.session_id)
    
    def get_user_facts(self) -> List[str]:
        """Get user facts"""
        if not self.connection:
            return []
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT fact FROM user_facts 
                    WHERE session_id = %s 
                    ORDER BY timestamp DESC
                """, (self.session_id,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error("Failed to get user facts", error=str(e), session_id=self.session_id)
            return []


# Enhanced search function for chat
async def search_documents_chat(ctx: Context, query: str, max_results: int = 5) -> str:
    """
    Search function optimized for chat service
    """
    logger.info("Starting document search", query=query, max_results=max_results)
    
    try:
        if not typesense_client:
            error_msg = "❌ Typesense client not available"
            logger.error(error_msg)
            return error_msg
        
        # Test connection
        try:
            collections = typesense_client.collections.retrieve()
            logger.info("Typesense connection successful", collections_count=len(collections))
        except Exception as conn_error:
            error_msg = f"❌ Typesense connection failed: {str(conn_error)}"
            logger.error(error_msg, error=str(conn_error))
            return error_msg
        
        # Perform search
        search_params = {
            'q': query,
            'query_by': 'title,description,summary,content',
            'per_page': max_results,
            'page': 1,
            'sort_by': '_text_match:desc',
            'highlight_full_fields': 'title,description,summary'
        }
        
        logger.info("Executing search", params=search_params)
        results = typesense_client.collections[TYPESENSE_COLLECTION].documents.search(search_params)
        
        if not results.get('hits'):
            no_results_msg = f"📭 No documents found for query: '{query}'"
            logger.warning(no_results_msg)
            return no_results_msg
        
        # Store in context for later retrieval
        current_state = await ctx.get("state", {})
        current_state["last_search_results"] = results
        current_state["last_search_query"] = query
        
        documents = []
        for hit in results['hits']:
            doc = hit['document']
            documents.append({
                'id': doc.get('id', 'Unknown'),
                'title': doc.get('title', 'Untitled'),
                'type': doc.get('type', 'document'),
                'score': hit.get('text_match', 0),
                'summary': doc.get('summary', 'No summary available')[:100] + '...',
                'raw_data': doc
            })
        
        current_state["search_documents"] = documents
        await ctx.set("state", current_state)
        
        # Format results
        formatted_results = [f"🎯 Found {len(documents)} documents for '{query}':\n"]
        
        for i, doc in enumerate(documents, 1):
            full_doc = doc['raw_data']
            result = f"""
📄 Document {i}:
   • Title: {full_doc.get('title', 'Untitled')}
   • Type: {full_doc.get('type', 'document')}
   • Description: {full_doc.get('description', 'No description available')}
   • Summary: {full_doc.get('summary', 'No summary available')[:200]}...
   • File: {full_doc.get('original_filename', 'Unknown')}
   • Score: {doc['score']:.2f}
   • Document ID: {doc['id']}
"""
            formatted_results.append(result)
        
        final_result = "\n".join(formatted_results)
        logger.info("Search completed successfully", result_length=len(final_result))
        
        return final_result
        
    except Exception as e:
        error_msg = f"❌ Error searching documents: {str(e)}"
        logger.error("Search failed", error=str(e), query=query)
        return error_msg


class MultiAgentChatService:
    """Main chat service for both console and WebSocket interfaces"""
    
    def __init__(self):
        self.chat_agent = None
        self.knowledge_agent = None
        self.workflow = None
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize the chat agents"""
        self.chat_agent = FunctionAgent(
            name="ChatAgent",
            description="General conversational agent",
            system_prompt=(
                "You are the ChatAgent, a helpful assistant. "
                "When users ask about documents or search, hand off to KnowledgeBaseAgent. "
                "Always mention the user's name (Roniel Nuqui) in responses when appropriate. "
                "You have access to enhanced database memory for user facts and chat history."
            ),
            llm=llm,
            tools=[],
            can_handoff_to=["KnowledgeBaseAgent"],
        )
        
        self.knowledge_agent = FunctionAgent(
            name="KnowledgeBaseAgent", 
            description="Document search and analysis agent",
            system_prompt=(
                "You are the KnowledgeBaseAgent that specializes in searching documents. "
                "IMPORTANT: When users request document searches: "
                "1. Use search_documents_chat to find documents "
                "2. Present the complete tool result exactly as returned "
                "3. Do NOT summarize or modify the search results "
                "Always mention the user's name (Roniel Nuqui) when appropriate. "
                "You provide comprehensive document search and analysis."
            ),
            llm=llm,
            tools=[search_documents_chat],
            can_handoff_to=["ChatAgent"],
        )
        
        # Create workflow
        self.workflow = AgentWorkflow(
            agents=[self.chat_agent, self.knowledge_agent],
            root_agent=self.chat_agent.name,
            initial_state={
                "last_search_results": {},
                "last_search_query": "",
                "search_documents": [],
            },
        )
        
        logger.info("Multi-agent chat service initialized")
    
    async def process_message_stream(
        self, 
        message: str, 
        session_id: str,
        emit_event_callback: Optional[callable] = None
    ) -> AsyncGenerator[ChatEvent, None]:
        """
        Process message and yield streaming events
        """
        logger.info("Processing message", message=message[:100], session_id=session_id)
        
        # Initialize database memory
        db_memory = DatabaseChatMemory(session_id)
        
        # Initialize LlamaIndex memory
        memory = Memory.from_defaults(
            session_id=session_id,
            token_limit=8000,
            chat_history_token_ratio=0.7
        )
        
        # Add to database memory
        db_memory.add_message("user", message)
        
        # Extract facts about user (simple keyword detection)
        if "my name is" in message.lower():
            words = message.split()
            try:
                name_idx = words.index("is") + 1
                if name_idx < len(words):
                    name = words[name_idx].strip(".,!?")
                    db_memory.add_user_fact(f"User name is {name}")
                    logger.info("Extracted user name", name=name, session_id=session_id)
            except (ValueError, IndexError):
                pass
        
        # Send processing start event
        event = ChatEvent("processing_start", "🤖 Processing your request...", mode="thinking")
        if emit_event_callback:
            await emit_event_callback(event)
        yield event
        
        try:
            # Run workflow
            handler = self.workflow.run(user_msg=message, memory=memory)
            
            current_agent = None
            
            # Stream events
            async for workflow_event in handler.stream_events():
                # Agent switching
                if (
                    hasattr(workflow_event, "current_agent_name")
                    and workflow_event.current_agent_name != current_agent
                ):
                    current_agent = workflow_event.current_agent_name
                    event = ChatEvent(
                        "agent_switch",
                        f"{current_agent} is handling your request...",
                        agent=current_agent,
                        mode="thinking"
                    )
                    if emit_event_callback:
                        await emit_event_callback(event)
                    yield event
                
                # Agent output
                elif isinstance(workflow_event, AgentOutput):
                    if workflow_event.response.content:
                        event = ChatEvent(
                            "agent_response",
                            workflow_event.response.content,
                            agent=current_agent or "system",
                            mode="output"
                        )
                        if emit_event_callback:
                            await emit_event_callback(event)
                        yield event
                        
                    if workflow_event.tool_calls:
                        for tool_call in workflow_event.tool_calls:
                            event = ChatEvent(
                                "tool_call",
                                f"Using tool: {tool_call.tool_name}",
                                agent=current_agent or "system",
                                tool=tool_call.tool_name,
                                mode="thinking"
                            )
                            if emit_event_callback:
                                await emit_event_callback(event)
                            yield event
                
                # Tool results
                elif isinstance(workflow_event, ToolCallResult):
                    if workflow_event.tool_output:
                        event = ChatEvent(
                            "tool_result",
                            str(workflow_event.tool_output),
                            agent=current_agent or "system",
                            tool=workflow_event.tool_name,
                            mode="output"
                        )
                        if emit_event_callback:
                            await emit_event_callback(event)
                        yield event
                
                # Streaming tokens
                elif isinstance(workflow_event, AgentStream):
                    event = ChatEvent(
                        "stream_token",
                        workflow_event.delta,
                        agent=current_agent or "system",
                        mode="output"
                    )
                    if emit_event_callback:
                        await emit_event_callback(event)
                    yield event
            
            # Get final result
            result = await handler
            
            # Add to database memory
            db_memory.add_message("assistant", str(result), current_agent)
            
            # Send completion
            event = ChatEvent(
                "processing_complete",
                "✅ Request completed successfully",
                mode="thinking"
            )
            if emit_event_callback:
                await emit_event_callback(event)
            yield event
            
        except Exception as e:
            logger.error("Error processing message", error=str(e), session_id=session_id)
            error_event = ChatEvent(
                "error",
                f"❌ Error: {str(e)}",
                mode="error"
            )
            if emit_event_callback:
                await emit_event_callback(error_event)
            yield error_event
    
    async def process_message_simple(self, message: str, session_id: str) -> str:
        """
        Simple message processing without streaming (for basic console use)
        """
        try:
            final_response = ""
            async for event in self.process_message_stream(message, session_id):
                if event.event_type == "agent_response":
                    final_response = event.content
                elif event.event_type == "tool_result":
                    final_response = event.content
            
            return final_response or "No response generated"
            
        except Exception as e:
            logger.error("Error in simple message processing", error=str(e))
            return f"❌ Error: {str(e)}"


# Global chat service instance
chat_service = MultiAgentChatService() 