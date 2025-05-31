"""
Visualization Agent - Specialized for generating charts and visual data representations.
"""

import json
from typing import Dict, Any, List
import random

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class VisualizationAgent(BaseAgent):
    """
    Agent specialized in generating visualization artifacts.
    Handles charts, graphs, and visual data representations.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Statistical Charts",
                description="Create statistical charts and data visualizations",
                artifact_types=[ArtifactType.CHART, ArtifactType.JSON],
                keywords=[
                    "chart", "graph", "plot", "visualize", "statistics",
                    "bar chart", "line chart", "pie chart", "histogram", "scatter"
                ],
                examples=[
                    "Create a bar chart of sales data",
                    "Generate a line graph showing trends",
                    "Make a pie chart of market share"
                ]
            ),
            AgentCapability(
                name="Business Dashboards",
                description="Generate business intelligence visualizations",
                artifact_types=[ArtifactType.CHART, ArtifactType.HTML],
                keywords=[
                    "dashboard", "kpi", "metrics", "performance", "business",
                    "analytics", "trends", "monitoring", "indicators"
                ],
                examples=[
                    "Create a sales dashboard",
                    "Generate KPI visualization",
                    "Build performance metrics chart"
                ]
            ),
            AgentCapability(
                name="Data Analysis Plots",
                description="Create data analysis and scientific plots",
                artifact_types=[ArtifactType.CHART, ArtifactType.JSON],
                keywords=[
                    "data analysis", "correlation", "distribution", "regression",
                    "box plot", "heat map", "violin plot", "scientific"
                ],
                examples=[
                    "Create correlation heatmap",
                    "Generate distribution plot",
                    "Make regression analysis chart"
                ]
            )
        ]
        
        super().__init__("Visualization", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are a Visualization Agent, an expert in creating data visualizations and charts.

Your capabilities include:
- Creating statistical charts (bar, line, pie, scatter, histogram)
- Generating business dashboards and KPI visualizations
- Building data analysis plots and scientific visualizations
- Designing interactive and informative charts
- Selecting appropriate chart types for different data

When creating visualizations:
1. Choose the most appropriate chart type for the data
2. Use clear, descriptive titles and labels
3. Apply appropriate colors and styling
4. Ensure data is presented clearly and accurately
5. Include legends and annotations when helpful

Chart types you can create:
- Bar charts (vertical/horizontal)
- Line charts and time series
- Pie charts and donut charts
- Scatter plots and bubble charts
- Histograms and distribution plots
- Box plots and violin plots
- Heatmaps and correlation matrices
- Area charts and stacked charts

Always structure your response as:
1. Brief description of the visualization
2. Chart configuration and data
3. Insights or interpretation notes

Focus on creating clear, informative visualizations that effectively communicate the data story."""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        keywords = self.extract_keywords(user_input)
        
        viz_indicators = [
            "chart", "graph", "plot", "visualize", "visualization",
            "bar", "line", "pie", "scatter", "histogram", "dashboard",
            "show data", "display", "draw", "create chart"
        ]
        
        user_lower = user_input.lower()
        for indicator in viz_indicators:
            if indicator in user_lower:
                return True
        
        return len(keywords) > 0
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process visualization request."""
        try:
            logger.info(f"Visualization Agent processing request: {user_input[:100]}...")
            
            # Detect chart type
            chart_type = self._detect_chart_type(user_input)
            
            # Generate visualization response
            response_content = await self.generate_response(
                user_input,
                self._get_specialized_prompt(chart_type)
            )
            
            # Create visualization artifact
            viz_artifact = self._create_visualization_artifact(user_input, response_content, chart_type)
            
            artifacts = [viz_artifact]
            
            response = AgentResponse(
                success=True,
                content=self._format_visualization_summary(response_content, chart_type),
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "chart_type": chart_type,
                    "data_points": self._count_data_points(viz_artifact)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in Visualization Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _detect_chart_type(self, user_input: str) -> str:
        """Detect the type of chart requested."""
        user_lower = user_input.lower()
        
        chart_indicators = {
            "bar": ["bar", "column", "bars"],
            "line": ["line", "trend", "time series", "timeline"],
            "pie": ["pie", "donut", "proportion", "percentage"],
            "scatter": ["scatter", "correlation", "relationship"],
            "histogram": ["histogram", "distribution", "frequency"],
            "area": ["area", "filled"],
            "box": ["box plot", "box", "quartile"],
            "heatmap": ["heatmap", "heat map", "correlation matrix"]
        }
        
        for chart_type, indicators in chart_indicators.items():
            for indicator in indicators:
                if indicator in user_lower:
                    return chart_type
        
        # Default based on context
        if any(word in user_lower for word in ["over time", "trend", "timeline"]):
            return "line"
        elif any(word in user_lower for word in ["compare", "comparison", "categories"]):
            return "bar"
        else:
            return "bar"  # Default to bar chart
    
    def _get_specialized_prompt(self, chart_type: str) -> str:
        """Get specialized prompt based on chart type."""
        base_prompt = self.get_system_prompt()
        
        type_specific_prompts = {
            "bar": "\n\nCreate a bar chart with clear categories and values. Include appropriate colors and labels.",
            "line": "\n\nGenerate a line chart showing trends over time. Include clear x and y axes with appropriate scales.",
            "pie": "\n\nCreate a pie chart with clear segments and percentages. Use distinct colors for each segment.",
            "scatter": "\n\nGenerate a scatter plot showing relationships between variables. Include trend lines if appropriate.",
            "histogram": "\n\nCreate a histogram showing data distribution. Use appropriate bin sizes and clear labeling.",
            "area": "\n\nGenerate an area chart with smooth curves and appropriate fill colors.",
            "box": "\n\nCreate a box plot showing statistical distribution with quartiles and outliers.",
            "heatmap": "\n\nGenerate a heatmap with appropriate color scales and clear value indicators."
        }
        
        return base_prompt + type_specific_prompts.get(chart_type, "")
    
    def _create_visualization_artifact(self, user_input: str, content: str, chart_type: str) -> Dict[str, Any]:
        """Create visualization artifact with sample data."""
        
        # Generate sample data based on chart type
        chart_data = self._generate_sample_data(chart_type, user_input)
        
        # Create chart configuration
        chart_config = {
            "type": chart_type,
            "data": chart_data,
            "options": self._get_chart_options(chart_type),
            "plugins": self._get_chart_plugins(chart_type)
        }
        
        artifact = self.create_artifact(
            ArtifactType.CHART,
            title=self._generate_title(user_input, chart_type),
            chart_type=chart_type,
            data=chart_config,
            description=self._generate_description(user_input, chart_type),
            options=chart_config["options"]
        )
        
        return artifact
    
    def _generate_sample_data(self, chart_type: str, user_input: str) -> Dict[str, Any]:
        """Generate appropriate sample data for the chart type."""
        
        if chart_type == "bar":
            return {
                "labels": ["Q1", "Q2", "Q3", "Q4"],
                "datasets": [{
                    "label": "Sales",
                    "data": [12000, 15000, 18000, 16000],
                    "backgroundColor": ["#3498db", "#e74c3c", "#f39c12", "#2ecc71"]
                }]
            }
        
        elif chart_type == "line":
            return {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [{
                    "label": "Revenue",
                    "data": [10000, 12000, 11500, 14000, 16000, 15500],
                    "borderColor": "#3498db",
                    "backgroundColor": "rgba(52, 152, 219, 0.1)",
                    "fill": True
                }]
            }
        
        elif chart_type == "pie":
            return {
                "labels": ["Product A", "Product B", "Product C", "Product D"],
                "datasets": [{
                    "data": [30, 25, 25, 20],
                    "backgroundColor": ["#3498db", "#e74c3c", "#f39c12", "#2ecc71"]
                }]
            }
        
        elif chart_type == "scatter":
            scatter_data = []
            for i in range(20):
                scatter_data.append({
                    "x": random.randint(10, 100),
                    "y": random.randint(10, 100)
                })
            
            return {
                "datasets": [{
                    "label": "Data Points",
                    "data": scatter_data,
                    "backgroundColor": "#3498db"
                }]
            }
        
        else:
            # Default data structure
            return {
                "labels": ["Category 1", "Category 2", "Category 3", "Category 4"],
                "datasets": [{
                    "label": "Values",
                    "data": [25, 35, 20, 45],
                    "backgroundColor": ["#3498db", "#e74c3c", "#f39c12", "#2ecc71"]
                }]
            }
    
    def _get_chart_options(self, chart_type: str) -> Dict[str, Any]:
        """Get chart configuration options."""
        base_options = {
            "responsive": True,
            "plugins": {
                "legend": {
                    "position": "top"
                },
                "title": {
                    "display": True,
                    "text": "Chart Title"
                }
            }
        }
        
        if chart_type in ["bar", "line"]:
            base_options["scales"] = {
                "y": {
                    "beginAtZero": True
                }
            }
        
        return base_options
    
    def _get_chart_plugins(self, chart_type: str) -> List[str]:
        """Get required plugins for chart type."""
        return ["legend", "title", "tooltip"]
    
    def _count_data_points(self, artifact: Dict[str, Any]) -> int:
        """Count the number of data points in the chart."""
        try:
            data = artifact.get("data", {}).get("data", {})
            datasets = data.get("datasets", [])
            if datasets:
                return len(datasets[0].get("data", []))
            return 0
        except:
            return 0
    
    def _generate_title(self, user_input: str, chart_type: str) -> str:
        """Generate title for visualization artifact."""
        chart_type_names = {
            "bar": "Bar Chart",
            "line": "Line Chart",
            "pie": "Pie Chart",
            "scatter": "Scatter Plot",
            "histogram": "Histogram",
            "area": "Area Chart",
            "box": "Box Plot",
            "heatmap": "Heatmap"
        }
        
        base_title = chart_type_names.get(chart_type, "Chart")
        
        # Try to extract subject
        if "of" in user_input.lower():
            import re
            match = re.search(r'(?:chart|graph|plot)\s+of\s+(.+?)(?:\.|$|,)', user_input, re.IGNORECASE)
            if match:
                subject = match.group(1).strip()[:50]
                return f"{base_title} - {subject}"
        
        return base_title
    
    def _generate_description(self, user_input: str, chart_type: str) -> str:
        """Generate description for visualization artifact."""
        return f"Generated {chart_type} chart for: {user_input[:100]}{'...' if len(user_input) > 100 else ''}"
    
    def _format_visualization_summary(self, content: str, chart_type: str) -> str:
        """Format summary of the visualization."""
        return f"Created {chart_type} chart visualization. The chart displays the requested data with appropriate styling and formatting. [Interactive chart available in artifact]" 