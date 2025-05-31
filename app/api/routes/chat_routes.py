"""
Chat API routes for the AI chat interface.
"""
import asyncio
import time
import json
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.agents import AgentOrchestrator

logger = get_logger(__name__)

# Create router
router = APIRouter()

# Initialize the agent orchestrator
orchestrator = AgentOrchestrator()

# Pydantic models for request/response
class ChatMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: Optional[float] = None

class ChatResponse(BaseModel):
    type: str = "chat_response"
    content: str
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float

class ChatSession(BaseModel):
    title: str
    messages: List[Dict[str, Any]]
    created: str

class UserPreferences(BaseModel):
    theme: str = "light"
    language: str = "en"
    notifications: bool = True
    auto_save: bool = True

# Mock data storage (in production, use proper database)
chat_sessions = {}
user_preferences = {
    "theme": "light",
    "language": "en", 
    "notifications": True,
    "auto_save": True
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

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

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

# WebSocket endpoint is now handled in main.py

async def generate_ai_response(user_message: str) -> Dict[str, Any]:
    """
    Generate AI response using the LangGraph agent orchestrator system
    """
    try:
        logger.info(f"Processing message with agent orchestrator: {user_message[:100]}...")
        
        # Use the orchestrator to process the request
        response = await orchestrator.process_request(user_message)
        
        if response.success:
            return {
                "type": "chat_response",
                "content": response.content,
                "artifacts": response.artifacts,
                "metadata": response.metadata,
                "timestamp": time.time()
            }
        else:
            # Fallback to simple response if orchestrator fails
            logger.warning(f"Orchestrator failed: {response.error}")
            return {
                "type": "chat_response",
                "content": f"I encountered an issue processing your request: {response.error}",
                "artifacts": [],
                "metadata": {"fallback": True},
                "timestamp": time.time()
            }
            
    except Exception as e:
        logger.error(f"Error in generate_ai_response: {e}")
        # Fallback to mock responses
        return await generate_mock_response(user_message)

async def generate_mock_response(user_message: str) -> Dict[str, Any]:
    """
    Fallback mock response generation
    """
    # Simulate AI thinking time
    await asyncio.sleep(1)
    
    # Generate mock response based on user input
    if "code" in user_message.lower() or "python" in user_message.lower():
        return {
            "type": "chat_response",
            "content": f"I'll help you with that coding question: '{user_message}'. Here's a Python example:",
            "artifacts": [
                {
                    "id": f"artifact_{int(time.time())}",
                    "type": "code",
                    "title": "Python Example",
                    "language": "python",
                    "content": """def example_function(param):
    \"\"\"
    Example function based on your request
    \"\"\"
    result = param * 2
    return result

# Usage
output = example_function(5)
print(f"Result: {output}")"""
                }
            ],
            "timestamp": time.time()
        }
    elif "diagram" in user_message.lower() or "mermaid" in user_message.lower():
        return {
            "type": "chat_response", 
            "content": f"I'll create a diagram for your request: '{user_message}'",
            "artifacts": [
                {
                    "id": f"artifact_{int(time.time())}",
                    "type": "mermaid",
                    "title": "System Diagram",
                    "content": """graph TD
    A[User Request] --> B[Processing]
    B --> C[AI Analysis]
    C --> D[Response Generation]
    D --> E[User Interface]
    E --> F[Display Result]"""
                }
            ],
            "timestamp": time.time()
        }
    else:
        return {
            "type": "chat_response",
            "content": f"Thank you for your message: '{user_message}'. I'm here to help you with coding, analysis, writing, and more!",
            "artifacts": [],
            "timestamp": time.time()
        }

@router.post("/message")
async def send_chat_message(message: ChatMessage) -> Dict[str, Any]:
    """
    Send a chat message (HTTP endpoint as fallback to WebSocket)
    """
    try:
        logger.info("Received chat message via HTTP", content_length=len(message.content))
        
        # Generate AI response
        response = await generate_ai_response(message.content)
        
        return {
            "success": True,
            "message": "Message sent successfully",
            "response": response,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error("Error sending chat message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

@router.get("/preferences")
async def get_user_preferences() -> Dict[str, Any]:
    """
    Get user preferences
    """
    return {
        "success": True,
        "preferences": user_preferences
    }

@router.put("/preferences")
async def update_user_preferences(preferences: UserPreferences) -> Dict[str, Any]:
    """
    Update user preferences
    """
    global user_preferences
    user_preferences.update(preferences.dict())
    
    logger.info("User preferences updated", preferences=user_preferences)
    
    return {
        "success": True,
        "message": "Preferences updated successfully",
        "preferences": user_preferences
    }

@router.get("/history")
async def get_chat_history(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """
    Get chat history
    """
    # Mock chat history
    mock_messages = [
        {
            "id": "msg_1",
            "type": "user",
            "content": "Hello, can you help me with Python?",
            "timestamp": "2024-01-01T10:00:00Z"
        },
        {
            "id": "msg_2", 
            "type": "ai",
            "content": "Of course! I'd be happy to help you with Python. What specific topic would you like to explore?",
            "timestamp": "2024-01-01T10:00:05Z"
        }
    ]
    
    return {
        "success": True,
        "messages": mock_messages[offset:offset+limit],
        "total": len(mock_messages)
    }

@router.get("/sessions")
async def list_chat_sessions(limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """
    List chat sessions
    """
    sessions_list = list(chat_sessions.values())[offset:offset+limit]
    
    return {
        "success": True,
        "sessions": sessions_list,
        "total": len(chat_sessions)
    }

@router.post("/sessions")
async def save_chat_session(session: ChatSession) -> Dict[str, Any]:
    """
    Save a chat session
    """
    session_id = f"session_{int(time.time())}"
    chat_sessions[session_id] = {
        "id": session_id,
        "title": session.title,
        "messages": session.messages,
        "created": session.created,
        "updated": time.time()
    }
    
    logger.info("Chat session saved", session_id=session_id, title=session.title)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Session saved successfully"
    }

@router.get("/sessions/{session_id}")
async def get_chat_session(session_id: str) -> Dict[str, Any]:
    """
    Get a specific chat session
    """
    if session_id not in chat_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return {
        "success": True,
        "session": chat_sessions[session_id]
    }

@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: str) -> Dict[str, Any]:
    """
    Delete a chat session
    """
    if session_id not in chat_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    del chat_sessions[session_id]
    
    logger.info("Chat session deleted", session_id=session_id)
    
    return {
        "success": True,
        "message": "Session deleted successfully"
    }

@router.post("/search")
async def search_chat_history(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search chat history
    """
    search_query = query.get("query", "")
    limit = query.get("limit", 20)
    
    # Mock search results
    results = [
        {
            "id": "msg_1",
            "content": f"Found result matching '{search_query}'",
            "session_id": "session_1",
            "timestamp": "2024-01-01T10:00:00Z"
        }
    ]
    
    return {
        "success": True,
        "results": results,
        "total": len(results)
    }

@router.post("/suggestions")
async def get_suggested_responses(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get suggested responses based on context
    """
    suggestions = [
        "Can you explain that in more detail?",
        "Show me an example",
        "What are the alternatives?",
        "How does this work in practice?"
    ]
    
    return {
        "success": True,
        "suggestions": suggestions
    }

@router.post("/process-file")
async def process_file_for_chat(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process uploaded file for chat context
    """
    file_path = file_data.get("file_path")
    
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File path is required"
        )
    
    # Mock file processing
    return {
        "success": True,
        "file_path": file_path,
        "processed": True,
        "summary": f"File {file_path} has been processed and is ready for chat context"
    }

@router.get("/export")
async def export_current_chat(format: str = "json") -> Dict[str, Any]:
    """
    Export current chat session
    """
    if format not in ["json", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export format. Use 'json' or 'txt'"
        )
    
    # Mock export data
    return {
        "success": True,
        "format": format,
        "download_url": f"/api/chat/download/export.{format}"
    }

@router.get("/export/{session_id}")
async def export_chat_session(session_id: str, format: str = "json") -> Dict[str, Any]:
    """
    Export specific chat session
    """
    if session_id not in chat_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if format not in ["json", "txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export format. Use 'json' or 'txt'"
        )
    
    return {
        "success": True,
        "session_id": session_id,
        "format": format,
        "download_url": f"/api/chat/download/{session_id}.{format}"
    }

# Add new endpoint to get agent capabilities
@router.get("/agents/capabilities")
async def get_agent_capabilities() -> Dict[str, Any]:
    """
    Get capabilities of all available agents
    """
    try:
        capabilities = orchestrator.get_agent_capabilities()
        available_agents = orchestrator.get_available_agents()
        
        return {
            "success": True,
            "agents": available_agents,
            "capabilities": capabilities,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting agent capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent capabilities"
        )

# Add endpoint to get agent suggestions for a query
@router.post("/agents/suggestions")
async def get_agent_suggestions(query: Dict[str, str]) -> Dict[str, Any]:
    """
    Get agent suggestions for a specific query
    """
    try:
        user_input = query.get("query", "")
        if not user_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        suggestions = await orchestrator.get_agent_suggestions(user_input)
        
        return {
            "success": True,
            "query": user_input,
            "suggestions": suggestions,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error getting agent suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent suggestions"
        ) 