"""
Agent Orchestrator - LangGraph-based orchestration system for specialized agents.
Based on LangGraph agentic RAG best practices with PostgreSQL memory.
Implements short-term (workflow) and long-term (persistent) memory patterns.
"""

import asyncio
import uuid
import time
from typing import Dict, Any, List, Optional, TypedDict
from typing_extensions import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.agents.base_agent import AgentResponse, ArtifactType
from app.agents.agents.code_agent import CodeAgent
from app.agents.agents.document_agent import DocumentAgent
from app.agents.agents.general_agent import GeneralAgent
from app.agents.agents.minio_agent import MinIOAgent
from app.agents.agents.typesense_agent import TypeSenseAgent
from app.agents.agents.qdrant_agent import QdrantAgent
from app.agents.agents.file_display_agent import FileDisplayAgent
from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.db.memory import PostgresChatMemory

logger = get_logger(__name__)
settings = get_settings()


def serialize_artifacts_for_db(artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Serialize artifacts for database storage by converting ArtifactType enums to strings.
    This fixes the 'Object of type ArtifactType is not JSON serializable' error.
    """
    if not artifacts:
        return []
    
    serialized_artifacts = []
    for artifact in artifacts:
        # Create a copy to avoid modifying the original
        serialized_artifact = artifact.copy()
        
        # Convert ArtifactType enum to string if present
        if 'type' in serialized_artifact and isinstance(serialized_artifact['type'], ArtifactType):
            serialized_artifact['type'] = serialized_artifact['type'].value
        
        # Handle nested data that might contain ArtifactType
        if 'data' in serialized_artifact and isinstance(serialized_artifact['data'], dict):
            data_copy = serialized_artifact['data'].copy()
            for key, value in data_copy.items():
                if isinstance(value, ArtifactType):
                    data_copy[key] = value.value
            serialized_artifact['data'] = data_copy
        
        # Handle artifact types in metadata
        if 'metadata' in serialized_artifact and isinstance(serialized_artifact['metadata'], dict):
            metadata_copy = serialized_artifact['metadata'].copy()
            for key, value in metadata_copy.items():
                if isinstance(value, ArtifactType):
                    metadata_copy[key] = value.value
                elif isinstance(value, list):
                    # Handle lists that might contain ArtifactType
                    metadata_copy[key] = [item.value if isinstance(item, ArtifactType) else item for item in value]
            serialized_artifact['metadata'] = metadata_copy
        
        serialized_artifacts.append(serialized_artifact)
    
    return serialized_artifacts


class MessagesState(TypedDict):
    """
    Enhanced state for the agent orchestration workflow following LangGraph best practices.
    Implements both short-term (in-workflow) and long-term (persistent) memory patterns.
    """
    # Short-term memory (current workflow)
    messages: Annotated[list, add_messages]  # Current conversation messages
    selected_agent: Optional[str]  # Selected agent for routing
    context: Dict[str, Any]  # Workflow context
    config: Dict[str, Any]  # Configuration parameters
    
    # Long-term memory integration
    session_id: Optional[str]  # Session identifier for persistence
    conversation_summary: Optional[str]  # Summary of long conversation history
    user_profile: Dict[str, Any]  # User preferences and profile
    agent_metadata: Dict[str, Any]  # Agent execution metadata
    
    # Memory management flags
    memory_loaded: bool  # Flag indicating if long-term memory was loaded
    should_summarize: bool  # Flag to trigger conversation summarization
    last_activity: Optional[str]  # Timestamp of last activity


class AgentOrchestrator:
    """
    Enhanced LangGraph-based agent orchestrator with sophisticated memory management.
    Implements modern memory patterns: short-term (workflow state) + long-term (PostgreSQL).
    """
    
    def __init__(self):
        # Initialize specialized agents
        self.agents = {
            "general": GeneralAgent(),
            "code": CodeAgent(),
            "document": DocumentAgent(),
            "minio": MinIOAgent(),
            "typesense": TypeSenseAgent(),
            "qdrant": QdrantAgent(),
            "file_display": FileDisplayAgent(),
        }
        
        # Initialize PostgreSQL memory system
        self.memory = PostgresChatMemory()
        
        # Memory configuration
        self.max_short_term_messages = 10  # Keep recent messages in workflow state
        self.max_long_term_messages = 50   # Limit when loading from database
        self.summarization_threshold = 30  # Trigger summary after N messages
        
        # Build LangGraph workflow with enhanced memory
        self.workflow = self._build_enhanced_workflow()
        
        logger.info("🧠 Agent Orchestrator initialized with enhanced memory system")
    
    def _build_enhanced_workflow(self) -> StateGraph:
        """Build the enhanced LangGraph workflow with proper memory management."""
        
        # Create the state graph with enhanced state
        workflow = StateGraph(MessagesState)
        
        # Add memory management nodes
        workflow.add_node("initialize_session", self._initialize_session)
        workflow.add_node("load_long_term_memory", self._load_long_term_memory)
        workflow.add_node("route_request", self._route_request)
        workflow.add_node("manage_short_term_memory", self._manage_short_term_memory)
        
        # Add agent execution nodes
        workflow.add_node("execute_general", self._execute_general)
        workflow.add_node("execute_code", self._execute_code)
        workflow.add_node("execute_document", self._execute_document)
        workflow.add_node("execute_minio", self._execute_minio)
        workflow.add_node("execute_typesense", self._execute_typesense)
        workflow.add_node("execute_qdrant", self._execute_qdrant)
        workflow.add_node("execute_file_display", self._execute_file_display)
        
        # Add memory persistence nodes
        workflow.add_node("save_long_term_memory", self._save_long_term_memory)
        workflow.add_node("update_conversation_summary", self._update_conversation_summary)
        workflow.add_node("finalize_session", self._finalize_session)
        
        # Build workflow edges
        workflow.add_edge(START, "initialize_session")
        workflow.add_edge("initialize_session", "load_long_term_memory")
        workflow.add_edge("load_long_term_memory", "manage_short_term_memory")
        workflow.add_edge("manage_short_term_memory", "route_request")
        
        # Conditional routing based on selected agent
        workflow.add_conditional_edges(
            "route_request",
            lambda state: f"execute_{state['selected_agent']}",
            {
                "execute_general": "execute_general",
                "execute_code": "execute_code",
                "execute_document": "execute_document",
                "execute_minio": "execute_minio",
                "execute_typesense": "execute_typesense",
                "execute_qdrant": "execute_qdrant",
                "execute_file_display": "execute_file_display",
            }
        )
        
        # All execution nodes lead to memory persistence
        for agent_name in self.agents.keys():
            workflow.add_edge(f"execute_{agent_name}", "save_long_term_memory")
        
        # Memory finalization flow
        workflow.add_edge("save_long_term_memory", "update_conversation_summary")
        workflow.add_edge("update_conversation_summary", "finalize_session")
        workflow.add_edge("finalize_session", END)
        
        return workflow.compile()
    
    async def _initialize_session(self, session_id: str = None, user_id: str = None, config: Dict[str, Any] = None) -> Any:
        """Initialize or validate session for memory management."""
        try:
            # Create new session if none provided
            if not session_id:
                session = await self.memory.create_session(
                    title="New Conversation",
                    user_id=user_id or "anonymous",
                    session_type="chat",
                    config=config or {},
                    context={}
                )
                logger.info(f"🆕 MEMORY: Created new session {session.id}")
                return session
            else:
                # Validate existing session
                if isinstance(session_id, str):
                    try:
                        session_uuid = uuid.UUID(session_id)
                        session = await self.memory.get_session(session_uuid)
                        if session:
                            logger.info(f"🔗 MEMORY: Using existing session {session_id}")
                            return session
                        else:
                            logger.warning(f"⚠️ Session {session_id} not found, creating new one")
                    except ValueError:
                        logger.warning(f"⚠️ Invalid session ID format: {session_id}")
                        
                # Invalid or not found session ID, create new one
                session = await self.memory.create_session(
                    title="New Conversation",
                    user_id=user_id or "anonymous",
                    session_type="chat",
                    config=config or {}
                )
                logger.info(f"🆕 MEMORY: Created new session due to invalid/missing session")
                return session
            
        except Exception as e:
            logger.error(f"❌ SESSION INIT ERROR: {e}")
            # Create minimal session
            session = await self.memory.create_session(
                title="Error Recovery Session",
                user_id=user_id or "anonymous",
                session_type="chat"
            )
            return session

    async def _load_memory_context(self, session_id: str) -> Dict[str, Any]:
        """Load conversation history and context from database."""
        try:
            session_uuid = uuid.UUID(session_id)
            
            # Load conversation history
            history = await self.memory.get_conversation_history(
                session_uuid, 
                limit=20  # Limit for context
            )
            
            # Load session statistics
            stats = await self.memory.get_session_stats(session_uuid)
            
            # Load session details
            session_details = await self.memory.get_session(session_uuid)
            
            memory_context = {
                "conversation_history": history,
                "session_stats": stats,
                "session_details": session_details,
                "conversation_summary": session_details.context.get("summary", "") if session_details and session_details.context else "",
                "user_profile": session_details.config.get("user_profile", {}) if session_details and session_details.config else {}
            }
            
            logger.info(f"🧠 MEMORY: Loaded {len(history)} messages for session {session_id}")
            return memory_context
            
        except Exception as e:
            logger.error(f"❌ MEMORY LOAD ERROR: {e}")
            return {
                "conversation_history": [],
                "session_stats": {},
                "session_details": None,
                "conversation_summary": "",
                "user_profile": {}
            }

    async def _route_to_agent(self, user_input: str, memory_context: Dict[str, Any]) -> tuple:
        """Route to the best agent based on input and memory context."""
        user_input_lower = user_input.lower()
        conversation_summary = memory_context.get("conversation_summary", "").lower()
        
        # Context-aware routing scores
        routing_score = {}
        
        # Document Search keywords (highest priority for TypeSense agent)
        search_keywords = [
            "search", "find", "look for", "search documents", "search knowledge base",
            "find documents", "search files", "document search", "knowledge search",
            "search my documents", "find in documents", "search content", "search for"
        ]
        routing_score["typesense"] = sum(2 for kw in search_keywords if kw in user_input_lower)
        
        # Additional boost for explicit document/knowledge base searches
        if any(phrase in user_input_lower for phrase in [
            "search documents", "find documents", "search knowledge base",
            "search my documents", "document search", "search for documents",
            "find in knowledge base", "search files", "search content"
        ]):
            routing_score["typesense"] += 5
        
        # Code-related keywords
        code_keywords = ["code", "python", "javascript", "sql", "function", "class", "variable",
                       "algorithm", "programming", "debug", "script", "api", "json", "recursive"]
        routing_score["code"] = sum(1 for kw in code_keywords if kw in user_input_lower)
        if "programming" in conversation_summary or "code" in conversation_summary:
            routing_score["code"] += 2  # Boost if previous context is code-related
        
        # Document creation keywords
        doc_creation_keywords = ["write", "create document", "generate report", "draft", "compose"]
        routing_score["document"] = sum(1 for kw in doc_creation_keywords if kw in user_input_lower)
        
        # MinIO/storage keywords
        storage_keywords = ["minio", "storage", "bucket", "upload", "download", "s3", "object storage"]
        routing_score["minio"] = sum(1 for kw in storage_keywords if kw in user_input_lower)
        
        # Qdrant/vector keywords
        vector_keywords = ["vector", "qdrant", "embedding", "similarity", "semantic"]
        routing_score["qdrant"] = sum(1 for kw in vector_keywords if kw in user_input_lower)
        
        # File display keywords (but not search - that goes to TypeSense)
        file_keywords = ["display file", "show file", "read file", "file content", "view file"]
        routing_score["file_display"] = sum(1 for kw in file_keywords if kw in user_input_lower)
        
        # General conversation (default with lower score)
        routing_score["general"] = 1  # Default score
        
        # Select agent with highest score
        selected_agent_name = max(routing_score, key=routing_score.get)
        
        # Override if no specific keywords found (except for search which should go to TypeSense)
        if routing_score[selected_agent_name] <= 1 and selected_agent_name != "general":
            # Check if it's a potential search request that didn't score high enough
            if any(word in user_input_lower for word in ["search", "find", "look for"]):
                selected_agent_name = "typesense"
            else:
                selected_agent_name = "general"
        
        # Get the actual agent instance
        agent_map = {
            "general": self.agents["general"],
            "code": self.agents["code"],
            "document": self.agents["document"],
            "minio": self.agents["minio"],
            "typesense": self.agents["typesense"],
            "qdrant": self.agents["qdrant"],
            "file_display": self.agents["file_display"]
        }
        
        selected_agent = agent_map.get(selected_agent_name, self.agents["general"])
        score = routing_score[selected_agent_name]
        
        return selected_agent, score

    async def _save_long_term_memory(self, session_id: str, user_input: str, agent_response: AgentResponse, selected_agent: Any, user_id: str):
        """Save the conversation exchange to long-term memory."""
        try:
            session_uuid = uuid.UUID(session_id)
            
            # Save user message
            from langchain_core.messages import HumanMessage, AIMessage
            user_message = HumanMessage(content=user_input)
            
            await self.memory.add_message(
                session_id=session_uuid,
                message=user_message,
                agent_name="user",
                agent_metadata={
                    "user_id": user_id,
                    "timestamp": time.time()
                }
            )
            
            # Serialize artifacts to fix JSON serialization issues
            serialized_artifacts = serialize_artifacts_for_db(agent_response.artifacts)
            
            # Save AI response
            ai_message = AIMessage(
                content=agent_response.content,
                additional_kwargs={
                    "agent_name": selected_agent.name.lower(),
                    "agent_metadata": agent_response.metadata,
                    "artifacts": serialized_artifacts,  # Use serialized artifacts
                    "session_id": session_id
                }
            )
            
            await self.memory.add_message(
                session_id=session_uuid,
                message=ai_message,
                agent_name=selected_agent.name.lower(),
                agent_metadata={
                    "agent_name": selected_agent.name.lower(),
                    "timestamp": time.time(),
                    "user_profile": {},
                    "conversation_context": ""
                },
                artifacts=serialized_artifacts  # Use serialized artifacts
            )
            
            logger.info(f"💾 MEMORY: Saved exchange to session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ MEMORY SAVE ERROR: {e}")

    async def _finalize_session_context(self, session_id: str, memory_context: Dict[str, Any]):
        """Finalize session with any updates."""
        try:
            # This is a placeholder for session finalization logic
            # Could update session context, compute summaries, etc.
            logger.info(f"🏁 SESSION FINALIZED: {session_id}")
        except Exception as e:
            logger.error(f"❌ SESSION FINALIZE ERROR: {e}")

    async def _load_long_term_memory(self, state: MessagesState) -> MessagesState:
        """Load long-term memory from PostgreSQL database."""
        try:
            session_id = state.get("session_id")
            
            if session_id:
                session_uuid = uuid.UUID(session_id)
                
                # Load conversation history (long-term memory)
                history = await self.memory.get_conversation_history(
                    session_uuid, 
                    limit=self.max_long_term_messages
                )
                
                # Load session statistics for context
                stats = await self.memory.get_session_stats(session_uuid)
                
                # Load session details
                session_details = await self.memory.get_session(session_uuid)
                
                if history:
                    # Separate current user message from history
                    current_messages = state.get("messages", [])
                    
                    # Combine history with current messages
                    all_messages = history + current_messages
                    state["messages"] = all_messages
                    
                    # Set conversation summary if available
                    if session_details and session_details.context:
                        state["conversation_summary"] = session_details.context.get("summary", "")
                    
                    # Set user profile if available
                    if session_details and session_details.config:
                        state["user_profile"] = session_details.config.get("user_profile", {})
                    
                    logger.info(f"🧠 LONG-TERM MEMORY: Loaded {len(history)} messages, {stats['total_tokens']} tokens")
                
                state["memory_loaded"] = True
                
                # Check if summarization is needed
                if stats['total_messages'] > self.summarization_threshold:
                    state["should_summarize"] = True
            
            return state
            
        except Exception as e:
            logger.error(f"❌ LONG-TERM MEMORY LOAD ERROR: {e}")
            state["memory_loaded"] = False
            return state
    
    async def _manage_short_term_memory(self, state: MessagesState) -> MessagesState:
        """Manage short-term memory within the workflow."""
        try:
            messages = state.get("messages", [])
            
            # Trim messages if too many for short-term processing
            if len(messages) > self.max_short_term_messages:
                # Keep conversation summary + recent messages
                summary = state.get("conversation_summary", "")
                recent_messages = messages[-self.max_short_term_messages:]
                
                # Add summary as system message if available
                if summary:
                    summary_message = SystemMessage(
                        content=f"Conversation summary: {summary}",
                        additional_kwargs={"type": "summary"}
                    )
                    trimmed_messages = [summary_message] + recent_messages
                else:
                    trimmed_messages = recent_messages
                
                state["messages"] = trimmed_messages
                logger.info(f"🔄 SHORT-TERM MEMORY: Trimmed to {len(trimmed_messages)} messages")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ SHORT-TERM MEMORY ERROR: {e}")
            return state
    
    async def _route_request(self, state: MessagesState) -> MessagesState:
        """Enhanced routing with memory context awareness."""
        try:
            messages = state.get("messages", [])
            if not messages:
                state["selected_agent"] = "general"
                return state
            
            # Get the latest user message
            user_message = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    user_message = msg.content
                    break
            
            if not user_message:
                state["selected_agent"] = "general"
                return state
            
            # Enhanced routing with conversation context
            user_input_lower = user_message.lower()
            conversation_context = state.get("conversation_summary", "").lower()
            
            # Context-aware routing - consider previous conversation
            routing_score = {}
            
            # Code-related keywords
            code_keywords = ["code", "python", "javascript", "sql", "function", "class", "variable",
                           "algorithm", "programming", "debug", "script", "api", "json", "recursive"]
            routing_score["code"] = sum(1 for kw in code_keywords if kw in user_input_lower)
            if "programming" in conversation_context or "code" in conversation_context:
                routing_score["code"] += 2  # Boost if previous context is code-related
            
            # Document-related keywords
            doc_keywords = ["document", "write", "report", "article", "guide", "documentation",
                          "manual", "tutorial", "readme", "specification"]
            routing_score["document"] = sum(1 for kw in doc_keywords if kw in user_input_lower)
            
            # MinIO/storage keywords
            storage_keywords = ["minio", "storage", "bucket", "upload", "download", "s3", "object storage"]
            routing_score["minio"] = sum(1 for kw in storage_keywords if kw in user_input_lower)
            
            # Search/Typesense keywords
            search_keywords = ["search", "typesense", "index", "query", "find", "lookup"]
            routing_score["typesense"] = sum(1 for kw in search_keywords if kw in user_input_lower)
            
            # Vector/Qdrant keywords
            vector_keywords = ["vector", "qdrant", "embedding", "similarity", "semantic"]
            routing_score["qdrant"] = sum(1 for kw in vector_keywords if kw in user_input_lower)
            
            # File display keywords
            file_keywords = ["file", "display", "show", "list", "directory", "folder"]
            routing_score["file_display"] = sum(1 for kw in file_keywords if kw in user_input_lower)
            
            # General conversation
            routing_score["general"] = 1  # Default score
            
            # Select agent with highest score
            selected_agent = max(routing_score, key=routing_score.get)
            
            # Override if no specific keywords found
            if routing_score[selected_agent] <= 1 and selected_agent != "general":
                selected_agent = "general"
            
            state["selected_agent"] = selected_agent
            logger.info(f"🎯 ENHANCED ROUTER: Selected '{selected_agent}' agent (score: {routing_score[selected_agent]})")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ ROUTING ERROR: {e}")
            state["selected_agent"] = "general"
            return state
    
    async def _update_conversation_summary(self, state: MessagesState) -> MessagesState:
        """Update conversation summary for long conversations."""
        try:
            if not state.get("should_summarize", False):
                return state
            
            session_id = state.get("session_id")
            if not session_id:
                return state
            
            # Generate conversation summary using recent messages
            messages = state.get("messages", [])
            recent_messages = messages[-10:]  # Last 10 messages for summary
            
            # Simple summarization (can be enhanced with LLM)
            summary_parts = []
            for msg in recent_messages:
                if isinstance(msg, HumanMessage):
                    summary_parts.append(f"User: {msg.content[:100]}...")
                elif isinstance(msg, AIMessage):
                    summary_parts.append(f"Assistant: {msg.content[:100]}...")
            
            summary = " | ".join(summary_parts[-4:])  # Keep last 4 exchanges
            state["conversation_summary"] = summary
            
            logger.info(f"📝 CONVERSATION SUMMARY: Updated for session {session_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ SUMMARY UPDATE ERROR: {e}")
            return state
    
    async def _finalize_session(self, state: MessagesState) -> MessagesState:
        """Finalize session with updated metadata."""
        try:
            session_id = state.get("session_id")
            
            if session_id:
                session_uuid = uuid.UUID(session_id)
                
                # Update session context with summary and metadata
                session_details = await self.memory.get_session(session_uuid)
                if session_details:
                    updated_context = session_details.context or {}
                    updated_context.update({
                        "summary": state.get("conversation_summary", ""),
                        "last_agent": state.get("selected_agent", ""),
                        "message_count": len(state.get("messages", []))
                    })
                    
                    # Note: We would need to add an update_session_context method to memory
                    # For now, just log the finalization
                    logger.info(f"🏁 SESSION FINALIZED: {session_id}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ SESSION FINALIZE ERROR: {e}")
            return state

    async def _execute_agent(self, agent_name: str, state: MessagesState) -> MessagesState:
        """Execute a specific agent with enhanced memory context."""
        try:
            messages = state.get("messages", [])
            if not messages:
                return state
            
            # Get latest user message
            user_input = None
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    user_input = msg.content
                    break
            
            if not user_input:
                return state
            
            agent = self.agents[agent_name]
            logger.info(f"🎯 EXECUTING: {agent_name} agent")
            
            # Enhanced context with memory information
            enhanced_context = state.get("context", {}).copy()
            enhanced_context.update({
                "conversation_summary": state.get("conversation_summary", ""),
                "user_profile": state.get("user_profile", {}),
                "session_id": state.get("session_id"),
                "previous_messages": len(messages) - 1  # Exclude current message
            })
            
            # Execute agent with enhanced context
            config = state.get("config", {})
            response = await agent.process_request(user_input, enhanced_context, config)
            
            if response.success:
                # Create AI message with enhanced metadata
                ai_message = AIMessage(
                    content=response.content,
                    additional_kwargs={
                        "agent_name": agent_name,
                        "agent_metadata": response.metadata,
                        "artifacts": response.artifacts,
                        "session_id": state.get("session_id")
                    }
                )
                state["messages"].append(ai_message)
                
                # Update agent metadata in state
                state["agent_metadata"][agent_name] = {
                    "last_response": response.content[:100],
                    "success": True,
                    "artifacts_count": len(response.artifacts)
                }
                
                logger.info(f"✅ AGENT {agent_name}: Success")
            else:
                # Add error message
                error_message = AIMessage(
                    content=f"Sorry, I encountered an error: {response.error}",
                    additional_kwargs={
                        "agent_name": agent_name,
                        "error": True,
                        "session_id": state.get("session_id")
                    }
                )
                state["messages"].append(error_message)
                
                logger.error(f"❌ AGENT {agent_name}: Failed - {response.error}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ ERROR executing {agent_name}: {e}")
            error_message = AIMessage(
                content=f"Sorry, I encountered an error while processing your request.",
                additional_kwargs={
                    "agent_name": agent_name,
                    "error": True,
                    "session_id": state.get("session_id")
                }
            )
            state["messages"].append(error_message)
            return state

    # Individual agent execution methods
    async def _execute_general(self, state: MessagesState) -> MessagesState:
        """Execute general agent."""
        return await self._execute_agent("general", state)
    
    async def _execute_code(self, state: MessagesState) -> MessagesState:
        """Execute code agent."""
        return await self._execute_agent("code", state)
    
    async def _execute_document(self, state: MessagesState) -> MessagesState:
        """Execute document agent."""
        return await self._execute_agent("document", state)
    
    async def _execute_minio(self, state: MessagesState) -> MessagesState:
        """Execute minio agent."""
        return await self._execute_agent("minio", state)
    
    async def _execute_typesense(self, state: MessagesState) -> MessagesState:
        """Execute typesense agent."""
        return await self._execute_agent("typesense", state)
    
    async def _execute_qdrant(self, state: MessagesState) -> MessagesState:
        """Execute qdrant agent."""
        return await self._execute_agent("qdrant", state)
    
    async def _execute_file_display(self, state: MessagesState) -> MessagesState:
        """Execute file display agent."""
        return await self._execute_agent("file_display", state)

    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Enhanced orchestrator with LangGraph memory integration."""
        try:
            logger.info(f"🚀 ENHANCED ORCHESTRATOR: Processing: {user_input[:100]}...")
            
            # Debug: Log incoming context and config
            logger.info(f"📋 DEBUG: Incoming context keys: {list(context.keys()) if context else 'None'}")
            logger.info(f"📋 DEBUG: Incoming config keys: {list(config.keys()) if config else 'None'}")
            
            # Extract session information from config (where WebSocket handler puts it)
            session_id = None
            user_id = "anonymous"
            
            if config:
                session_id = config.get("session_id")
                user_id = config.get("user_id", "anonymous")
            
            # Initialize session if needed
            session = await self._initialize_session(session_id, user_id, config)
            session_id = str(session.id)
            
            logger.info(f"🆔 DEBUG: Using session_id: {session_id}, user_id: {user_id}")
            
            # Load conversation memory and context
            memory_context = await self._load_memory_context(session_id)
            
            # Debug: Log memory context details
            logger.info(f"🧠 DEBUG: Memory context loaded - Messages: {len(memory_context.get('conversation_history', []))}")
            if memory_context.get('conversation_history'):
                for i, msg in enumerate(memory_context['conversation_history'][-3:]):  # Show last 3 messages
                    logger.info(f"   Message {i}: {msg.type} - {msg.content[:50]}...")
            
            # Select the best agent
            selected_agent, score = await self._route_to_agent(user_input, memory_context)
            logger.info(f"🎯 ENHANCED ROUTER: Selected '{selected_agent.name.lower()}' agent (score: {score})")
            
            # Process with selected agent including memory context
            logger.info(f"🎯 EXECUTING: {selected_agent.name.lower()} agent")
            
            # Prepare enhanced context with memory
            enhanced_context = (context or {}).copy()
            enhanced_context.update(memory_context)
            enhanced_context["session_id"] = session_id
            enhanced_context["user_id"] = user_id
            
            # Debug: Log what we're passing to the agent
            logger.info(f"📋 DEBUG: Enhanced context keys: {list(enhanced_context.keys())}")
            if enhanced_context.get('conversation_history'):
                logger.info(f"📋 DEBUG: Passing {len(enhanced_context['conversation_history'])} messages to agent")
            
            agent_response = await selected_agent.process_request(
                user_input, 
                context=enhanced_context, 
                config=config
            )
            
            if agent_response.success:
                logger.info(f"✅ AGENT {selected_agent.name.lower()}: Success")
                
                # Save to long-term memory
                await self._save_long_term_memory(
                    session_id, 
                    user_input, 
                    agent_response, 
                    selected_agent,
                    user_id
                )
                
                # Add enhanced metadata
                agent_response.metadata.update({
                    "primary_agent": selected_agent.name.lower(),
                    "orchestrator": "enhanced_langgraph",
                    "session_id": str(session_id),
                    "memory_loaded": True,
                    "message_count": len(memory_context.get('conversation_history', [])) + 2  # +2 for current exchange
                })
                
                # Finalize session context
                await self._finalize_session_context(session_id, memory_context)
                logger.info(f"🏁 SESSION FINALIZED: {session_id}")
                
                return agent_response
            else:
                logger.error(f"❌ AGENT {selected_agent.name.lower()}: {agent_response.error}")
                return agent_response
                
        except Exception as e:
            logger.error(f"❌ ENHANCED ORCHESTRATOR ERROR: {e}")
            import traceback
            logger.error(f"❌ TRACEBACK: {traceback.format_exc()}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"orchestrator": "enhanced_langgraph", "error": "processing_failed"},
                error=str(e)
            )
    
    async def process_with_specific_agent(self, user_input: str, agent_name: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process request with a specific agent (for compatibility)."""
        if agent_name.lower() not in self.agents:
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": agent_name},
                error=f"Agent '{agent_name}' not found"
            )
        
        agent = self.agents[agent_name.lower()]
        return await agent.process_request(user_input, context or {})
    
    def get_agent_capabilities(self) -> Dict[str, str]:
        """Get capabilities of all agents."""
        return {
            "general": "Conversations, greetings, general help",
            "code": "Programming, coding, software development",
            "document": "Document creation, reports, guides",
            "minio": "File storage and management",
            "typesense": "Search and indexing",
            "qdrant": "RAG and knowledge retrieval",
            "file_display": "File reading and content display"
        }
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agents."""
        return list(self.agents.keys()) 