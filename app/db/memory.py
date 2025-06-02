"""
LangGraph-compatible PostgreSQL chat memory implementation.
Provides conversation history management for LangGraph workflows.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Sequence
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.core.logging_config import get_logger
from .models import ChatSession, ChatMessage
from .session import get_session_factory, run_db_operation

logger = get_logger(__name__)


class PostgresChatMemory:
    """
    PostgreSQL-based chat memory compatible with LangGraph.
    Provides conversation history management and retrieval.
    """
    
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session_factory()
    
    async def create_session(
        self,
        title: str = "New Conversation",
        user_id: Optional[str] = None,
        session_type: str = "chat",
        config: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> ChatSession:
        """Create a new chat session."""
        
        async def _create_session(session: AsyncSession):
            chat_session = ChatSession(
                title=title,
                user_id=user_id,
                session_type=session_type,
                config=config or {},
                context=context or {}
            )
            session.add(chat_session)
            await session.flush()  # Get the ID
            return chat_session
        
        return await run_db_operation(_create_session)
    
    async def get_session(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        """Get a chat session by ID."""
        
        async def _get_session(session: AsyncSession):
            result = await session.execute(
                select(ChatSession)
                .options(selectinload(ChatSession.messages))
                .where(ChatSession.id == session_id)
            )
            return result.scalar_one_or_none()
        
        return await run_db_operation(_get_session)
    
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False
    ) -> List[ChatSession]:
        """List chat sessions with pagination."""
        
        async def _list_sessions(session: AsyncSession):
            query = select(ChatSession).order_by(desc(ChatSession.last_activity))
            
            # Filter by user if provided
            if user_id:
                query = query.where(ChatSession.user_id == user_id)
            
            # Filter archived sessions
            if not include_archived:
                query = query.where(ChatSession.is_archived == False)
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
        
        return await run_db_operation(_list_sessions)
    
    async def add_message(
        self,
        session_id: uuid.UUID,
        message: BaseMessage,
        agent_name: Optional[str] = None,
        agent_metadata: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        tokens_used: Optional[int] = None,
        processing_time: Optional[int] = None
    ) -> ChatMessage:
        """Add a message to the conversation history."""
        
        async def _add_message(session: AsyncSession):
            # Get current message count for sequence number
            result = await session.execute(
                select(func.count(ChatMessage.id))
                .where(ChatMessage.session_id == session_id)
            )
            sequence_number = result.scalar() + 1
            
            # Create message from LangChain message
            chat_message = ChatMessage.from_langchain_message(
                message=message,
                session_id=session_id,
                sequence_number=sequence_number,
                agent_name=agent_name,
                agent_metadata=agent_metadata or {},
                artifacts=artifacts or [],
                tokens_used=tokens_used,
                processing_time=processing_time
            )
            
            session.add(chat_message)
            
            # Update session last activity
            await session.execute(
                select(ChatSession)
                .where(ChatSession.id == session_id)
            )
            chat_session = await session.get(ChatSession, session_id)
            if chat_session:
                chat_session.last_activity = datetime.utcnow()
            
            await session.flush()
            return chat_message
        
        return await run_db_operation(_add_message)
    
    async def add_messages(
        self,
        session_id: uuid.UUID,
        messages: List[BaseMessage],
        agent_name: Optional[str] = None,
        agent_metadata: Optional[Dict[str, Any]] = None
    ) -> List[ChatMessage]:
        """Add multiple messages to the conversation history."""
        
        added_messages = []
        for message in messages:
            chat_message = await self.add_message(
                session_id=session_id,
                message=message,
                agent_name=agent_name,
                agent_metadata=agent_metadata
            )
            added_messages.append(chat_message)
        
        return added_messages
    
    async def get_messages(
        self,
        session_id: uuid.UUID,
        limit: Optional[int] = None,
        message_types: Optional[List[str]] = None
    ) -> List[ChatMessage]:
        """Get messages from a conversation session."""
        
        async def _get_messages(session: AsyncSession):
            query = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.sequence_number)
            )
            
            # Filter by message types if provided
            if message_types:
                query = query.where(ChatMessage.message_type.in_(message_types))
            
            # Apply limit if provided
            if limit:
                query = query.limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
        
        return await run_db_operation(_get_messages)
    
    async def get_conversation_history(
        self,
        session_id: uuid.UUID,
        limit: Optional[int] = None
    ) -> List[BaseMessage]:
        """
        Get conversation history as LangChain messages for LangGraph compatibility.
        """
        messages = await self.get_messages(session_id, limit=limit)
        return [msg.to_langchain_message() for msg in messages]
    
    async def clear_session(self, session_id: uuid.UUID) -> bool:
        """Clear all messages from a session."""
        
        async def _clear_session(session: AsyncSession):
            await session.execute(
                ChatMessage.__table__.delete()
                .where(ChatMessage.session_id == session_id)
            )
            return True
        
        return await run_db_operation(_clear_session)
    
    async def delete_session(self, session_id: uuid.UUID) -> bool:
        """Delete a session and all its messages."""
        
        async def _delete_session(session: AsyncSession):
            # Delete messages first (cascade should handle this, but being explicit)
            await session.execute(
                ChatMessage.__table__.delete()
                .where(ChatMessage.session_id == session_id)
            )
            
            # Delete session
            await session.execute(
                ChatSession.__table__.delete()
                .where(ChatSession.id == session_id)
            )
            return True
        
        return await run_db_operation(_delete_session)
    
    async def archive_session(self, session_id: uuid.UUID) -> bool:
        """Archive a session (soft delete)."""
        
        async def _archive_session(session: AsyncSession):
            chat_session = await session.get(ChatSession, session_id)
            if chat_session:
                chat_session.is_archived = True
                chat_session.is_active = False
                return True
            return False
        
        return await run_db_operation(_archive_session)
    
    async def update_session_title(self, session_id: uuid.UUID, title: str) -> bool:
        """Update session title."""
        
        async def _update_title(session: AsyncSession):
            chat_session = await session.get(ChatSession, session_id)
            if chat_session:
                chat_session.title = title
                return True
            return False
        
        return await run_db_operation(_update_title)
    
    async def get_session_stats(self, session_id: uuid.UUID) -> Dict[str, Any]:
        """Get statistics for a session."""
        
        async def _get_stats(session: AsyncSession):
            # Get message counts by type
            result = await session.execute(
                select(
                    ChatMessage.message_type,
                    func.count(ChatMessage.id).label('count')
                )
                .where(ChatMessage.session_id == session_id)
                .group_by(ChatMessage.message_type)
            )
            
            message_counts = {row.message_type: row.count for row in result}
            
            # Get total tokens used
            result = await session.execute(
                select(func.sum(ChatMessage.tokens_used))
                .where(
                    and_(
                        ChatMessage.session_id == session_id,
                        ChatMessage.tokens_used.isnot(None)
                    )
                )
            )
            total_tokens = result.scalar() or 0
            
            # Get session info
            chat_session = await session.get(ChatSession, session_id)
            
            return {
                "session_id": str(session_id),
                "message_counts": message_counts,
                "total_messages": sum(message_counts.values()),
                "total_tokens": total_tokens,
                "created_at": chat_session.created_at if chat_session else None,
                "last_activity": chat_session.last_activity if chat_session else None
            }
        
        return await run_db_operation(_get_stats) 