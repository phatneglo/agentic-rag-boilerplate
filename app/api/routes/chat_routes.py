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
from app.agents.base_agent import AgentResponse

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

async def generate_ai_response_streaming(user_message: str, websocket: WebSocket) -> None:
    """
    Generate true real-time streaming AI response like Claude
    """
    try:
        logger.info(f"Starting real-time streaming for: {user_message[:100]}...")
        
        # Phase 1: Initial thinking
        await send_thinking_update(websocket, "Analyzing your request...")
        await asyncio.sleep(0.5)
        
        # Phase 2: Route selection
        await send_thinking_update(websocket, "Selecting appropriate AI agents...")
        
        # Start response stream
        await websocket.send_text(json.dumps({
            "type": "response_start",
            "timestamp": time.time()
        }))
        
        # Determine response type early for better thinking updates
        response_type = classify_request(user_message)
        
        if response_type == "document":
            await send_thinking_update(websocket, "Preparing document creation...")
            await stream_document_response(user_message, websocket)
        elif response_type == "code":
            await send_thinking_update(websocket, "Analyzing code requirements...")
            await stream_code_response(user_message, websocket)
        elif response_type == "diagram":
            await send_thinking_update(websocket, "Designing diagram structure...")
            await stream_diagram_response(user_message, websocket)
        else:
            await send_thinking_update(websocket, "Formulating response...")
            await stream_general_response(user_message, websocket)
        
        # Send completion
        await websocket.send_text(json.dumps({
            "type": "response_complete",
            "timestamp": time.time()
        }))
        
    except Exception as e:
        logger.error(f"Error in real-time streaming: {e}", exc_info=True)
        await send_error_response(websocket, str(e))

async def send_thinking_update(websocket: WebSocket, status: str):
    """Send thinking status update"""
    await websocket.send_text(json.dumps({
        "type": "thinking_status",
        "status": status,
        "timestamp": time.time()
    }))

async def stream_content_chunks(websocket: WebSocket, content: str, chunk_size: int = 5):
    """Stream content in word chunks with realistic delays"""
    words = content.split(' ')
    current_chunk = ""
    
    for i, word in enumerate(words):
        current_chunk += word + " "
        
        if (i + 1) % chunk_size == 0 or i == len(words) - 1:
            await websocket.send_text(json.dumps({
                "type": "content_chunk",
                "content": current_chunk.strip(),
                "is_final": i == len(words) - 1,
                "timestamp": time.time()
            }))
            current_chunk = ""
            # Realistic typing delay
            await asyncio.sleep(0.1 + (len(current_chunk) * 0.02))

def classify_request(user_message: str) -> str:
    """Quickly classify request type for appropriate streaming"""
    lower_msg = user_message.lower()
    
    if any(word in lower_msg for word in ["email", "document", "letter", "memo", "report"]):
        return "document"
    elif any(word in lower_msg for word in ["code", "function", "python", "javascript", "programming"]):
        return "code"
    elif any(word in lower_msg for word in ["diagram", "chart", "flowchart", "mermaid", "visualize"]):
        return "diagram"
    else:
        return "general"

async def stream_document_response(user_message: str, websocket: WebSocket):
    """Stream document creation response with artifact"""
    # Simulate thinking about document structure
    await send_thinking_update(websocket, "Determining document structure...")
    await asyncio.sleep(1)
    
    # Stream main response
    response_text = "I'll create a structured document for you. Let me build this step by step to ensure it meets your requirements."
    await stream_content_chunks(websocket, response_text)
    
    # Detect and create artifact
    await send_thinking_update(websocket, "Generating document content...")
    await asyncio.sleep(0.5)
    
    # Create specific artifact based on request
    if "email" in user_message.lower():
        artifact_title = "Professional Email Template"
        artifact_content = """Subject: [Your Subject Here]

Dear [Recipient's Name],

I hope this message finds you well.

I am writing to [briefly explain the purpose of your email]. [Provide any necessary details or context that the recipient should know. Be concise but thorough to ensure clarity.]

[If applicable, include any specific requests or questions you have for the recipient. This can be an invitation to a meeting, a request for information, or any other relevant point.]

Thank you for your time and consideration. I look forward to your response.

Best regards,
[Your Name]
[Your Position]
[Your Company]"""
    else:
        artifact_title = "Document Template"
        artifact_content = f"""# Document: {user_message}

## Overview
This document addresses your request regarding: {user_message}

## Key Points
- Point 1: [Detail]
- Point 2: [Detail]  
- Point 3: [Detail]

## Conclusion
[Summary and next steps]"""
    
    await stream_artifact(websocket, "document", artifact_title, artifact_content)

