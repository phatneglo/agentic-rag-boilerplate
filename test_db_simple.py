#!/usr/bin/env python3
"""
Simple test for database message saving
"""

import asyncio
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from app.db.memory import PostgresChatMemory

async def test_db_simple():
    """Test basic database operations."""
    
    print("🔍 Testing Database Operations...")
    
    # Initialize memory
    memory = PostgresChatMemory()
    
    try:
        # Test 1: Create session
        print("\n📋 TEST 1: Create Session")
        session = await memory.create_session(
            title="Test Session",
            user_id="test_user",
            session_type="chat",
            config={"test": True},
            context={"source": "test"}
        )
        print(f"✅ Created session: {session.id}")
        
        # Test 2: Add user message
        print("\n📋 TEST 2: Add User Message")
        user_message = HumanMessage(content="Hello test")
        
        try:
            await memory.add_message(
                session_id=session.id,
                message=user_message,
                agent_name="user",  # This might be causing the issue
                agent_metadata={
                    "user_id": "test_user",
                    "timestamp": 1748860000.0
                }
            )
            print("✅ User message saved successfully")
        except Exception as e:
            print(f"❌ User message save failed: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            
            # Try with different agent_name
            try:
                print("🔄 Trying with agent_name='general'...")
                await memory.add_message(
                    session_id=session.id,
                    message=user_message,
                    agent_name="general",
                    agent_metadata={
                        "user_id": "test_user",
                        "timestamp": 1748860000.0
                    }
                )
                print("✅ User message saved with agent_name='general'")
            except Exception as e2:
                print(f"❌ Still failed with general: {e2}")
        
        # Test 3: Add AI message
        print("\n📋 TEST 3: Add AI Message")
        ai_message = AIMessage(content="Hello response")
        
        try:
            await memory.add_message(
                session_id=session.id,
                message=ai_message,
                agent_name="general",
                agent_metadata={
                    "agent_name": "general",
                    "timestamp": 1748860001.0,
                    "user_profile": {},
                    "conversation_context": ""
                }
            )
            print("✅ AI message saved successfully")
        except Exception as e:
            print(f"❌ AI message save failed: {e}")
            print(f"❌ Error type: {type(e).__name__}")
        
        # Test 4: Load conversation history
        print("\n📋 TEST 4: Load Conversation History")
        try:
            history = await memory.get_conversation_history(session.id, limit=10)
            print(f"✅ Loaded {len(history)} messages from history")
            for i, msg in enumerate(history):
                print(f"   {i+1}. {msg.type}: {msg.content[:50]}...")
        except Exception as e:
            print(f"❌ History load failed: {e}")
        
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_db_simple()) 