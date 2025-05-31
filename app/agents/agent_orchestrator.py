"""
Agent Orchestrator - LangGraph-based orchestration system for specialized agents.
Based on LangGraph agentic RAG best practices.
"""

import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from typing_extensions import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
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

logger = get_logger(__name__)
settings = get_settings()


class MessagesState(TypedDict):
    """State for the agent orchestration workflow following LangGraph best practices."""
    messages: Annotated[list, add_messages]
    selected_agent: Optional[str]
    context: Dict[str, Any]
    config: Dict[str, Any]


class AgentOrchestrator:
    """
    LangGraph-based orchestrator for coordinating specialized agents.
    Follows the agentic RAG pattern from LangGraph tutorials.
    """
    
    def __init__(self):
        # Initialize specialized agents (focused and simplified)
        self.agents = {
            "general": GeneralAgent(),
            "code": CodeAgent(),
            "document": DocumentAgent(),
            "minio": MinIOAgent(),
            "typesense": TypeSenseAgent(),
            "qdrant": QdrantAgent(),
            "file_display": FileDisplayAgent()
        }
        
        # Initialize routing LLM
        self.routing_llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            api_key=settings.openai_api_key
        )
        
        # Build the orchestration graph
        self.workflow = self._build_workflow()
        
        logger.info("Agent Orchestrator initialized with simplified agents")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for agent orchestration following best practices."""
        
        # Define the workflow graph
        workflow = StateGraph(MessagesState)
        
        # Add nodes following the agentic pattern
        workflow.add_node("route_agent", self._route_agent)
        workflow.add_node("execute_general", self._execute_general)
        workflow.add_node("execute_code", self._execute_code)
        workflow.add_node("execute_document", self._execute_document)
        workflow.add_node("execute_minio", self._execute_minio)
        workflow.add_node("execute_typesense", self._execute_typesense)
        workflow.add_node("execute_qdrant", self._execute_qdrant)
        workflow.add_node("execute_file_display", self._execute_file_display)
        
        # Add edges following the routing pattern
        workflow.add_edge(START, "route_agent")
        
        # Add conditional edges for agent routing
        workflow.add_conditional_edges(
            "route_agent",
            self._agent_router,
            {
                "general": "execute_general",
                "code": "execute_code", 
                "document": "execute_document",
                "minio": "execute_minio",
                "typesense": "execute_typesense",
                "qdrant": "execute_qdrant",
                "file_display": "execute_file_display"
            }
        )
        
        # All execution nodes lead to END
        workflow.add_edge("execute_general", END)
        workflow.add_edge("execute_code", END)
        workflow.add_edge("execute_document", END)
        workflow.add_edge("execute_minio", END)
        workflow.add_edge("execute_typesense", END)
        workflow.add_edge("execute_qdrant", END)
        workflow.add_edge("execute_file_display", END)
        
        return workflow.compile()
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """
        Process user request through the agent orchestration workflow with streaming support.
        """
        try:
            logger.info(f"🚀 ORCHESTRATOR: Processing: {user_input[:100]}...")
            
            # Initialize state following LangGraph patterns
            initial_state = {
                "messages": [HumanMessage(content=user_input)],
                "selected_agent": None,
                "context": context or {},
                "config": config or {}
            }
            
            # Execute workflow with streaming support
            if config and config.get("callbacks"):
                logger.info("🔥 ORCHESTRATOR: Real-time streaming mode enabled")
                
                # Use astream for streaming
                final_state = None
                async for chunk in self.workflow.astream(initial_state, config=config):
                    # Process streaming chunks
                    if chunk and isinstance(chunk, dict):
                        # Get the latest state
                        for node_name, node_state in chunk.items():
                            if node_name.startswith("execute_") and "messages" in node_state:
                                final_state = node_state
                                break
                
                if not final_state:
                    # Fallback to regular invoke
                    final_state = await self.workflow.ainvoke(initial_state, config=config)
            else:
                # Regular execution
                final_state = await self.workflow.ainvoke(initial_state, config=config)
            
            # Extract response from final state
            if final_state and "messages" in final_state:
                last_message = final_state["messages"][-1]
                if hasattr(last_message, 'content'):
                    return AgentResponse(
                        success=True,
                        content=last_message.content,
                        artifacts=[],
                        metadata={
                            "primary_agent": final_state.get("selected_agent", "general"),
                            "orchestrator": "langgraph"
                        }
                    )
            
            # Fallback response
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"orchestrator": "error"},
                error="Failed to process request"
            )
            
        except Exception as e:
            logger.error(f"❌ ORCHESTRATOR ERROR: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"orchestrator": "error"},
                error=str(e)
            )
    
    async def _route_agent(self, state: MessagesState) -> MessagesState:
        """Route request to appropriate agent using AI-powered routing."""
        
        user_input = state["messages"][-1].content
        
        # Create routing prompt
        routing_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI agent router. Based on the user's request, select the most appropriate agent.

Available agents:
- general: For greetings, conversations, help, and general questions
- code: For programming, coding, software development tasks
- document: For creating formal documents, reports, guides, documentation
- minio: For file storage, management, object storage operations
- typesense: For search, indexing, finding information
- qdrant: For RAG, knowledge retrieval, question answering based on documents
- file_display: For reading, viewing, analyzing file contents

Rules:
1. For simple greetings or conversations (hi, hello, how are you), choose 'general'
2. For programming tasks (write code, create function), choose 'code'
3. For document creation (write report, create guide), choose 'document'
4. For file operations (upload, store, manage files), choose 'minio'
5. For search tasks (find, search, look for), choose 'typesense'
6. For knowledge questions (what is, explain, based on), choose 'qdrant'
7. For file reading (read file, show content), choose 'file_display'

Response format: Just the agent name (e.g., "general")"""),
            ("human", "Route this request: {user_input}")
        ])
        
        # Get routing decision
        chain = routing_prompt | self.routing_llm
        response = await chain.ainvoke({"user_input": user_input})
        
        selected_agent = response.content.strip().lower()
        
        # Validate agent selection
        if selected_agent not in self.agents:
            selected_agent = "general"  # Default fallback
        
        logger.info(f"🎯 ROUTER: Selected '{selected_agent}' for: '{user_input[:50]}...'")
        
        state["selected_agent"] = selected_agent
        return state
    
    def _agent_router(self, state: MessagesState) -> str:
        """Return the selected agent for conditional routing."""
        return state.get("selected_agent", "general")
    
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
    
    async def _execute_agent(self, agent_name: str, state: MessagesState) -> MessagesState:
        """Execute a specific agent with streaming support."""
        try:
            user_input = state["messages"][-1].content
            agent = self.agents[agent_name]
            
            logger.info(f"🎯 EXECUTING: {agent_name} agent")
            
            # Execute agent with streaming config
            config = state.get("config", {})
            response = await agent.process_request(user_input, state.get("context", {}), config)
            
            if response.success:
                # Add agent response to messages
                ai_message = AIMessage(content=response.content)
                state["messages"].append(ai_message)
                
                logger.info(f"✅ AGENT {agent_name}: Success")
            else:
                # Add error message
                error_message = AIMessage(content=f"Sorry, I encountered an error: {response.error}")
                state["messages"].append(error_message)
                
                logger.error(f"❌ AGENT {agent_name}: Failed - {response.error}")
            
            return state
            
        except Exception as e:
            logger.error(f"❌ ERROR executing {agent_name}: {e}")
            error_message = AIMessage(content=f"Sorry, I encountered an error while processing your request.")
            state["messages"].append(error_message)
            return state
    
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