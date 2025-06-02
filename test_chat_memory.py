#!/usr/bin/env python3
"""
Test script for PostgreSQL Chat Memory with LangGraph integration.
Demonstrates the full chat memory functionality following LangGraph best practices.
"""

import asyncio
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.db.session import init_db, test_connection
from app.db.memory import PostgresChatMemory
from app.agents.agent_orchestrator import AgentOrchestrator


async def test_database_setup():
    """Test basic database setup and connection."""
    print("🔧 Testing Database Setup")
    print("=" * 50)
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized successfully")
        
        # Test connection
        connection_ok = await test_connection()
        if connection_ok:
            print("✅ Database connection test passed")
        else:
            print("❌ Database connection test failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


async def test_basic_memory_operations():
    """Test basic chat memory operations."""
    print("\n💾 Testing Basic Memory Operations")
    print("=" * 50)
    
    try:
        memory = PostgresChatMemory()
        
        # 1. Create a session
        session = await memory.create_session(
            title="Test Conversation",
            user_id="test_user_001",
            session_type="chat",
            config={"model": "gpt-4o-mini", "temperature": 0.7},
            context={"test": True}
        )
        print(f"✅ Created session: {session.id}")
        
        # 2. Add messages
        user_msg = HumanMessage(content="Hello, how are you?")
        await memory.add_message(
            session_id=session.id,
            message=user_msg,
            agent_name="user"
        )
        print("✅ Added user message")
        
        ai_msg = AIMessage(content="Hello! I'm doing well, thank you for asking. How can I help you today?")
        await memory.add_message(
            session_id=session.id,
            message=ai_msg,
            agent_name="general_agent",
            agent_metadata={"confidence": 0.95},
            tokens_used=25,
            processing_time=150
        )
        print("✅ Added AI message")
        
        # 3. Retrieve conversation history
        history = await memory.get_conversation_history(session.id)
        print(f"✅ Retrieved {len(history)} messages from history")
        
        for i, msg in enumerate(history):
            print(f"   {i+1}. {msg.__class__.__name__}: {msg.content[:50]}...")
        
        # 4. Get session stats
        stats = await memory.get_session_stats(session.id)
        print(f"✅ Session stats: {stats['total_messages']} messages, {stats['total_tokens']} tokens")
        
        # 5. List sessions
        sessions = await memory.list_sessions(user_id="test_user_001")
        print(f"✅ Found {len(sessions)} sessions for user")
        
        return session.id
        
    except Exception as e:
        print(f"❌ Memory operations failed: {e}")
        return None


async def test_langgraph_integration(session_id: uuid.UUID):
    """Test LangGraph integration with PostgreSQL memory."""
    print("\n🤖 Testing LangGraph Integration")
    print("=" * 50)
    
    try:
        orchestrator = AgentOrchestrator()
        
        # Test 1: Process request with memory
        print("Testing agent orchestration with memory...")
        
        response = await orchestrator.process_request(
            user_input="Can you write a simple Python function to calculate fibonacci numbers?",
            context={"use_memory": True},
            config={"session_id": str(session_id)}
        )
        
        if response.success:
            print("✅ Agent response generated successfully")
            print(f"   Agent: {response.metadata.get('primary_agent', 'unknown')}")
            print(f"   Content: {response.content[:100]}...")
        else:
            print(f"❌ Agent response failed: {response.error}")
        
        # Test 2: Check if memory was updated
        memory = PostgresChatMemory()
        history = await memory.get_conversation_history(session_id)
        print(f"✅ Memory now contains {len(history)} messages")
        
        # Test 3: Continue conversation with context
        response2 = await orchestrator.process_request(
            user_input="Can you make that function recursive?",
            context={"use_memory": True},
            config={"session_id": str(session_id)}
        )
        
        if response2.success:
            print("✅ Follow-up response with context generated")
            print(f"   Content: {response2.content[:100]}...")
        
        # Final memory check
        final_history = await memory.get_conversation_history(session_id)
        print(f"✅ Final memory contains {len(final_history)} messages")
        
        return True
        
    except Exception as e:
        print(f"❌ LangGraph integration failed: {e}")
        return False


async def test_advanced_memory_features(session_id: uuid.UUID):
    """Test advanced memory features."""
    print("\n🔍 Testing Advanced Memory Features")
    print("=" * 50)
    
    try:
        memory = PostgresChatMemory()
        
        # 1. Test message filtering
        ai_messages = await memory.get_messages(session_id, message_types=["ai"])
        human_messages = await memory.get_messages(session_id, message_types=["human"])
        
        print(f"✅ Found {len(ai_messages)} AI messages and {len(human_messages)} human messages")
        
        # 2. Test session update
        success = await memory.update_session_title(session_id, "Updated Test Conversation - LangGraph Demo")
        print(f"✅ Session title update: {'success' if success else 'failed'}")
        
        # 3. Test session archiving
        success = await memory.archive_session(session_id)
        print(f"✅ Session archiving: {'success' if success else 'failed'}")
        
        # 4. Test listing with archived sessions
        all_sessions = await memory.list_sessions(include_archived=True)
        active_sessions = await memory.list_sessions(include_archived=False)
        
        print(f"✅ Total sessions: {len(all_sessions)}, Active sessions: {len(active_sessions)}")
        
        # 5. Test session stats
        stats = await memory.get_session_stats(session_id)
        print(f"✅ Final session stats:")
        print(f"   - Total messages: {stats['total_messages']}")
        print(f"   - Message types: {stats['message_counts']}")
        print(f"   - Total tokens: {stats['total_tokens']}")
        print(f"   - Duration: {stats['last_activity']} - {stats['created_at']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Advanced memory features failed: {e}")
        return False


async def test_cleanup(session_id: uuid.UUID):
    """Clean up test data."""
    print("\n🧹 Cleaning Up Test Data")
    print("=" * 50)
    
    try:
        memory = PostgresChatMemory()
        
        # Delete the test session
        success = await memory.delete_session(session_id)
        print(f"✅ Test session cleanup: {'success' if success else 'failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False


async def run_comprehensive_test():
    """Run the comprehensive chat memory test suite."""
    print("🚀 PostgreSQL Chat Memory Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.utcnow()}")
    print()
    
    # Test 1: Database setup
    if not await test_database_setup():
        print("❌ Database setup failed, aborting tests")
        return
    
    # Test 2: Basic memory operations
    session_id = await test_basic_memory_operations()
    if not session_id:
        print("❌ Basic memory operations failed, aborting tests")
        return
    
    # Test 3: LangGraph integration
    if not await test_langgraph_integration(session_id):
        print("❌ LangGraph integration failed")
    
    # Test 4: Advanced features
    if not await test_advanced_memory_features(session_id):
        print("❌ Advanced memory features failed")
    
    # Test 5: Cleanup
    if not await test_cleanup(session_id):
        print("❌ Cleanup failed")
    
    print("\n🎉 Test Suite Complete!")
    print("=" * 60)
    print(f"Finished at: {datetime.utcnow()}")


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test()) 