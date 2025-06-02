"""
Database models for chat memory and conversation history.
Following LangGraph best practices for conversation persistence.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ChatSession(Base):
    """
    Chat session model for grouping related conversations.
    Follows LangGraph conversation grouping patterns.
    """
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False, default="New Conversation")
    description = Column(Text, nullable=True)
    
    # Session metadata
    user_id = Column(String(255), nullable=True)  # For multi-user support
    session_type = Column(String(50), default="chat")  # chat, document_qa, etc.
    
    # LangGraph configuration
    config = Column(JSON, default=dict)  # Store LangGraph config
    context = Column(JSON, default=dict)  # Store conversation context
    
    # Status and lifecycle
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, title='{self.title}', messages={len(self.messages)})>"


class ChatMessage(Base):
    """
    Individual chat message model compatible with LangGraph message types.
    Stores both user inputs and agent responses with full metadata.
    """
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    
    # Message content and type
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=False)  # 'human', 'ai', 'system', 'function'
    role = Column(String(50), nullable=False, default="user")  # user, assistant, system
    
    # LangGraph message metadata
    message_metadata = Column(JSON, default=dict)  # Store LangGraph message metadata
    additional_kwargs = Column(JSON, default=dict)  # Store additional message kwargs
    
    # Agent and processing information
    agent_name = Column(String(100), nullable=True)  # Which agent processed this
    agent_metadata = Column(JSON, default=dict)  # Agent-specific metadata
    
    # Message sequence and threading
    sequence_number = Column(Integer, nullable=False)  # Order within session
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=True)
    
    # Content analysis and artifacts
    tokens_used = Column(Integer, nullable=True)  # For cost tracking
    processing_time = Column(Integer, nullable=True)  # Processing time in ms
    artifacts = Column(JSON, default=list)  # Store generated artifacts
    
    # Status flags
    is_streamed = Column(Boolean, default=False)  # Was this message streamed?
    is_error = Column(Boolean, default=False)  # Is this an error message?
    is_system = Column(Boolean, default=False)  # Is this a system message?
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    replies = relationship("ChatMessage", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, type='{self.message_type}', content='{self.content[:50]}...')>"
    
    def to_langchain_message(self):
        """
        Convert to LangChain message format for LangGraph compatibility.
        """
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
        
        if self.message_type == "human":
            return HumanMessage(
                content=self.content,
                additional_kwargs=self.additional_kwargs or {},
                id=str(self.id)
            )
        elif self.message_type == "ai":
            return AIMessage(
                content=self.content,
                additional_kwargs=self.additional_kwargs or {},
                id=str(self.id)
            )
        elif self.message_type == "system":
            return SystemMessage(
                content=self.content,
                additional_kwargs=self.additional_kwargs or {},
                id=str(self.id)
            )
        else:
            # Default to HumanMessage for unknown types
            return HumanMessage(
                content=self.content,
                additional_kwargs=self.additional_kwargs or {},
                id=str(self.id)
            )
    
    @classmethod
    def from_langchain_message(cls, message, session_id: uuid.UUID, sequence_number: int, **kwargs):
        """
        Create ChatMessage from LangChain message for LangGraph compatibility.
        """
        message_type_map = {
            "HumanMessage": "human",
            "AIMessage": "ai", 
            "SystemMessage": "system",
            "FunctionMessage": "function",
        }
        
        role_map = {
            "human": "user",
            "ai": "assistant",
            "system": "system",
            "function": "function"
        }
        
        message_type = message_type_map.get(message.__class__.__name__, "human")
        role = role_map.get(message_type, "user")
        
        return cls(
            session_id=session_id,
            content=message.content,
            message_type=message_type,
            role=role,
            sequence_number=sequence_number,
            additional_kwargs=getattr(message, 'additional_kwargs', {}),
            message_metadata=kwargs.get('metadata', {}),
            **kwargs
        ) 