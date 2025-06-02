"""
Chat Memory API Routes
Provides REST endpoints for managing chat sessions and conversation history.
"""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import get_logger
from app.db.session import get_db
from app.db.memory import PostgresChatMemory
from app.db.models import ChatSession, ChatMessage

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/chat/memory", tags=["chat-memory"])

# Initialize memory system
memory = PostgresChatMemory()


# Pydantic models for requests and responses
class CreateSessionRequest(BaseModel):
    title: str = Field(default="New Conversation", description="Session title")
    user_id: Optional[str] = Field(default=None, description="User ID for multi-user support")
    session_type: str = Field(default="chat", description="Type of session")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Session configuration")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Session context")


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="New session title")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Updated configuration")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Updated context")


class SessionResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    user_id: Optional[str]
    session_type: str
    config: Dict[str, Any]
    context: Dict[str, Any]
    is_active: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    message_count: Optional[int] = None


class MessageResponse(BaseModel):
    id: str
    session_id: str
    content: str
    message_type: str
    role: str
    agent_name: Optional[str]
    agent_metadata: Dict[str, Any]
    sequence_number: int
    artifacts: List[Dict[str, Any]]
    tokens_used: Optional[int]
    processing_time: Optional[int]
    is_streamed: bool
    is_error: bool
    is_system: bool
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageResponse]
    total_messages: int


class SessionStatsResponse(BaseModel):
    session_id: str
    message_counts: Dict[str, int]
    total_messages: int
    total_tokens: int
    created_at: Optional[datetime]
    last_activity: Optional[datetime]


