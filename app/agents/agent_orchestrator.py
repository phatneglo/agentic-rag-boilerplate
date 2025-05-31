"""
Agent Orchestrator - LangGraph-based orchestration system for specialized agents.
"""

import asyncio
from typing import Dict, Any, List, Optional, TypedDict
from typing_extensions import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.agents.base_agent import AgentResponse, ArtifactType
from app.agents.agents.code_agent import CodeAgent
from app.agents.agents.diagram_agent import DiagramAgent
from app.agents.agents.analysis_agent import AnalysisAgent
from app.agents.agents.document_agent import DocumentAgent
from app.agents.agents.visualization_agent import VisualizationAgent
from app.agents.agents.general_agent import GeneralAgent
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class OrchestrationState(TypedDict):
    """State for the agent orchestration workflow."""
    user_input: str
    context: Dict[str, Any]
    selected_agents: List[str]
    agent_responses: Dict[str, AgentResponse]
    final_response: Optional[AgentResponse]
    messages: Annotated[list, add_messages]


class AgentOrchestrator:
    """
    LangGraph-based orchestrator for coordinating specialized agents.
    Routes requests to appropriate agents and combines responses.
    """
    
    def __init__(self):
        # Initialize all specialized agents
        self.agents = {
            "general": GeneralAgent(),
            "code": CodeAgent(),
            "diagram": DiagramAgent(),
            "analysis": AnalysisAgent(),
            "document": DocumentAgent(),
            "visualization": VisualizationAgent()
        }
        
        # Build the orchestration graph
        self.workflow = self._build_workflow()
        
        logger.info("Agent Orchestrator initialized with all specialized agents")
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for agent orchestration."""
        
        # Define the workflow graph
        workflow = StateGraph(OrchestrationState)
        
        # Add nodes
        workflow.add_node("route_request", self._route_request)
        workflow.add_node("execute_agents", self._execute_agents)
        workflow.add_node("combine_responses", self._combine_responses)
        
        # Add edges
        workflow.add_edge(START, "route_request")
        workflow.add_edge("route_request", "execute_agents")
        workflow.add_edge("execute_agents", "combine_responses")
        workflow.add_edge("combine_responses", END)
        
        return workflow.compile()
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Process user request through the agent orchestration workflow.
        """
        try:
            logger.info(f"Orchestrating request: {user_input[:100]}...")
            
            # Initialize state
            initial_state = {
                "user_input": user_input,
                "context": context or {},
                "selected_agents": [],
                "agent_responses": {},
                "final_response": None,
                "messages": [HumanMessage(content=user_input)]
            }
            
            # Execute the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            return final_state["final_response"]
            
        except Exception as e:
            logger.error(f"Error in orchestration: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"orchestrator": "error"},
                error=str(e)
            )
    
    async def _route_request(self, state: OrchestrationState) -> OrchestrationState:
        """Route the request to appropriate agents based on content analysis."""
        
        # Score each agent's capability to handle the request
        agent_scores = {}
        
        for agent_name, agent in self.agents.items():
            if agent.can_handle(state["user_input"]):
                # Calculate a score based on keyword matches
                keywords = agent.extract_keywords(state["user_input"])
                score = len(keywords)
                
                # Boost score for more specific matches
                if any(kw.lower() in state["user_input"].lower() for capability in agent.capabilities for kw in capability.keywords):
                    score += 2
                
                # Give general agent higher priority for short conversational inputs
                if agent_name == "general" and len(state["user_input"].split()) <= 5:
                    score += 3
                
                agent_scores[agent_name] = score
        
        # Select agents with scores above threshold
        threshold = 1
        selected_agents = [name for name, score in agent_scores.items() if score >= threshold]
        
        # If no agents selected, default to general agent for conversation
        if not selected_agents:
            if agent_scores:
                best_agent = max(agent_scores, key=agent_scores.get)
                selected_agents = [best_agent]
            else:
                selected_agents = ["general"]  # Default to general conversation
        
        # Prioritize general agent for simple inputs
        if "general" in selected_agents and len(state["user_input"].split()) <= 5:
            selected_agents = ["general"]
        
        # Limit to top 2 agents to avoid overwhelming responses
        selected_agents = selected_agents[:2]
        
        state["selected_agents"] = selected_agents
        
        logger.info(f"Selected agents: {selected_agents} (scores: {agent_scores})")
        
        return state
    
    async def _execute_agents(self, state: OrchestrationState) -> OrchestrationState:
        """Execute the selected agents in parallel."""
        
        async def execute_agent(agent_name: str) -> tuple[str, AgentResponse]:
            try:
                agent = self.agents[agent_name]
                response = await agent.process_request(state["user_input"], state["context"])
                return agent_name, response
            except Exception as e:
                logger.error(f"Error executing {agent_name} agent: {e}")
                return agent_name, AgentResponse(
                    success=False,
                    content="",
                    artifacts=[],
                    metadata={"agent": agent_name},
                    error=str(e)
                )
        
        # Execute agents in parallel
        tasks = [execute_agent(agent_name) for agent_name in state["selected_agents"]]
        results = await asyncio.gather(*tasks)
        
        # Store responses
        state["agent_responses"] = dict(results)
        
        return state
    
    async def _combine_responses(self, state: OrchestrationState) -> OrchestrationState:
        """Combine responses from multiple agents into a cohesive final response."""
        
        successful_responses = [
            response for response in state["agent_responses"].values() 
            if response.success
        ]
        
        if not successful_responses:
            # All agents failed
            state["final_response"] = AgentResponse(
                success=False,
                content="I apologize, but I wasn't able to process your request successfully.",
                artifacts=[],
                metadata={"orchestrator": "all_agents_failed"},
                error="All selected agents failed to process the request"
            )
            return state
        
        # Combine content from successful responses
        combined_content_parts = []
        all_artifacts = []
        combined_metadata = {"orchestrator": "combined", "agents_used": list(state["agent_responses"].keys())}
        
        for agent_name, response in state["agent_responses"].items():
            if response.success:
                if response.content:
                    combined_content_parts.append(f"**{agent_name.title()} Agent Response:**\n{response.content}")
                
                all_artifacts.extend(response.artifacts)
                combined_metadata.update(response.metadata)
        
        # Create final combined response
        if len(successful_responses) == 1:
            # Single agent response - use it directly but add orchestrator metadata
            single_response = successful_responses[0]
            state["final_response"] = AgentResponse(
                success=True,
                content=single_response.content,
                artifacts=single_response.artifacts,
                metadata={**single_response.metadata, **combined_metadata}
            )
        else:
            # Multiple agents - combine responses
            combined_content = "\n\n".join(combined_content_parts)
            
            state["final_response"] = AgentResponse(
                success=True,
                content=combined_content,
                artifacts=all_artifacts,
                metadata=combined_metadata
            )
        
        return state
    
    def get_agent_capabilities(self) -> Dict[str, str]:
        """Get summary of all agent capabilities."""
        capabilities = {}
        for agent_name, agent in self.agents.items():
            capabilities[agent_name] = agent.get_capabilities_summary()
        return capabilities
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self.agents.keys())
    
    def get_agent_for_artifact_type(self, artifact_type: ArtifactType) -> Optional[str]:
        """Get the best agent for a specific artifact type."""
        for agent_name, agent in self.agents.items():
            for capability in agent.capabilities:
                if artifact_type in capability.artifact_types:
                    return agent_name
        return None
    
    async def get_agent_suggestions(self, user_input: str) -> Dict[str, float]:
        """Get suggestions for which agents could handle the request."""
        suggestions = {}
        
        for agent_name, agent in self.agents.items():
            if agent.can_handle(user_input):
                keywords = agent.extract_keywords(user_input)
                confidence = len(keywords) * 0.2  # Basic confidence scoring
                suggestions[agent_name] = min(confidence, 1.0)
        
        return suggestions 