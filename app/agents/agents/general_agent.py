"""
General Agent - Handles conversational interactions and general queries.
"""

from typing import Dict, Any, List

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GeneralAgent(BaseAgent):
    """
    Agent for handling general conversational interactions and simple queries.
    Provides friendly responses for greetings, compliments, and general questions.
    """
    
    def __init__(self):
        capabilities = [
            AgentCapability(
                name="Conversational Interactions",
                description="Handle greetings, social interactions, and casual conversation",
                artifact_types=[],  # No artifacts for simple conversation
                keywords=[
                    "hi", "hello", "hey", "thanks", "thank you", "cool", "nice",
                    "awesome", "great", "good", "how are you", "what's up"
                ],
                examples=[
                    "Hi there!",
                    "That's cool",
                    "How are you today?"
                ]
            ),
            AgentCapability(
                name="General Questions",
                description="Answer general questions about capabilities and help",
                artifact_types=[],
                keywords=[
                    "help", "what can you do", "abilities", "capabilities",
                    "assist", "support", "question", "tell me about"
                ],
                examples=[
                    "What can you help me with?",
                    "Tell me about your capabilities",
                    "How can you assist me?"
                ]
            )
        ]
        
        super().__init__("General", capabilities)
    
    def get_system_prompt(self) -> str:
        return """You are a friendly AI assistant. You handle conversational interactions and general questions with warmth and helpfulness.

Your role is to:
- Respond to greetings and social interactions naturally
- Acknowledge user comments and compliments appropriately  
- Provide brief, helpful responses to general questions
- Guide users toward specific help when they need specialized assistance

Keep your responses:
- Friendly and conversational
- Brief and to the point
- Helpful without being overwhelming
- Encouraging and positive

For specific tasks like coding, analysis, diagrams, or document creation, you should suggest that the user ask more specifically about what they need help with.

Example responses:
- For "Hi" → "Hello! I'm here to help you with coding, analysis, writing, diagrams, and more. What can I assist you with today?"
- For "That's cool" → "I'm glad you think so! Is there anything specific I can help you with?"
- For "How are you?" → "I'm doing great, thanks for asking! I'm ready to help with whatever you need. What would you like to work on?"
"""
    
    def can_handle(self, user_input: str) -> bool:
        """Check if this agent can handle the user request."""
        user_lower = user_input.lower().strip()
        
        # Handle short conversational inputs
        if len(user_input.split()) <= 5:
            conversational_patterns = [
                "hi", "hello", "hey", "thanks", "thank you", "thanks!",
                "cool", "nice", "good", "great", "awesome", "ok", "okay",
                "yes", "no", "wow", "amazing", "interesting", "how are you",
                "what's up", "wassup", "sup", "morning", "afternoon", "evening"
            ]
            
            for pattern in conversational_patterns:
                if pattern in user_lower or user_lower == pattern:
                    return True
        
        # Handle general help requests
        help_patterns = [
            "what can you do", "what are your capabilities", "help me",
            "can you help", "what can you help with", "tell me about yourself",
            "what are you", "who are you"
        ]
        
        for pattern in help_patterns:
            if pattern in user_lower:
                return True
        
        return False
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process general conversation request."""
        try:
            logger.info(f"General Agent processing request: {user_input[:100]}...")
            
            # Generate conversational response
            response_content = await self.generate_response(user_input)
            
            # No artifacts for simple conversation
            artifacts = []
            
            response = AgentResponse(
                success=True,
                content=response_content,
                artifacts=artifacts,
                metadata={
                    "agent": self.name,
                    "interaction_type": self._classify_interaction(user_input)
                }
            )
            
            return await self.validate_output(response)
            
        except Exception as e:
            logger.error(f"Error in General Agent: {e}")
            return AgentResponse(
                success=False,
                content="",
                artifacts=[],
                metadata={"agent": self.name},
                error=str(e)
            )
    
    def _classify_interaction(self, user_input: str) -> str:
        """Classify the type of interaction."""
        user_lower = user_input.lower()
        
        if any(greeting in user_lower for greeting in ["hi", "hello", "hey"]):
            return "greeting"
        elif any(thanks in user_lower for thanks in ["thanks", "thank you"]):
            return "gratitude"
        elif any(compliment in user_lower for compliment in ["cool", "nice", "awesome", "great"]):
            return "compliment"
        elif any(question in user_lower for question in ["how are you", "what's up"]):
            return "social_question"
        elif any(help_word in user_lower for help_word in ["help", "what can you"]):
            return "help_request"
        else:
            return "general"
    
    def _generate_mock_response(self, user_input: str, system_prompt: str = None) -> str:
        """Generate a mock response for general conversation."""
        user_lower = user_input.lower()
        
        # Greeting responses
        if any(greeting in user_lower for greeting in ["hi", "hello", "hey"]):
            return "Hello! I'm here to help you with coding, analysis, writing, diagrams, and more. What can I assist you with today?"
        
        # Compliment responses
        elif any(compliment in user_lower for compliment in ["cool", "nice", "awesome", "great"]):
            return "I'm glad you think so! Is there anything specific I can help you with? I can assist with coding, creating diagrams, writing documents, data analysis, or visualizations."
        
        # Social questions
        elif "how are you" in user_lower:
            return "I'm doing great, thanks for asking! I'm ready to help with whatever you need. What would you like to work on?"
        
        # Thanks responses
        elif any(thanks in user_lower for thanks in ["thanks", "thank you"]):
            return "You're welcome! Feel free to ask if you need help with anything else."
        
        # Help requests
        elif any(help_word in user_lower for help_word in ["help", "what can you"]):
            return """I can help you with many different tasks:

• **Code Generation** - Python, JavaScript, SQL, and more
• **Diagram Creation** - Flowcharts, system architectures, ERDs
• **Data Analysis** - Insights, reports, and recommendations  
• **Document Writing** - Technical docs, reports, articles
• **Data Visualization** - Charts, graphs, and dashboards

Just tell me what you'd like to work on and I'll assist you!"""
        
        # Default response
        else:
            return "I appreciate your message! How can I help you today? I can assist with coding, diagrams, analysis, writing, or visualizations." 