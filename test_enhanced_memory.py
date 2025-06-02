#!/usr/bin/env python3
"""
Enhanced Memory Test Script
Tests the complete enhanced memory system with short-term and long-term memory patterns.
"""

import asyncio
import uuid
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.db.session import init_db, test_connection
from app.db.memory import PostgresChatMemory
from app.agents.agent_orchestrator import AgentOrchestrator


async def test_enhanced_memory_system():
    """Test the complete enhanced memory system."""
    print("🧠 Enhanced Memory System Test")
    print("=" * 60)
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database initialized")
        
        # Test connection
        if not await test_connection():
            print("❌ Database connection failed")
            return False
        
        print("✅ Database connection verified")
        
        # Initialize enhanced orchestrator
        orchestrator = AgentOrchestrator()
        print("✅ Enhanced orchestrator initialized")
        
        # Test 1: Session Auto-Creation
        print("\n🆕 Test 1: Session Auto-Creation")
        response1 = await orchestrator.process_request(
            "Hello! Can you write a simple Python function to add two numbers?",
            context={"test": "auto_session"},
            config={"user_id": "test_user_enhanced"}
        )
        
        print(f"✅ Response 1: {response1.content[:100]}...")
        print(f"Session ID: {response1.metadata.get('session_id', 'None')}")
        print(f"Memory loaded: {response1.metadata.get('memory_loaded', False)}")
        
        session_id = response1.metadata.get('session_id')
        if not session_id:
            print("❌ No session ID created")
            return False
        
        # Test 2: Memory Persistence with Same Session
        print(f"\n💾 Test 2: Memory Persistence (Session: {session_id})")
        response2 = await orchestrator.process_request(
            "Can you make that function recursive?",
            context={"test": "memory_persistence"},
            config={"session_id": session_id, "user_id": "test_user_enhanced"}
        )
        
        print(f"✅ Response 2: {response2.content[:100]}...")
        print(f"Memory loaded: {response2.metadata.get('memory_loaded', False)}")
        print(f"Message count: {response2.metadata.get('message_count', 0)}")
        
        # Test 3: Conversation Context Awareness
        print(f"\n🔄 Test 3: Context Awareness (Session: {session_id})")
        response3 = await orchestrator.process_request(
            "Now add error handling to it",
            context={"test": "context_awareness"},
            config={"session_id": session_id, "user_id": "test_user_enhanced"}
        )
        
        print(f"✅ Response 3: {response3.content[:100]}...")
        print(f"Message count: {response3.metadata.get('message_count', 0)}")
        
        # Test 4: Agent Routing with Context
        print(f"\n🎯 Test 4: Agent Routing with Context (Session: {session_id})")
        response4 = await orchestrator.process_request(
            "That's great! Now can you help me write documentation for this function?",
            context={"test": "routing_with_context"},
            config={"session_id": session_id, "user_id": "test_user_enhanced"}
        )
        
        print(f"✅ Response 4: {response4.content[:100]}...")
        print(f"Selected agent: {response4.metadata.get('primary_agent', 'unknown')}")
        
        # Test 5: Verify Database Persistence
        print(f"\n🔍 Test 5: Database Verification")
        memory = PostgresChatMemory()
        
        # Get conversation history
        session_uuid = uuid.UUID(session_id)
        history = await memory.get_conversation_history(session_uuid)
        print(f"✅ Conversation history: {len(history)} messages")
        
        # Get session stats
        stats = await memory.get_session_stats(session_uuid)
        print(f"✅ Session stats: {stats['total_messages']} messages, {stats['total_tokens']} tokens")
        print(f"Message breakdown: {stats['message_counts']}")
        
        # Test 6: New Session Context Loading
        print(f"\n🔄 Test 6: Context Loading in New Session")
        response5 = await orchestrator.process_request(
            "What was the last function we worked on?",
            context={"test": "context_loading"},
            config={"session_id": session_id, "user_id": "test_user_enhanced"}
        )
        
        print(f"✅ Response 5: {response5.content[:100]}...")
        print(f"Memory loaded: {response5.metadata.get('memory_loaded', False)}")
        
        # Test 7: Short-term Memory Management
        print(f"\n⚡ Test 7: Short-term Memory Management")
        # Send multiple messages to test memory trimming
        for i in range(5):
            response = await orchestrator.process_request(
                f"This is test message {i+1} to check memory management",
                context={"test": f"short_term_{i}"},
                config={"session_id": session_id, "user_id": "test_user_enhanced"}
            )
            message_count = response.metadata.get('message_count', 0)
            print(f"   Message {i+1}: {message_count} total messages")
        
        # Final verification
        final_stats = await memory.get_session_stats(session_uuid)
        print(f"✅ Final stats: {final_stats['total_messages']} messages in database")
        
        # Cleanup
        print(f"\n🧹 Cleanup")
        cleanup_success = await memory.delete_session(session_uuid)
        print(f"✅ Session cleanup: {'success' if cleanup_success else 'failed'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced memory test failed: {e}")
        return False


async def test_memory_edge_cases():
    """Test edge cases for memory system."""
    print("\n🔍 Testing Memory Edge Cases")
    print("=" * 40)
    
    try:
        orchestrator = AgentOrchestrator()
        
        # Test invalid session ID
        print("Testing invalid session ID...")
        response = await orchestrator.process_request(
            "Hello with invalid session",
            config={"session_id": "invalid-uuid"}
        )
        print(f"✅ Handled invalid session: {response.metadata.get('session_id')}")
        
        # Test no session ID
        print("Testing no session ID...")
        response = await orchestrator.process_request(
            "Hello without session",
            config={}
        )
        print(f"✅ Auto-created session: {response.metadata.get('session_id')}")
        
        # Test empty messages
        print("Testing empty context...")
        response = await orchestrator.process_request(
            "Test with minimal config",
            context=None,
            config=None
        )
        print(f"✅ Handled minimal config: {response.success}")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        return False


async def run_enhanced_memory_tests():
    """Run all enhanced memory tests."""
    print("🚀 Enhanced Memory System Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Test 1: Core memory system
    success1 = await test_enhanced_memory_system()
    
    # Test 2: Edge cases
    success2 = await test_memory_edge_cases()
    
    print("\n🎉 Test Suite Summary")
    print("=" * 60)
    print(f"Core memory system: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Edge cases: {'✅ PASSED' if success2 else '❌ FAILED'}")
    print(f"Overall result: {'✅ ALL TESTS PASSED' if success1 and success2 else '❌ SOME TESTS FAILED'}")
    print(f"Finished at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(run_enhanced_memory_tests()) 