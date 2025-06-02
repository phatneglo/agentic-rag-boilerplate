"""
General Agent - Handles conversational interactions and general queries.
"""

from typing import Dict, Any, List
import asyncio

from app.agents.base_agent import BaseAgent, AgentResponse, AgentCapability, ArtifactType
from app.core.logging_config import get_logger
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

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
        return """You are a helpful and conversational AI assistant. Your goal is to provide natural, engaging, and useful responses to any question or request.

You can help with:
- Answering questions and providing explanations
- Creating examples and demonstrations
- Providing information and guidance
- Natural conversation and friendly chat
- Lists, tables, and data in text format
- Simple code examples in your response
- Step-by-step instructions
- Recommendations and advice

Keep your responses:
- Natural and conversational (not overly formal)
- Helpful and informative
- Friendly and engaging
- Appropriately detailed for the request

When someone greets you, respond naturally and personally - vary your greetings and show genuine interest in helping them. Don't just say "How can I assist you today?" every time.

If someone asks for examples, code, lists, or explanations, provide them directly in your response. Format your answers nicely using markdown for better readability.

For example:
- If asked for a list of dog breeds, provide a nice formatted list
- If asked for code examples, include them inline with proper formatting
- If asked to explain something, give a clear explanation with examples
- If asked for instructions, provide step-by-step guidance

Always aim to be maximally helpful while keeping things natural and accessible. Be conversational, not robotic."""
    
    def can_handle(self, user_input: str) -> bool:
        """Handle almost all requests - this is now the primary agent."""
        # Handle everything except very specific technical requests
        return True
    
    async def process_request(self, user_input: str, context: Dict[str, Any] = None, config: Dict[str, Any] = None) -> AgentResponse:
        """Process general conversation request."""
        try:
            logger.info(f"General Agent processing request: {user_input[:100]}...")
            
            # Debug: Log what context we received
            logger.info(f"🔍 GENERAL AGENT DEBUG: Context keys: {list(context.keys()) if context else 'None'}")
            
            conversation_history = []
            if context and context.get('conversation_history'):
                history = context['conversation_history']
                logger.info(f"🔍 GENERAL AGENT DEBUG: Received {len(history)} messages in conversation history:")
                for i, msg in enumerate(history[-5:]):  # Show last 5 messages
                    logger.info(f"   History[{i}]: {msg.type} - {msg.content[:50]}...")
                conversation_history = history
            else:
                logger.info(f"🔍 GENERAL AGENT DEBUG: No conversation history received")
            
            # Generate conversational response with streaming support AND conversation history
            response_content = await self.generate_response_with_history(
                user_input, 
                conversation_history=conversation_history,
                config=config
            )
            
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
    
    async def generate_response_with_history(self, user_input: str, conversation_history: List = None, config: Dict[str, Any] = None) -> str:
        """Generate response including conversation history for context."""
        try:
            logger.info(f"🧠 GENERATING WITH HISTORY: {len(conversation_history or [])} previous messages")
            
            if not self.llm:
                logger.warning(f"⚠️ {self.name}: No LLM available, using mock response")
                return self._generate_mock_response(user_input, None)
            
            # Build message chain with conversation history
            messages = []
            
            # Add system prompt
            messages.append(SystemMessage(content=self.get_system_prompt()))
            
            # Add conversation history (but limit to recent messages to avoid token limits)
            if conversation_history:
                # Take last 10 messages to stay within token limits but provide context
                recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
                logger.info(f"🧠 Including {len(recent_history)} recent messages in context")
                
                for msg in recent_history:
                    if hasattr(msg, 'type') and hasattr(msg, 'content'):
                        if msg.type == "human":
                            messages.append(HumanMessage(content=msg.content))
                        elif msg.type == "ai":
                            messages.append(AIMessage(content=msg.content))
                    else:
                        logger.warning(f"⚠️ Skipping invalid message in history: {msg}")
            
            # Add current user input
            messages.append(HumanMessage(content=user_input))
            
            logger.info(f"🧠 FINAL MESSAGE CHAIN: {len(messages)} messages total")
            
            # Check if streaming is requested via config
            if config and config.get("callbacks"):
                logger.info(f"🚀 {self.name}: Starting real-time streaming with history context")
                
                callbacks = config.get("callbacks", [])
                callback = callbacks[0] if callbacks else None
                
                # Use astream for real-time token streaming with cancellation checks
                full_response = ""
                try:
                    async for chunk in self.llm.astream(messages, config=config):
                        # Check if user cancelled the generation
                        if callback and hasattr(callback, 'is_cancelled') and callback.is_cancelled:
                            logger.info(f"🛑 {self.name}: Generation cancelled by user")
                            break
                            
                        # Check if asyncio task was cancelled
                        if asyncio.current_task() and asyncio.current_task().cancelled():
                            logger.info(f"🛑 {self.name}: Generation cancelled by task cancellation")
                            break
                            
                        if hasattr(chunk, 'content') and chunk.content:
                            full_response += chunk.content
                            
                except asyncio.CancelledError:
                    logger.info(f"🛑 {self.name}: Generation cancelled via asyncio.CancelledError")
                    raise
                except Exception as stream_error:
                    logger.error(f"❌ {self.name}: Error during streaming: {stream_error}")
                    raise
                
                logger.info(f"✅ {self.name}: Completed streaming with history - {len(full_response)} characters total")
                return full_response
            else:
                # Regular non-streaming request
                logger.info(f"🔧 {self.name}: Using regular non-streaming request with history")
                response = await self.llm.ainvoke(messages)
                logger.info(f"✅ {self.name}: Got response with history - {len(response.content)} characters")
                return response.content
                
        except asyncio.CancelledError:
            logger.info(f"🛑 {self.name}: CancelledError re-raised")
            raise
        except Exception as e:
            logger.error(f"❌ {self.name}: Error generating response with history: {e}")
            logger.error(f"❌ {self.name}: Error type: {type(e).__name__}")
            # Fallback to mock response on error
            logger.warning(f"⚠️ {self.name}: Falling back to mock response due to error")
            return self._generate_mock_response(user_input, None)
    
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