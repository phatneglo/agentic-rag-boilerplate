"""
Diagram Agent - Specialized for generating mermaid diagrams and flowcharts.
"""

import re
from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DiagramAgent(BaseAgent):
    """
    Agent specialized in generating diagram artifacts.
    Handles Mermaid diagrams, flowcharts, system diagrams, etc.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Flowchart Generation",
                description="Create flowcharts and process diagrams",
                artifact_types=[ArtifactType.MERMAID],
                keywords=[
                    "flowchart", "flow", "process", "workflow", "steps",
                    "diagram", "chart", "sequence", "decision"
                ],
                examples=[
                    "Create a flowchart for user registration",
                    "Show the workflow for order processing",
                    "Generate a decision tree diagram"
                ]
            ),
            AgentCapability(
                name="System Architecture Diagrams",
                description="Generate system architecture and component diagrams",
                artifact_types=[ArtifactType.MERMAID],
                keywords=[
                    "architecture", "system", "component", "microservice",
                    "infrastructure", "network", "deployment", "topology"
                ],
                examples=[
                    "Design a microservices architecture",
                    "Create a network topology diagram",
                    "Show system components and their relationships"
                ]
            ),
            AgentCapability(
                name="Database Diagrams",
                description="Create database schema and relationship diagrams",
                artifact_types=[ArtifactType.MERMAID],
                keywords=[
                    "database", "schema", "erd", "entity", "relationship",
                    "table", "foreign key", "primary key"
                ],
                examples=[
                    "Create an ERD for e-commerce database",
                    "Show table relationships",
                    "Generate database schema diagram"
                ]
            ),
            AgentCapability(
                name="Sequence Diagrams",
                description="Generate sequence diagrams for interactions",
                artifact_types=[ArtifactType.MERMAID],
                keywords=[
                    "sequence", "interaction", "timeline", "communication",
                    "message", "actor", "participant", "api flow"
                ],
                examples=[
                    "Show API call sequence",
                    "Create user interaction flow",
                    "Generate communication timeline"
                ]
            ),
            AgentCapability(
                name="Mind Maps and Conceptual Diagrams",
                description="Create mind maps and conceptual diagrams",
                artifact_types=[ArtifactType.MERMAID],
                keywords=[
                    "mindmap", "mind map", "concept", "hierarchy",
                    "organization", "structure", "tree", "taxonomy"
                ],
                examples=[
                    "Create a mind map for project planning",
                    "Show organizational hierarchy",
                    "Generate concept relationships"
                ]
            )
        ]
        
        super().__init__("Diagram", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are a Diagram Agent, an expert in creating visual diagrams using Mermaid syntax.

Your capabilities include:
- Creating flowcharts and process diagrams
- Generating system architecture diagrams
- Building database schema and ERD diagrams
- Designing sequence diagrams for interactions
- Making mind maps and conceptual diagrams

When creating diagrams:
1. Use proper Mermaid syntax and formatting
2. Choose the most appropriate diagram type for the request
3. Include clear labels and descriptions
4. Organize elements logically and readably
5. Use appropriate colors and styling when helpful

Mermaid diagram types you can create:
- flowchart TD/LR (Top Down / Left Right flowcharts)
- sequenceDiagram (for interactions and API flows)
- erDiagram (for database relationships)
- graph TD/LR (for general graphs)
- mindmap (for mind maps)
- gitgraph (for version control flows)
- journey (for user journeys)

Always structure your response as:
1. Brief explanation of the diagram purpose
2. The Mermaid diagram code
3. Additional notes or customization suggestions

Focus on creating clear, informative diagrams that effectively communicate the requested information."""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        keywords = self.extract_keywords(user_input)
        
        # Check for diagram-related terms
        diagram_indicators = [
            "diagram", "chart", "flowchart", "flow", "mermaid",
            "visualize", "show", "draw", "create diagram", "sequence",
            "architecture", "schema", "erd", "mindmap", "process"
        ]
        
        user_lower = user_input.lower()
        for indicator in diagram_indicators:
            if indicator in user_lower:
                return True
        
        return len(keywords) > 0
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process diagram generation request."""
        try:
            logger.info(f"Diagram Agent processing request: {user_input[:100]}...")
            
            # Detect diagram type
            diagram_type = self._detect_diagram_type(user_input)
            
            # Generate diagram response
            response_content = await self.generate_response(
                user_input, 
                self._get_specialized_prompt(diagram_type)
            )
            
            # Extract mermaid diagrams from response
            diagrams = self._extract_mermaid_diagrams(response_content)
            
            artifacts = []
            for i, diagram in enumerate(diagrams):
                artifact = self.create_artifact(
                    ArtifactType.MERMAID,
                    title=self._generate_title(user_input, diagram_type),
                    content=diagram["content"],
                    description=self._generate_description(user_input, diagram_type)
                )
                artifacts.append(artifact)
            
            # If no diagrams found, try to create one from the response
            if not artifacts:
                diagram_content = self._extract_diagram_content(response_content)
                if diagram_content:
                    artifact = self.create_artifact(
                        ArtifactType.MERMAID,
                        title=self._generate_title(user_input, diagram_type),
                        content=diagram_content,
                        description=self._generate_description(user_input, diagram_type)
                    )
                    artifacts.append(artifact)
            
            response = AgentResponse(
                success=True,
                content=self._clean_response_content(response_content),
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "diagram_type": diagram_type,
                    "diagrams_found": len(diagrams)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in Diagram Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _detect_diagram_type(self, user_input: str) -> str:
        """Detect the type of diagram needed."""
        user_lower = user_input.lower()
        
        type_indicators = {
            "flowchart": ["flowchart", "flow", "process", "workflow", "steps"],
            "sequence": ["sequence", "interaction", "api", "timeline", "communication"],
            "erd": ["database", "schema", "erd", "entity", "relationship", "table"],
            "architecture": ["architecture", "system", "component", "microservice"],
            "mindmap": ["mindmap", "mind map", "concept", "hierarchy"],
            "graph": ["graph", "network", "connection", "relationship"],
            "journey": ["journey", "user journey", "customer journey", "experience"]
        }
        
        for diagram_type, indicators in type_indicators.items():
            for indicator in indicators:
                if indicator in user_lower:
                    return diagram_type
        
        return "flowchart"  # Default to flowchart
    
    def _get_specialized_prompt(self, diagram_type: str) -> str:
        """Get specialized prompt based on diagram type."""
        base_prompt = self.get_system_prompt()
        
        type_specific_prompts = {
            "flowchart": "\n\nFocus on creating a clear flowchart using 'flowchart TD' or 'flowchart LR' syntax. Include decision points, processes, and clear flow directions.",
            "sequence": "\n\nCreate a sequence diagram using 'sequenceDiagram' syntax. Show participants, messages, and interactions over time.",
            "erd": "\n\nGenerate an ERD using 'erDiagram' syntax. Include entities, attributes, and relationships with proper cardinality.",
            "architecture": "\n\nCreate a system architecture diagram using 'graph TD' or 'flowchart TD' syntax. Show components, services, and their connections.",
            "mindmap": "\n\nCreate a mind map using 'mindmap' syntax. Organize concepts hierarchically with clear relationships.",
            "graph": "\n\nCreate a graph diagram using 'graph TD' or 'graph LR' syntax. Show nodes and their connections.",
            "journey": "\n\nCreate a user journey using 'journey' syntax. Show the user experience steps and emotions."
        }
        
        return base_prompt + type_specific_prompts.get(diagram_type, "")
    
    def _extract_mermaid_diagrams(self, content: str) -> List[Dict[str, str]]:
        """Extract Mermaid diagrams from content."""
        diagrams = []
        
        # Pattern for mermaid code blocks
        pattern = r'```mermaid\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            diagrams.append({
                "content": match.strip()
            })
        
        return diagrams
    
    def _extract_diagram_content(self, content: str) -> str:
        """Extract diagram content if not in code blocks."""
        lines = content.split('\n')
        diagram_lines = []
        
        # Look for mermaid diagram syntax
        mermaid_keywords = [
            "flowchart", "sequenceDiagram", "erDiagram", 
            "graph", "mindmap", "gitgraph", "journey"
        ]
        
        in_diagram = False
        for line in lines:
            line_stripped = line.strip()
            
            # Check if line starts a diagram
            if any(keyword in line_stripped for keyword in mermaid_keywords):
                in_diagram = True
                diagram_lines.append(line_stripped)
            elif in_diagram:
                # Continue collecting diagram lines
                if line_stripped and not line_stripped.startswith('#'):
                    diagram_lines.append(line_stripped)
                elif not line_stripped and diagram_lines:
                    # Empty line might end the diagram
                    break
        
        return '\n'.join(diagram_lines) if diagram_lines else ""
    
    def _clean_response_content(self, content: str) -> str:
        """Clean response content for display."""
        # Remove mermaid code blocks but keep explanatory text
        cleaned = re.sub(r'```mermaid\n.*?\n```', '[Diagram artifact generated]', content, flags=re.DOTALL)
        return cleaned.strip()
    
    def _generate_title(self, user_input: str, diagram_type: str) -> str:
        """Generate a descriptive title for the diagram."""
        type_titles = {
            "flowchart": "Process Flowchart",
            "sequence": "Sequence Diagram", 
            "erd": "Database Schema",
            "architecture": "System Architecture",
            "mindmap": "Mind Map",
            "graph": "Network Diagram",
            "journey": "User Journey"
        }
        
        base_title = type_titles.get(diagram_type, "Diagram")
        
        # Try to extract subject from user input
        if "for" in user_input.lower():
            subject_match = re.search(r'for\s+(.+?)(?:\.|$)', user_input, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()[:50]
                return f"{base_title} - {subject}"
        
        return base_title
    
    def _generate_description(self, user_input: str, diagram_type: str) -> str:
        """Generate a description for the diagram artifact."""
        return f"Generated {diagram_type} diagram for: {user_input[:100]}{'...' if len(user_input) > 100 else ''}" 