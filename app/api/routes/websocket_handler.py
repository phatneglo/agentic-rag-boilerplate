"""
WebSocket handler for real-time multi-agent chat streaming with enhanced memory
"""
import asyncio
import json
import time
import uuid
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from langchain.callbacks.base import BaseCallbackHandler
from app.core.logging_config import get_logger
from app.agents.agent_orchestrator import AgentOrchestrator
from app.db.memory import PostgresChatMemory
from app.db.session import init_db

logger = get_logger(__name__)

class ChatWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.orchestrator = AgentOrchestrator()
        self.memory = PostgresChatMemory()
        self.active_tasks: Dict[WebSocket, asyncio.Task] = {}
        self.active_callbacks: Dict[WebSocket, 'AsyncStreamingCallback'] = {}
        # Track session info per connection
        self.connection_sessions: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Initialize connection session info
        self.connection_sessions[websocket] = {
            "session_id": None,
            "user_id": None,
            "last_activity": time.time()
        }
        
        logger.info("🔗 WebSocket connection established")

    def disconnect(self, websocket: WebSocket):
        # Cancel any active task for this connection
        if websocket in self.active_tasks:
            task = self.active_tasks[websocket]
            if not task.done():
                task.cancel()
            del self.active_tasks[websocket]
            
        # Cancel any active callback
        if websocket in self.active_callbacks:
            callback = self.active_callbacks[websocket]
            callback.cancel()
            del self.active_callbacks[websocket]
            
        # Clean up connection session info
        if websocket in self.connection_sessions:
            del self.connection_sessions[websocket]
            
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("🔗 WebSocket connection closed")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def handle_message(self, websocket: WebSocket, data: str):
        """Handle incoming WebSocket messages with enhanced memory support"""
        try:
            message_data = json.loads(data)
            logger.info(f"📨 Received WebSocket message: {message_data.get('type')}")
            
            message_type = message_data.get("type")
            
            if message_type == "chat_message":
                await self.handle_chat_message(
                    websocket, 
                    message_data.get("content", ""),
                    message_data.get("session_id"),
                    message_data.get("user_id"),
                    message_data.get("context", {})
                )
            elif message_type == "init_session":
                await self.handle_session_init(
                    websocket,
                    message_data.get("session_id"),
                    message_data.get("user_id"),
                    message_data.get("config", {})
                )
            elif message_type == "load_session":
                await self.handle_session_load(
                    websocket,
                    message_data.get("session_id")
                )
            elif message_type == "stop_generation":
                await self.handle_stop_generation(websocket)
            elif message_type == "ping":
                await self.handle_ping(websocket)
            elif message_type == "get_session_info":
                await self.handle_get_session_info(websocket)
                
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON received from WebSocket")
        except Exception as e:
            logger.error(f"❌ Error processing WebSocket message: {e}")
            await self.send_error_response(websocket, str(e))

    async def handle_session_init(self, websocket: WebSocket, session_id: Optional[str], user_id: Optional[str], config: Dict[str, Any]):
        """Initialize or create a new chat session"""
        try:
            connection_info = self.connection_sessions.get(websocket, {})
            
            if session_id:
                # Validate existing session
                try:
                    session_uuid = uuid.UUID(session_id)
                    session_details = await self.memory.get_session(session_uuid)
                    if session_details:
                        connection_info["session_id"] = session_id
                        connection_info["user_id"] = user_id or session_details.user_id
                        logger.info(f"🔗 MEMORY: Connected to existing session {session_id}")
                    else:
                        # Session not found, create new one
                        session_id = None
                except (ValueError, Exception) as e:
                    logger.warning(f"⚠️ Invalid session ID provided: {e}")
                    session_id = None
            
            if not session_id:
                # Create new session
                try:
                    session = await self.memory.create_session(
                        title="New Chat Session",
                        user_id=user_id or "anonymous",
                        session_type="chat",
                        config=config,
                        context={"initiated_via": "websocket"}
                    )
                    session_id = str(session.id)
                    connection_info["session_id"] = session_id
                    connection_info["user_id"] = user_id or "anonymous"
                    logger.info(f"🆕 MEMORY: Created new session {session_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to create session: {e}")
                    await self.send_error_response(websocket, "Failed to create chat session")
                    return
            
            # Update connection info
            connection_info["last_activity"] = time.time()
            self.connection_sessions[websocket] = connection_info
            
            # Send session info back to client
            await websocket.send_text(json.dumps({
                "type": "session_initialized",
                "session_id": session_id,
                "user_id": connection_info["user_id"],
                "timestamp": time.time()
            }))
            
        except Exception as e:
            logger.error(f"❌ Error initializing session: {e}")
            await self.send_error_response(websocket, f"Session initialization error: {e}")

    async def handle_session_load(self, websocket: WebSocket, session_id: str):
        """Load conversation history for a session"""
        try:
            if not session_id:
                await self.send_error_response(websocket, "No session ID provided")
                return
                
            session_uuid = uuid.UUID(session_id)
            
            # Load conversation history
            history = await self.memory.get_conversation_history(session_uuid, limit=50)
            session_stats = await self.memory.get_session_stats(session_uuid)
            
            # Convert LangChain messages to WebSocket format
            formatted_history = []
            for msg in history:
                formatted_msg = {
                    "type": "human" if hasattr(msg, 'type') and msg.type == "human" else "ai",
                    "content": msg.content,
                    "timestamp": time.time()  # We'd need to add timestamps to messages
                }
                formatted_history.append(formatted_msg)
            
            # Send history to client
            await websocket.send_text(json.dumps({
                "type": "session_history",
                "session_id": session_id,
                "history": formatted_history,
                "stats": session_stats,
                "timestamp": time.time()
            }))
            
            logger.info(f"📚 MEMORY: Loaded {len(history)} messages for session {session_id}")
            
        except Exception as e:
            logger.error(f"❌ Error loading session: {e}")
            await self.send_error_response(websocket, f"Failed to load session: {e}")

    async def handle_get_session_info(self, websocket: WebSocket):
        """Get current session information"""
        try:
            connection_info = self.connection_sessions.get(websocket, {})
            
            await websocket.send_text(json.dumps({
                "type": "session_info",
                "session_id": connection_info.get("session_id"),
                "user_id": connection_info.get("user_id"),
                "last_activity": connection_info.get("last_activity"),
                "timestamp": time.time()
            }))
            
        except Exception as e:
            logger.error(f"❌ Error getting session info: {e}")

    async def handle_chat_message(self, websocket: WebSocket, content: str, session_id: Optional[str], user_id: Optional[str], context: Dict[str, Any]):
        """Handle incoming chat message with enhanced memory integration"""
        
        # Cancel any existing task for this connection
        if websocket in self.active_tasks:
            old_task = self.active_tasks[websocket]
            if not old_task.done():
                old_task.cancel()
                
        # Create a new task for this generation
        task = asyncio.create_task(self._process_chat_message_with_memory(websocket, content, session_id, user_id, context))
        self.active_tasks[websocket] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info("💬 Chat message processing was cancelled")
            await self.send_generation_stopped(websocket)
        except Exception as e:
            logger.error(f"❌ Error in chat message task: {e}")
            await self.send_error_response(websocket, str(e))
        finally:
            # Clean up task reference
            if websocket in self.active_tasks:
                del self.active_tasks[websocket]
            
            # Clean up callback reference
            if websocket in self.active_callbacks:
                callback = self.active_callbacks[websocket]
                callback.cancel()
                del self.active_callbacks[websocket]

    async def _process_chat_message_with_memory(self, websocket: WebSocket, content: str, session_id: Optional[str], user_id: Optional[str], context: Dict[str, Any]):
        """Process chat message with enhanced memory system integration"""
        try:
            # Get or ensure session
            connection_info = self.connection_sessions.get(websocket, {})
            
            if session_id:
                connection_info["session_id"] = session_id
            if user_id:
                connection_info["user_id"] = user_id
                
            # If no session, create one
            if not connection_info.get("session_id"):
                await self.handle_session_init(websocket, session_id, user_id or "anonymous", {})
                connection_info = self.connection_sessions.get(websocket, {})
            
            active_session_id = connection_info.get("session_id")
            active_user_id = connection_info.get("user_id", "anonymous")
            
            if not active_session_id:
                await self.send_error_response(websocket, "No active session")
                return
            
            # Send response start
            await self.send_response_start(websocket)
            
            # Create streaming callback for real-time updates
            callback = AsyncStreamingCallback(websocket)
            self.active_callbacks[websocket] = callback
            
            # Process with enhanced orchestrator
            enhanced_config = {
                "callbacks": [callback],
                "session_id": active_session_id,
                "user_id": active_user_id
            }
            
            enhanced_context = context.copy()
            enhanced_context.update({
                "websocket_connection": True,
                "streaming": True
            })
            
            # Process with orchestrator using enhanced memory
            try:
                logger.info(f"🧠 Processing message with session {active_session_id}")
                agent_response = await asyncio.wait_for(
                    self.orchestrator.process_request(
                        content, 
                        context=enhanced_context, 
                        config=enhanced_config
                    ),
                    timeout=300  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                logger.warning("⏰ Agent processing timed out")
                await self.send_agent_error(websocket, "assistant", "Response generation timed out")
                return
            
            # Check if task was cancelled during processing
            if asyncio.current_task() and asyncio.current_task().cancelled():
                return
                
            # Check if callback was cancelled
            if callback.is_cancelled:
                logger.info("🛑 Processing stopped due to user cancellation")
                return
            
            if agent_response.success:
                # Stream any remaining content if not already streamed
                if not callback.has_streamed_content and not callback.is_cancelled:
                    await self.stream_agent_content(websocket, "Assistant", agent_response.content, chunk_size=8)
                
                # Send enhanced response with memory metadata
                if not callback.is_cancelled:
                    artifacts = agent_response.artifacts or []
                    
                    # Add memory metadata to response
                    memory_metadata = {
                        "session_id": active_session_id,
                        "memory_loaded": agent_response.metadata.get("memory_loaded", False),
                        "message_count": agent_response.metadata.get("message_count", 0),
                        "primary_agent": agent_response.metadata.get("primary_agent", "general")
                    }
                    
                    await self.send_response_complete_with_memory(
                        websocket, 
                        agent_response.content, 
                        artifacts, 
                        memory_metadata
                    )
            else:
                if not callback.is_cancelled:
                    await self.send_agent_error(websocket, "assistant", agent_response.error or "Failed to process request")
                
            # Update connection activity
            connection_info["last_activity"] = time.time()
            self.connection_sessions[websocket] = connection_info
                
        except asyncio.CancelledError:
            logger.info("💬 Chat message processing was cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Error handling chat message with memory: {e}")
            if not callback.is_cancelled:
                await self.send_error_response(websocket, str(e))

    async def stream_agent_content(self, websocket: WebSocket, agent_name: str, content: str, chunk_size: int = 8):
        """Stream content in real-time chunks with cancellation support."""
        try:
            words = content.split()
            
            for i in range(0, len(words), chunk_size):
                # Check if callback was cancelled
                if websocket in self.active_callbacks:
                    callback = self.active_callbacks[websocket]
                    if callback.is_cancelled:
                        logger.info("Stream content cancelled by user")
                        return
                
                # Check if task was cancelled
                if asyncio.current_task() and asyncio.current_task().cancelled():
                    return
                
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                
                await websocket.send_text(json.dumps({
                    "type": "agent_streaming",
                    "agent": agent_name,
                    "content": chunk,
                    "timestamp": time.time()
                }))
                
                # Small delay for natural streaming effect (but check cancellation after)
                await asyncio.sleep(0.05)
                
        except Exception as e:
            logger.error(f"Error streaming content: {e}")

    async def send_agent_thinking(self, websocket: WebSocket, agent_name: str, status: str):
        """Send agent thinking status."""
        await websocket.send_text(json.dumps({
            "type": "agent_thinking",
            "agent": agent_name,
            "status": status,
            "timestamp": time.time()
        }))

    async def send_agent_error(self, websocket: WebSocket, agent_name: str, error: str):
        """Send agent error."""
        await websocket.send_text(json.dumps({
            "type": "agent_error",
            "agent": agent_name,
            "error": error,
            "timestamp": time.time()
        }))

    async def send_response_start(self, websocket: WebSocket):
        """Send response start indicator."""
        await websocket.send_text(json.dumps({
            "type": "response_start",
            "timestamp": time.time()
        }))

    async def send_response_complete(self, websocket: WebSocket, content: str, artifacts: List):
        """Send response completion."""
        # Send completion signal (without full content to save bandwidth)
        await websocket.send_text(json.dumps({
            "type": "response_complete", 
            "artifacts": [artifact.dict() for artifact in artifacts],
            "timestamp": time.time()
            # Note: content removed to save bandwidth since client already has it from streaming
        }))

    async def send_response_complete_with_memory(self, websocket: WebSocket, content: str, artifacts: List, memory_metadata: Dict[str, Any]):
        """Send response complete with enhanced memory metadata."""
        await websocket.send_text(json.dumps({
            "type": "response_complete",
            "content": content,
            "artifacts": artifacts,
            "memory": memory_metadata,
            "timestamp": time.time()
        }))

    async def handle_stop_generation(self, websocket: WebSocket):
        """Handle stop generation request by cancelling active tasks and callbacks."""
        try:
            # Cancel the callback first to stop token streaming
            if websocket in self.active_callbacks:
                callback = self.active_callbacks[websocket]
                callback.cancel()
                del self.active_callbacks[websocket]
                logger.info("Streaming callback cancelled")
            
            # Then cancel the task
            if websocket in self.active_tasks:
                task = self.active_tasks[websocket]
                if not task.done():
                    # Cancel the task
                    task.cancel()
                    logger.info("Generation task cancelled for WebSocket connection")
                    
                    # Send immediate confirmation
                    await self.send_generation_stopped(websocket)
                else:
                    # Task already completed
                    await websocket.send_text(json.dumps({
                        "type": "generation_stopped",
                        "message": "No active generation to stop",
                        "timestamp": time.time()
                    }))
            else:
                # No active task found
                await websocket.send_text(json.dumps({
                    "type": "generation_stopped", 
                    "message": "No active generation found",
                    "timestamp": time.time()
                }))
                
        except Exception as e:
            logger.error(f"Error stopping generation: {e}")
            await self.send_error_response(websocket, f"Error stopping generation: {str(e)}")

    async def handle_ping(self, websocket: WebSocket):
        """Handle ping request."""
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": time.time()
        }))

    async def send_error_response(self, websocket: WebSocket, error_message: str):
        """Send error response."""
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": error_message,
            "timestamp": time.time()
        }))

    async def send_generation_stopped(self, websocket: WebSocket):
        """Send generation stopped signal."""
        await websocket.send_text(json.dumps({
            "type": "generation_stopped",
            "timestamp": time.time()
        }))


