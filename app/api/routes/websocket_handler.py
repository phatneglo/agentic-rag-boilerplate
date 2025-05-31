"""
WebSocket handler for real-time multi-agent chat streaming
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from langchain.callbacks.base import BaseCallbackHandler
from app.core.logging_config import get_logger
from app.agents.agent_orchestrator import AgentOrchestrator

logger = get_logger(__name__)

class ChatWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.orchestrator = AgentOrchestrator()
        self.active_tasks: Dict[WebSocket, asyncio.Task] = {}  # Track active generation tasks
        self.active_callbacks: Dict[WebSocket, AsyncStreamingCallback] = {}  # Track active callbacks
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established")

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
            
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("WebSocket connection closed")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def handle_message(self, websocket: WebSocket, data: str):
        """Handle incoming WebSocket messages with proper streaming"""
        try:
            message_data = json.loads(data)
            logger.info("Received WebSocket message", message_type=message_data.get("type"))
            
            if message_data.get("type") == "chat_message":
                await self.handle_chat_message(websocket, message_data.get("content", ""))
            elif message_data.get("type") == "stop_generation":
                await self.handle_stop_generation(websocket)
            elif message_data.get("type") == "ping":
                await self.handle_ping(websocket)
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket")
        except Exception as e:
            logger.error("Error processing WebSocket message", error=str(e))
            await self.send_error_response(websocket, str(e))

    async def handle_chat_message(self, websocket: WebSocket, content: str):
        """Handle incoming chat message with real-time streaming using LangGraph orchestrator"""
        
        # Cancel any existing task for this connection
        if websocket in self.active_tasks:
            old_task = self.active_tasks[websocket]
            if not old_task.done():
                old_task.cancel()
                
        # Create a new task for this generation
        task = asyncio.create_task(self._process_chat_message(websocket, content))
        self.active_tasks[websocket] = task
        
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Chat message processing was cancelled")
            await self.send_generation_stopped(websocket)
        except Exception as e:
            logger.error(f"Error in chat message task: {e}")
            await self.send_error_response(websocket, str(e))
        finally:
            # Clean up task reference
            if websocket in self.active_tasks:
                del self.active_tasks[websocket]
            
            # Clean up callback reference
            if websocket in self.active_callbacks:
                callback = self.active_callbacks[websocket]
                callback.cancel()  # Ensure it's cancelled
                del self.active_callbacks[websocket]

    async def _process_chat_message(self, websocket: WebSocket, content: str):
        """Internal method to process the chat message with proper cancellation support"""
        try:
            # Send response start immediately
            await self.send_response_start(websocket)
            
            # Create streaming callback for real-time updates
            callback = AsyncStreamingCallback(websocket)
            self.active_callbacks[websocket] = callback
            
            # Process with orchestrator using streaming with cancellation checks
            config = {"callbacks": [callback]}
            
            # Wrap the orchestrator call to support cancellation
            try:
                agent_response = await asyncio.wait_for(
                    self.orchestrator.process_request(content, config=config),
                    timeout=300  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Agent processing timed out")
                await self.send_agent_error(websocket, "assistant", "Response generation timed out")
                return
            
            # Check if task was cancelled during processing
            if asyncio.current_task() and asyncio.current_task().cancelled():
                return
                
            # Check if callback was cancelled
            if callback.is_cancelled:
                logger.info("Processing stopped due to user cancellation")
                return
            
            if agent_response.success:
                # Stream any remaining content if not already streamed
                if not callback.has_streamed_content and not callback.is_cancelled:
                    await self.stream_agent_content(websocket, "Assistant", agent_response.content, chunk_size=8)
                
                # Send artifacts if available and not cancelled
                if not callback.is_cancelled:
                    artifacts = agent_response.artifacts or []
                    await self.send_response_complete(websocket, agent_response.content, artifacts)
            else:
                if not callback.is_cancelled:
                    await self.send_agent_error(websocket, "assistant", agent_response.error or "Failed to process request")
                
        except asyncio.CancelledError:
            # Re-raise cancellation to properly handle it
            logger.info("Chat message processing was cancelled")
            raise
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
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