"""
Analysis Agent - Specialized for generating analysis and insights artifacts.
"""

from typing import Dict, Any, List
import json

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Agent specialized in generating analysis artifacts.
    Handles data analysis, insights, reports, and recommendations.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Data Analysis",
                description="Analyze data and generate insights",
                artifact_types=[ArtifactType.ANALYSIS, ArtifactType.JSON],
                keywords=[
                    "analyze", "analysis", "data", "insights", "trends",
                    "statistics", "metrics", "performance", "patterns"
                ],
                examples=[
                    "Analyze sales data trends",
                    "Generate performance insights",
                    "Create statistical analysis report"
                ]
            ),
            AgentCapability(
                name="Business Intelligence",
                description="Generate business intelligence reports and recommendations",
                artifact_types=[ArtifactType.ANALYSIS, ArtifactType.DOCUMENT],
                keywords=[
                    "business", "intelligence", "kpi", "roi", "growth",
                    "market", "competitive", "strategy", "recommendations"
                ],
                examples=[
                    "Create business performance analysis",
                    "Generate market analysis report",
                    "Analyze competitor strategies"
                ]
            ),
            AgentCapability(
                name="Technical Analysis",
                description="Perform technical analysis and system evaluation",
                artifact_types=[ArtifactType.ANALYSIS, ArtifactType.JSON],
                keywords=[
                    "technical", "system", "architecture", "performance",
                    "security", "scalability", "optimization", "review"
                ],
                examples=[
                    "Analyze system performance",
                    "Review code architecture",
                    "Evaluate security measures"
                ]
            )
        ]
        
        super().__init__("Analysis", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are an Analysis Agent, an expert in data analysis, business intelligence, and generating insights.

Your capabilities include:
- Analyzing data patterns and trends
- Generating business intelligence reports
- Creating technical analysis and evaluations
- Providing actionable recommendations
- Summarizing complex information into key insights

When performing analysis:
1. Structure findings clearly with key insights
2. Provide data-driven conclusions
3. Include actionable recommendations
4. Use appropriate metrics and KPIs
5. Present information in digestible formats

Always structure your analysis as:
1. Executive Summary
2. Key Findings
3. Detailed Analysis
4. Recommendations
5. Next Steps (if applicable)

Focus on providing valuable, actionable insights that help decision-making."""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        keywords = self.extract_keywords(user_input)
        
        analysis_indicators = [
            "analyze", "analysis", "insights", "trends", "report",
            "evaluate", "assessment", "review", "study", "examine",
            "investigate", "summarize", "breakdown", "metrics"
        ]
        
        user_lower = user_input.lower()
        for indicator in analysis_indicators:
            if indicator in user_lower:
                return True
        
        return len(keywords) > 0
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process analysis request."""
        try:
            logger.info(f"Analysis Agent processing request: {user_input[:100]}...")
            
            # Generate analysis response
            response_content = await self.generate_response(user_input)
            
            # Create analysis artifact
            analysis_artifact = self._create_analysis_artifact(user_input, response_content)
            
            artifacts = [analysis_artifact]
            
            response = AgentResponse(
                success=True,
                content=self._format_analysis_summary(response_content),
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "analysis_type": self._detect_analysis_type(user_input)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in Analysis Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _create_analysis_artifact(self, user_input: str, content: str) -> Dict[str, Any]:
        """Create structured analysis artifact."""
        
        # Parse the analysis content into structured format
        analysis_data = self._parse_analysis_content(content)
        
        artifact = self.create_artifact(
            ArtifactType.ANALYSIS,
            title=self._generate_title(user_input),
            summary=analysis_data.get("summary", ""),
            findings=analysis_data.get("findings", []),
            recommendations=analysis_data.get("recommendations", []),
            content=content,
            metadata={
                "analysis_type": self._detect_analysis_type(user_input),
                "sections": list(analysis_data.keys())
            }
        )
        
        return artifact
    
    def _parse_analysis_content(self, content: str) -> Dict[str, Any]:
        """Parse analysis content into structured sections."""
        sections = {
            "summary": "",
            "findings": [],
            "recommendations": [],
            "metrics": {},
            "conclusions": []
        }
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect section headers
            if any(header in line_lower for header in ["summary", "executive summary"]):
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content)
                current_section = "summary"
                current_content = []
            elif any(header in line_lower for header in ["findings", "key findings", "analysis"]):
                if current_section and current_content:
                    sections[current_section] = self._process_list_content(current_content)
                current_section = "findings"
                current_content = []
            elif any(header in line_lower for header in ["recommendations", "suggestions"]):
                if current_section and current_content:
                    sections[current_section] = self._process_list_content(current_content)
                current_section = "recommendations"
                current_content = []
            elif any(header in line_lower for header in ["conclusions", "conclusion"]):
                if current_section and current_content:
                    sections[current_section] = self._process_list_content(current_content)
                current_section = "conclusions"
                current_content = []
            else:
                if line.strip():
                    current_content.append(line.strip())
        
        # Process the last section
        if current_section and current_content:
            if current_section in ["findings", "recommendations", "conclusions"]:
                sections[current_section] = self._process_list_content(current_content)
            else:
                sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _process_list_content(self, content_lines: List[str]) -> List[str]:
        """Process content into list format."""
        items = []
        current_item = []
        
        for line in content_lines:
            if line.startswith(('-', '•', '*', '1.', '2.', '3.', '4.', '5.')):
                if current_item:
                    items.append(' '.join(current_item))
                current_item = [line.lstrip('-•*0123456789. ')]
            else:
                current_item.append(line)
        
        if current_item:
            items.append(' '.join(current_item))
        
        return items
    
    def _detect_analysis_type(self, user_input: str) -> str:
        """Detect the type of analysis requested."""
        user_lower = user_input.lower()
        
        if any(term in user_lower for term in ["business", "market", "sales", "revenue"]):
            return "business"
        elif any(term in user_lower for term in ["technical", "system", "architecture", "code"]):
            return "technical"
        elif any(term in user_lower for term in ["data", "statistics", "metrics", "performance"]):
            return "data"
        else:
            return "general"
    
    def _generate_title(self, user_input: str) -> str:
        """Generate title for analysis artifact."""
        analysis_type = self._detect_analysis_type(user_input)
        
        type_titles = {
            "business": "Business Analysis Report",
            "technical": "Technical Analysis Report",
            "data": "Data Analysis Report",
            "general": "Analysis Report"
        }
        
        return type_titles.get(analysis_type, "Analysis Report")
    
    def _format_analysis_summary(self, content: str) -> str:
        """Format a brief summary of the analysis."""
        lines = content.split('\n')
        summary_lines = []
        
        # Take first few meaningful lines as summary
        for line in lines[:10]:
            if line.strip() and not line.strip().startswith('#'):
                summary_lines.append(line.strip())
                if len(summary_lines) >= 3:
                    break
        
        summary = ' '.join(summary_lines)
        
        if len(summary) > 300:
            summary = summary[:297] + "..."
        
        return f"Analysis completed. {summary} [Detailed analysis available in artifact]" 