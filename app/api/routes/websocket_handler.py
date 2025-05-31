"""
WebSocket handler for real-time multi-agent chat streaming
"""
import asyncio
import json
import time
from typing import Dict, List, Any
from fastapi import WebSocket, WebSocketDisconnect
from langchain.callbacks.base import BaseCallbackHandler
from app.core.logging_config import get_logger
from app.agents.agent_orchestrator import AgentOrchestrator

logger = get_logger(__name__)

class ChatWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.orchestrator = AgentOrchestrator()
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established")

    def disconnect(self, websocket: WebSocket):
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
        try:
            # Send response start immediately
            await self.send_response_start(websocket)
            
            # Create streaming callback for real-time updates
            callback = AsyncStreamingCallback(websocket)
            
            # Process with orchestrator using streaming
            config = {"callbacks": [callback]}
            agent_response = await self.orchestrator.process_request(content, config=config)
            
            if agent_response.success:
                # Stream any remaining content if not already streamed
                if not callback.has_streamed_content:
                    await self.stream_agent_content(websocket, "Assistant", agent_response.content, chunk_size=8)
                
                # Send artifacts if available
                artifacts = agent_response.artifacts or []
                
                # Complete with final response
                await self.send_response_complete(websocket, agent_response.content, artifacts)
            else:
                await self.send_agent_error(websocket, "assistant", agent_response.error or "Failed to process request")
                
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            await self.send_error_response(websocket, str(e))

    async def stream_agent_content(self, websocket: WebSocket, agent_name: str, content: str, chunk_size: int = 8):
        """Stream content in real-time chunks."""
        try:
            words = content.split()
            
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                if i + chunk_size < len(words):
                    chunk += " "
                
                await websocket.send_text(json.dumps({
                    "type": "agent_streaming",
                    "agent": agent_name,
                    "content": chunk,
                    "timestamp": time.time()
                }))
                
                # Small delay for natural streaming effect
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
        """Handle stop generation request."""
        await websocket.send_text(json.dumps({
            "type": "generation_stopped",
            "timestamp": time.time()
        }))

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


class AsyncStreamingCallback(BaseCallbackHandler):
    """Callback for streaming LLM responses in real-time."""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.has_streamed_content = False
        self.current_agent = "Assistant"
        
    async def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when LLM starts generating."""
        await self.websocket.send_text(json.dumps({
            "type": "agent_thinking",
            "agent": self.current_agent,
            "status": "Generating response...",
            "timestamp": time.time()
        }))

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated."""
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