class AsyncStreamingCallback(BaseCallbackHandler):
    """Callback for streaming LLM responses in real-time with cancellation support."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.has_streamed_content = False
        self.current_agent = "Assistant"
        self.is_cancelled = False
        
    def cancel(self):
        """Cancel the streaming callback."""
        self.is_cancelled = True
        logger.info("Streaming callback cancelled")
        
    async def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts generating."""
        if self.is_cancelled:
            return
            
        await self.websocket.send_text(json.dumps({
            "type": "agent_thinking",
            "agent": self.current_agent,
            "status": "Generating response...",
            "timestamp": time.time()
        }))

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated."""
        if self.is_cancelled:
            return
            
        try:
            # Process and clean the token
            processed_token = self._process_token(token)
            
            if processed_token:
                self.has_streamed_content = True
                await self.websocket.send_text(json.dumps({
                    "type": "agent_streaming",
                    "agent": self.current_agent,
                    "content": processed_token,
                    "timestamp": time.time()
                }))
        except Exception as e:
            logger.error(f"Error streaming token: {e}")

    def _process_token(self, token: str) -> str:
        """Process and clean individual tokens while preserving markdown formatting."""
        if self.is_cancelled:
            return ""
            
        # Remove only specific control characters, but preserve newlines for markdown
        cleaned_token = token.replace('\r', '').replace('\x00', '')
        
        # Handle special characters and formatting
        if cleaned_token in ['\n\n']:
            # Double newlines are important for paragraph breaks in markdown
            return '\n\n'
        elif cleaned_token == '\n':
            # Single newlines are also important for line breaks in markdown
            return '\n'
        elif cleaned_token.strip() == '':
            # Only filter out truly empty tokens (spaces, tabs, etc.)
            return cleaned_token if cleaned_token in [' ', '\t'] else ''
        
        return cleaned_token

    def on_llm_end(self, response, **kwargs):
        """Called when LLM finishes generating."""
        # This is synchronous, so we don't send WebSocket messages here
        pass


# WebSocket endpoint
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    manager = ChatWebSocketManager()
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            await manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Global manager instance for access from other modules
chat_websocket_manager = ChatWebSocketManager() 