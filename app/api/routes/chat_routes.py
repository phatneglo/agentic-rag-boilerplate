"""
Chat WebSocket Routes
Provides WebSocket endpoints for real-time multi-agent chat.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List
import json
import uuid
from datetime import datetime

from app.core.logging_config import get_logger
from app.services.chat_service import chat_service, ChatEvent

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("WebSocket connected", session_id=session_id, total_connections=len(self.active_connections))
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("WebSocket disconnected", session_id=session_id, total_connections=len(self.active_connections))
    
    async def send_event(self, session_id: str, event: ChatEvent):
        """Send event to specific WebSocket"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(event.to_json())
            except Exception as e:
                logger.error("Failed to send WebSocket event", error=str(e), session_id=session_id)
                self.disconnect(session_id)
                # Re-raise the exception so calling code knows the connection failed
                raise

# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat with multi-agent system.
    
    **Usage:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/chat/ws/your-session-id');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Event:', data.event_type, 'Content:', data.content);
    };
    
    ws.send(JSON.stringify({message: "Hello, search for documents about Baguio"}));
    ```
    
    **Event Types:**
    - `system_ready`: System initialization complete
    - `processing_start`: Processing user message
    - `agent_switch`: Agent handoff (ChatAgent -> KnowledgeBaseAgent)
    - `tool_call`: Tool being executed
    - `tool_result`: Tool execution result
    - `agent_response`: Agent response to user
    - `stream_token`: Real-time streaming token
    - `processing_complete`: Request completed
    - `error`: Error occurred
    """
    try:
        # Connect to WebSocket
        await manager.connect(websocket, session_id)
        
        # Send welcome message
        welcome_event = ChatEvent(
            "system_ready",
            f"🤖 Multi-Agent Chat System Ready! Session: {session_id}",
            mode="output"
        )
        await manager.send_event(session_id, welcome_event)
        
        # Listen for messages
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                user_message = message_data.get('message', '')
                
                if not user_message:
                    continue
                
                logger.info("Received chat message", message=user_message[:100], session_id=session_id)
                
                # Create callback to send events in real-time
                async def emit_event_callback(event: ChatEvent):
                    try:
                        await manager.send_event(session_id, event)
                    except Exception as e:
                        logger.warning("Failed to send event, client may be disconnected", 
                                     error=str(e), session_id=session_id)
                        raise
                
                # Process message with streaming
                async for event in chat_service.process_message_stream(
                    user_message, 
                    session_id,
                    emit_event_callback
                ):
                    # Events are already sent via callback, but we can log them
                    logger.debug("Chat event generated", 
                               event_type=event.event_type, 
                               session_id=session_id)
                
            except WebSocketDisconnect:
                # Client disconnected during message processing
                logger.info("WebSocket disconnected during message processing", session_id=session_id)
                break
            except json.JSONDecodeError:
                try:
                    error_event = ChatEvent("error", "Invalid JSON format", mode="error")
                    await manager.send_event(session_id, error_event)
                except Exception:
                    # If we can't send error, client is likely disconnected
                    logger.info("Cannot send error message, client disconnected", session_id=session_id)
                    break
            except Exception as e:
                logger.error("Error processing chat message", error=str(e), session_id=session_id)
                try:
                    error_event = ChatEvent("error", f"Error: {str(e)}", mode="error")
                    await manager.send_event(session_id, error_event)
                except Exception:
                    # If we can't send error, client is likely disconnected
                    logger.info("Cannot send error message, client disconnected", session_id=session_id)
                    break
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e), session_id=session_id)
    finally:
        # Always clean up the connection
        manager.disconnect(session_id)
        logger.info("WebSocket connection cleaned up", session_id=session_id)


@router.get("/demo")
async def chat_demo():
    """
    Demo HTML page for testing WebSocket chat functionality.
    """
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Agent Chat Demo</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: #007bff;
                color: white;
                padding: 20px;
                text-align: center;
            }
            .chat-container {
                height: 500px;
                overflow-y: auto;
                padding: 20px;
                background: #f8f9fa;
            }
            .message {
                margin: 10px 0;
                padding: 10px 15px;
                border-radius: 18px;
                max-width: 80%;
                word-wrap: break-word;
            }
            .user-message {
                background: #007bff;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            .agent-message {
                background: white;
                border: 1px solid #dee2e6;
            }
            .thinking-message {
                background: #fff3cd;
                border: 1px solid #ffeaa7;
                font-style: italic;
                opacity: 0.8;
            }
            .error-message {
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }
            .input-container {
                padding: 20px;
                border-top: 1px solid #dee2e6;
                display: flex;
                gap: 10px;
            }
            .message-input {
                flex: 1;
                padding: 12px;
                border: 1px solid #dee2e6;
                border-radius: 25px;
                outline: none;
                font-size: 14px;
            }
            .send-button {
                padding: 12px 24px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-size: 14px;
            }
            .send-button:hover {
                background: #0056b3;
            }
            .send-button:disabled {
                background: #6c757d;
                cursor: not-allowed;
            }
            .status {
                padding: 10px 20px;
                text-align: center;
                font-size: 12px;
                color: #6c757d;
                border-top: 1px solid #dee2e6;
            }
            .agent-indicator {
                font-size: 12px;
                color: #6c757d;
                margin-bottom: 5px;
            }
            .typing-indicator {
                padding: 10px 15px;
                background: #e9ecef;
                border-radius: 18px;
                max-width: 80%;
                animation: pulse 1.5s infinite;
            }
            @keyframes pulse {
                0% { opacity: 0.6; }
                50% { opacity: 1; }
                100% { opacity: 0.6; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 Multi-Agent Chat System</h1>
                <p>Real-time streaming chat with document search capabilities</p>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message thinking-message">
                    <div class="agent-indicator">System</div>
                    Connecting to chat service...
                </div>
            </div>
            
            <div class="input-container">
                <input 
                    type="text" 
                    id="messageInput" 
                    class="message-input" 
                    placeholder="Type your message... (e.g., 'Hello, search for documents about Baguio')"
                    disabled
                >
                <button id="sendButton" class="send-button" disabled>Send</button>
            </div>
            
            <div class="status" id="status">
                Connecting...
            </div>
        </div>

        <script>
            const chatContainer = document.getElementById('chatContainer');
            const messageInput = document.getElementById('messageInput');
            const sendButton = document.getElementById('sendButton');
            const status = document.getElementById('status');
            
            // Generate session ID
            const sessionId = 'demo_' + Math.random().toString(36).substr(2, 9);
            
            // WebSocket connection
            const ws = new WebSocket(`ws://localhost:8000/chat/ws/${sessionId}`);
            
            let isTyping = false;
            let typingElement = null;
            
            ws.onopen = function() {
                status.textContent = `Connected - Session: ${sessionId}`;
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
                
                // Clear connecting message
                chatContainer.innerHTML = '';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleChatEvent(data);
            };
            
            ws.onclose = function() {
                status.textContent = 'Disconnected';
                messageInput.disabled = true;
                sendButton.disabled = true;
                addMessage('Connection closed', 'error-message');
            };
            
            ws.onerror = function(error) {
                status.textContent = 'Connection error';
                addMessage('Connection error: ' + error, 'error-message');
            };
            
            function handleChatEvent(data) {
                const { event_type, content, user, tool, mode } = data;
                
                switch(event_type) {
                    case 'system_ready':
                        addMessage(content, 'thinking-message', 'System');
                        break;
                        
                    case 'processing_start':
                        startTyping('Processing...');
                        break;
                        
                    case 'agent_switch':
                        updateTyping(`${user} is thinking...`);
                        break;
                        
                    case 'tool_call':
                        updateTyping(`${user} is using ${tool}...`);
                        break;
                        
                    case 'agent_response':
                        stopTyping();
                        addMessage(content, 'agent-message', user);
                        break;
                        
                    case 'tool_result':
                        stopTyping();
                        addMessage(content, 'agent-message', user, '🔍 Search Results');
                        break;
                        
                    case 'stream_token':
                        // Handle real-time streaming if needed
                        break;
                        
                    case 'processing_complete':
                        stopTyping();
                        break;
                        
                    case 'error':
                        stopTyping();
                        addMessage(content, 'error-message', 'Error');
                        break;
                        
                    default:
                        if (mode === 'thinking') {
                            updateTyping(content);
                        } else if (mode === 'output') {
                            stopTyping();
                            addMessage(content, 'agent-message', user);
                        }
                }
            }
            
            function addMessage(content, className, agent = null, prefix = null) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${className}`;
                
                let html = '';
                if (agent) {
                    html += `<div class="agent-indicator">${agent}</div>`;
                }
                if (prefix) {
                    html += `<strong>${prefix}</strong><br>`;
                }
                html += content.replace(/\\n/g, '<br>');
                
                messageDiv.innerHTML = html;
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function startTyping(message) {
                if (!isTyping) {
                    typingElement = document.createElement('div');
                    typingElement.className = 'typing-indicator';
                    typingElement.textContent = message;
                    chatContainer.appendChild(typingElement);
                    isTyping = true;
                }
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function updateTyping(message) {
                if (typingElement) {
                    typingElement.textContent = message;
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            
            function stopTyping() {
                if (isTyping && typingElement) {
                    typingElement.remove();
                    isTyping = false;
                    typingElement = null;
                }
            }
            
            function sendMessage() {
                const message = messageInput.value.trim();
                if (message && ws.readyState === WebSocket.OPEN) {
                    // Add user message to chat
                    addMessage(message, 'user-message', 'You');
                    
                    // Send to WebSocket
                    ws.send(JSON.stringify({message: message}));
                    
                    // Clear input
                    messageInput.value = '';
                }
            }
            
            // Event listeners
            sendButton.addEventListener('click', sendMessage);
            
            messageInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                }
            });
            
            // Focus input when page loads
            messageInput.focus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/health")
async def chat_health():
    """Health check for chat service."""
    try:
        # Test chat service initialization
        if chat_service.workflow is None:
            raise HTTPException(status_code=503, detail="Chat service not initialized")
        
        return {
            "status": "healthy",
            "service": "chat",
            "active_connections": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error("Chat health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=f"Chat service unhealthy: {str(e)}")


@router.get("/sessions")
async def get_active_sessions():
    """Get list of active chat sessions."""
    return {
        "active_sessions": list(manager.active_connections.keys()),
        "total_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    } 