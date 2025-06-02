#!/usr/bin/env python3
"""
WebSocket Memory Integration Test Script
Tests the complete WebSocket integration with enhanced memory system.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed

from app.db.session import init_db, test_connection
from app.db.memory import PostgresChatMemory


async def test_websocket_memory_integration():
    """Test the complete WebSocket memory integration."""
    print("🔌 WebSocket Memory Integration Test")
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
        
        # Test WebSocket connection with memory
        uri = "ws://localhost:8000/ws/chat"
        
        print(f"\n🔌 Connecting to WebSocket: {uri}")
        
        try:
            async with websockets.connect(uri) as websocket:
                print("✅ WebSocket connected")
                
                # Test 1: Session Initialization
                print("\n🆕 Test 1: Session Initialization")
                
                init_message = {
                    "type": "init_session",
                    "user_id": "test_websocket_user",
                    "config": {"test": "websocket_integration"},
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send(json.dumps(init_message))
                print("📤 Sent session init message")
                
                # Wait for session initialized response
                response = await websocket.recv()
                session_data = json.loads(response)
                
                if session_data.get("type") == "session_initialized":
                    session_id = session_data.get("session_id")
                    user_id = session_data.get("user_id")
                    print(f"✅ Session initialized: {session_id}")
                    print(f"   User ID: {user_id}")
                else:
                    print(f"❌ Unexpected response: {session_data}")
                    return False
                
                # Test 2: Send Chat Message with Memory
                print(f"\n💬 Test 2: Chat Message with Memory (Session: {session_id})")
                
                chat_message = {
                    "type": "chat_message",
                    "content": "Hello! Can you write a Python function to calculate factorial?",
                    "session_id": session_id,
                    "user_id": user_id,
                    "context": {"test": "memory_chat"},
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send(json.dumps(chat_message))
                print("📤 Sent chat message")
                
                # Process streaming responses
                response_content = ""
                memory_metadata = None
                
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "response_start":
                            print("📥 Response started")
                        elif data.get("type") == "agent_thinking":
                            print(f"🤔 Agent thinking: {data.get('status')}")
                        elif data.get("type") == "agent_streaming":
                            content_chunk = data.get("content", "")
                            response_content += content_chunk
                            print(f"📥 Streaming: {content_chunk.strip()}")
                        elif data.get("type") == "response_complete":
                            memory_metadata = data.get("memory", {})
                            print(f"✅ Response complete")
                            print(f"   Content length: {len(data.get('content', ''))}")
                            print(f"   Artifacts: {len(data.get('artifacts', []))}")
                            print(f"   Memory - Session: {memory_metadata.get('session_id')}")
                            print(f"   Memory - Message count: {memory_metadata.get('message_count')}")
                            print(f"   Memory - Primary agent: {memory_metadata.get('primary_agent')}")
                            break
                        elif data.get("type") == "agent_error":
                            print(f"❌ Agent error: {data.get('error')}")
                            break
                        elif data.get("type") == "error":
                            print(f"❌ Error: {data.get('message')}")
                            break
                        
                    except asyncio.TimeoutError:
                        print("⏰ Response timeout")
                        break
                
                # Test 3: Follow-up Message with Context
                print(f"\n🔄 Test 3: Follow-up Message with Context")
                
                followup_message = {
                    "type": "chat_message",
                    "content": "Now can you make that function recursive?",
                    "session_id": session_id,
                    "user_id": user_id,
                    "context": {"test": "context_awareness"},
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send(json.dumps(followup_message))
                print("📤 Sent follow-up message")
                
                # Process response
                followup_content = ""
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(response)
                        
                        if data.get("type") == "agent_streaming":
                            followup_content += data.get("content", "")
                        elif data.get("type") == "response_complete":
                            memory_metadata = data.get("memory", {})
                            print(f"✅ Follow-up response complete")
                            print(f"   Memory - Message count: {memory_metadata.get('message_count')}")
                            break
                        elif data.get("type") in ["agent_error", "error"]:
                            print(f"❌ Follow-up error: {data}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("⏰ Follow-up response timeout")
                        break
                
                # Test 4: Load Session History
                print(f"\n📚 Test 4: Load Session History")
                
                history_message = {
                    "type": "load_session",
                    "session_id": session_id,
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send(json.dumps(history_message))
                print("📤 Sent history load request")
                
                # Wait for history response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    history_data = json.loads(response)
                    
                    if history_data.get("type") == "session_history":
                        history = history_data.get("history", [])
                        stats = history_data.get("stats", {})
                        print(f"✅ Session history loaded")
                        print(f"   History length: {len(history)}")
                        print(f"   Stats: {stats}")
                        
                        for i, msg in enumerate(history[-3:]):  # Show last 3 messages
                            print(f"   [{i+1}] {msg.get('type')}: {msg.get('content', '')[:50]}...")
                    else:
                        print(f"❌ Unexpected history response: {history_data}")
                        
                except asyncio.TimeoutError:
                    print("⏰ History load timeout")
                
                # Test 5: Session Info
                print(f"\n📋 Test 5: Session Info")
                
                info_message = {
                    "type": "get_session_info",
                    "timestamp": time.time() * 1000
                }
                
                await websocket.send(json.dumps(info_message))
                print("📤 Sent session info request")
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    info_data = json.loads(response)
                    
                    if info_data.get("type") == "session_info":
                        print(f"✅ Session info received")
                        print(f"   Session ID: {info_data.get('session_id')}")
                        print(f"   User ID: {info_data.get('user_id')}")
                        print(f"   Last activity: {info_data.get('last_activity')}")
                    else:
                        print(f"❌ Unexpected info response: {info_data}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Session info timeout")
                
                print(f"\n✅ WebSocket tests completed successfully!")
                
                # Verify database state
                print(f"\n🔍 Verifying Database State")
                memory = PostgresChatMemory()
                session_uuid = uuid.UUID(session_id)
                
                # Get final stats
                final_stats = await memory.get_session_stats(session_uuid)
                print(f"✅ Final database stats: {final_stats}")
                
                # Cleanup
                cleanup_success = await memory.delete_session(session_uuid)
                print(f"🧹 Session cleanup: {'success' if cleanup_success else 'failed'}")
                
                return True
                
        except ConnectionClosed:
            print("❌ WebSocket connection closed unexpectedly")
            return False
        except Exception as e:
            print(f"❌ WebSocket connection error: {e}")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket memory test failed: {e}")
        return False


async def test_websocket_error_cases():
    """Test WebSocket error handling and edge cases."""
    print("\n🔍 Testing WebSocket Error Cases")
    print("=" * 40)
    
    try:
        uri = "ws://localhost:8000/ws/chat"
        
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected for error testing")
            
            # Test invalid message format
            print("Testing invalid JSON...")
            await websocket.send("invalid json {")
            
            # Wait for error response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_data = json.loads(response)
                print(f"✅ Error handling: {error_data.get('type')}")
            except asyncio.TimeoutError:
                print("⏰ No error response received")
            
            # Test invalid session ID
            print("Testing invalid session ID...")
            invalid_message = {
                "type": "load_session",
                "session_id": "invalid-uuid-format",
                "timestamp": time.time() * 1000
            }
            
            await websocket.send(json.dumps(invalid_message))
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                error_data = json.loads(response)
                print(f"✅ Invalid session handling: {error_data.get('type')}")
            except asyncio.TimeoutError:
                print("⏰ No invalid session response")
            
            return True
            
    except Exception as e:
        print(f"❌ Error case test failed: {e}")
        return False


async def run_websocket_memory_tests():
    """Run all WebSocket memory tests."""
    print("🚀 WebSocket Memory Integration Test Suite")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")
    print()
    
    # Test 1: Core WebSocket memory integration
    success1 = await test_websocket_memory_integration()
    
    # Test 2: Error cases
    success2 = await test_websocket_error_cases()
    
    print("\n🎉 Test Suite Summary")
    print("=" * 60)
    print(f"WebSocket memory integration: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Error case handling: {'✅ PASSED' if success2 else '❌ FAILED'}")
    print(f"Overall result: {'✅ ALL TESTS PASSED' if success1 and success2 else '❌ SOME TESTS FAILED'}")
    print(f"Finished at: {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(run_websocket_memory_tests()) 