@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: CreateSessionRequest) -> SessionResponse:
    """Create a new chat session."""
    try:
        session = await memory.create_session(
            title=request.title,
            user_id=request.user_id,
            session_type=request.session_type,
            config=request.config,
            context=request.context
        )
        
        logger.info(f"✅ Created new chat session: {session.id}")
        
        return SessionResponse(
            id=str(session.id),
            title=session.title,
            description=session.description,
            user_id=session.user_id,
            session_type=session.session_type,
            config=session.config,
            context=session.context,
            is_active=session.is_active,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity=session.last_activity,
            message_count=0
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(50, ge=1, le=100, description="Number of sessions to return"),
    offset: int = Query(0, ge=0, description="Number of sessions to skip"),
    include_archived: bool = Query(False, description="Include archived sessions")
) -> List[SessionResponse]:
    """List chat sessions with pagination."""
    try:
        sessions = await memory.list_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
            include_archived=include_archived
        )
        
        logger.info(f"📋 Retrieved {len(sessions)} chat sessions")
        
        return [
            SessionResponse(
                id=str(session.id),
                title=session.title,
                description=session.description,
                user_id=session.user_id,
                session_type=session.session_type,
                config=session.config,
                context=session.context,
                is_active=session.is_active,
                is_archived=session.is_archived,
                created_at=session.created_at,
                updated_at=session.updated_at,
                last_activity=session.last_activity,
                message_count=len(session.messages) if hasattr(session, 'messages') and session.messages else None
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(f"❌ Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str = Path(..., description="Session UUID")
) -> SessionResponse:
    """Get a specific chat session."""
    try:
        session_uuid = uuid.UUID(session_id)
        session = await memory.get_session(session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"📄 Retrieved session: {session_id}")
        
        return SessionResponse(
            id=str(session.id),
            title=session.title,
            description=session.description,
            user_id=session.user_id,
            session_type=session.session_type,
            config=session.config,
            context=session.context,
            is_active=session.is_active,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity=session.last_activity,
            message_count=len(session.messages) if session.messages else 0
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to get session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.put("/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str = Path(..., description="Session UUID"),
    request: UpdateSessionRequest = None
) -> SessionResponse:
    """Update a chat session."""
    try:
        session_uuid = uuid.UUID(session_id)
        
        # Update title if provided
        if request.title:
            await memory.update_session_title(session_uuid, request.title)
        
        # Get updated session
        session = await memory.get_session(session_uuid)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"✏️ Updated session: {session_id}")
        
        return SessionResponse(
            id=str(session.id),
            title=session.title,
            description=session.description,
            user_id=session.user_id,
            session_type=session.session_type,
            config=session.config,
            context=session.context,
            is_active=session.is_active,
            is_archived=session.is_archived,
            created_at=session.created_at,
            updated_at=session.updated_at,
            last_activity=session.last_activity,
            message_count=len(session.messages) if session.messages else 0
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to update session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str = Path(..., description="Session UUID")
) -> Dict[str, Any]:
    """Delete a chat session and all its messages."""
    try:
        session_uuid = uuid.UUID(session_id)
        success = await memory.delete_session(session_uuid)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"🗑️ Deleted session: {session_id}")
        
        return {
            "success": True,
            "message": "Session deleted successfully",
            "session_id": session_id
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to delete session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@router.post("/sessions/{session_id}/archive")
async def archive_session(
    session_id: str = Path(..., description="Session UUID")
) -> Dict[str, Any]:
    """Archive a chat session (soft delete)."""
    try:
        session_uuid = uuid.UUID(session_id)
        success = await memory.archive_session(session_uuid)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        logger.info(f"📦 Archived session: {session_id}")
        
        return {
            "success": True,
            "message": "Session archived successfully",
            "session_id": session_id
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to archive session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive session: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=ConversationHistoryResponse)
async def get_conversation_history(
    session_id: str = Path(..., description="Session UUID"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of messages"),
    message_types: Optional[List[str]] = Query(None, description="Filter by message types")
) -> ConversationHistoryResponse:
    """Get conversation history for a session."""
    try:
        session_uuid = uuid.UUID(session_id)
        messages = await memory.get_messages(
            session_uuid,
            limit=limit,
            message_types=message_types
        )
        
        logger.info(f"💬 Retrieved {len(messages)} messages for session: {session_id}")
        
        message_responses = [
            MessageResponse(
                id=str(msg.id),
                session_id=str(msg.session_id),
                content=msg.content,
                message_type=msg.message_type,
                role=msg.role,
                agent_name=msg.agent_name,
                agent_metadata=msg.agent_metadata,
                sequence_number=msg.sequence_number,
                artifacts=msg.artifacts,
                tokens_used=msg.tokens_used,
                processing_time=msg.processing_time,
                is_streamed=msg.is_streamed,
                is_error=msg.is_error,
                is_system=msg.is_system,
                created_at=msg.created_at
            )
            for msg in messages
        ]
        
        return ConversationHistoryResponse(
            session_id=session_id,
            messages=message_responses,
            total_messages=len(message_responses)
        )
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to get conversation history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {str(e)}")


@router.delete("/sessions/{session_id}/messages")
async def clear_conversation_history(
    session_id: str = Path(..., description="Session UUID")
) -> Dict[str, Any]:
    """Clear all messages from a session."""
    try:
        session_uuid = uuid.UUID(session_id)
        success = await memory.clear_session(session_uuid)
        
        logger.info(f"🧹 Cleared conversation history for session: {session_id}")
        
        return {
            "success": success,
            "message": "Conversation history cleared successfully",
            "session_id": session_id
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to clear conversation history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")


@router.get("/sessions/{session_id}/stats", response_model=SessionStatsResponse)
async def get_session_stats(
    session_id: str = Path(..., description="Session UUID")
) -> SessionStatsResponse:
    """Get statistics for a chat session."""
    try:
        session_uuid = uuid.UUID(session_id)
        stats = await memory.get_session_stats(session_uuid)
        
        logger.info(f"📊 Retrieved stats for session: {session_id}")
        
        return SessionStatsResponse(**stats)
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")
    except Exception as e:
        logger.error(f"❌ Failed to get session stats for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session stats: {str(e)}")


@router.get("/health")
async def memory_health_check() -> Dict[str, Any]:
    """Health check for the memory system."""
    try:
        from app.db.session import test_connection
        
        # Test database connection
        db_healthy = await test_connection()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "memory_system": "operational",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Memory health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "memory_system": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 