async def stream_code_response(user_message: str, websocket: WebSocket):
    """Stream code response with artifact"""
    await send_thinking_update(websocket, "Writing code solution...")
    await asyncio.sleep(1)
    
    response_text = f"I'll help you with that coding request. Here's a solution for: {user_message}"
    await stream_content_chunks(websocket, response_text)
    
    await send_thinking_update(websocket, "Generating code example...")
    
    # Determine code type
    if "python" in user_message.lower():
        language = "python"
        artifact_title = "Python Solution"
        artifact_content = f'''def solve_problem():
    """
    Solution for: {user_message}
    """
    # Implementation here
    result = "Hello, World!"
    return result

# Example usage
if __name__ == "__main__":
    output = solve_problem()
    print(f"Result: {{output}}")'''
    else:
        language = "javascript"
        artifact_title = "JavaScript Solution"
        artifact_content = f'''function solveProblem() {{
    // Solution for: {user_message}
    const result = "Hello, World!";
    return result;
}}

// Example usage
const output = solveProblem();
console.log(`Result: ${{output}}`);'''
    
    await stream_artifact(websocket, "code", artifact_title, artifact_content, language)

async def stream_diagram_response(user_message: str, websocket: WebSocket):
    """Stream diagram response with artifact"""
    await send_thinking_update(websocket, "Designing diagram layout...")
    await asyncio.sleep(1)
    
    response_text = "I'll create a visual diagram to illustrate your concept. Let me design this step by step."
    await stream_content_chunks(websocket, response_text)
    
    await send_thinking_update(websocket, "Generating diagram code...")
    
    artifact_title = "System Architecture Diagram"
    if "flowchart" in user_message.lower():
        artifact_title = "Process Flowchart"
        artifact_content = '''flowchart TD
    A[Start Process] --> B{Check Condition}
    B -->|Yes| C[Execute Action]
    B -->|No| D[Alternative Path]
    C --> E[Complete Task]
    D --> E
    E --> F[End Process]'''
    else:
        artifact_content = '''graph TD
    A[User Input] --> B[Processing Layer]
    B --> C[Business Logic]
    B --> D[Data Access]
    C --> E[Response Generation]
    D --> F[Database]
    E --> G[User Interface]
    F --> D'''
    
    await stream_artifact(websocket, "mermaid", artifact_title, artifact_content)

async def stream_general_response(user_message: str, websocket: WebSocket):
    """Stream general conversational response"""
    await send_thinking_update(websocket, "Processing your message...")
    await asyncio.sleep(0.8)
    
    # Generate contextual response
    if any(greeting in user_message.lower() for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        response_text = f"Hello! I'm here to help you with any questions or tasks you might have. What would you like to work on today?"
    elif "how are you" in user_message.lower():
        response_text = "I'm doing well, thank you for asking! I'm ready to assist you with coding, writing, analysis, or any other tasks you need help with."
    else:
        response_text = f"I understand you're asking about '{user_message}'. I'm here to help! Could you provide a bit more detail about what specific assistance you need?"
    
    await stream_content_chunks(websocket, response_text)

async def stream_artifact(websocket: WebSocket, artifact_type: str, title: str, content: str, language: str = None):
    """Stream artifact creation with real-time content"""
    artifact_id = f"artifact_{int(time.time() * 1000)}"
    
    # Send artifact start
    artifact_data = {
        "id": artifact_id,
        "type": artifact_type,
        "title": title
    }
    if language:
        artifact_data["language"] = language
    
    await websocket.send_text(json.dumps({
        "type": "artifact_start",
        "artifact": artifact_data,
        "timestamp": time.time()
    }))
    
    # Stream artifact content line by line
    lines = content.split('\n')
    for i, line in enumerate(lines):
        await websocket.send_text(json.dumps({
            "type": "artifact_chunk",
            "artifact_id": artifact_id,
            "content": line + ('\n' if i < len(lines) - 1 else ''),
            "is_final": i == len(lines) - 1,
            "timestamp": time.time()
        }))
        # Faster streaming for code
        await asyncio.sleep(0.03)

async def send_error_response(websocket: WebSocket, error_message: str):
    """Send error response"""
    await websocket.send_text(json.dumps({
        "type": "response_error",
        "content": f"I encountered an issue: {error_message}",
        "error": error_message,
        "timestamp": time.time()
    })) 