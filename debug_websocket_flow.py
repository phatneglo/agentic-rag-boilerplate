#!/usr/bin/env python3
"""
Debug WebSocket flow step by step
"""

import asyncio
import json
import time
import websockets
import uuid

async def debug_websocket_flow():
    """Debug the complete WebSocket flow step by step."""
    
    print("🔍 Starting WebSocket Flow Debug...")
    print("=" * 60)
    
    # Connect to WebSocket
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established")
            
            # Step 1: Initialize session
            print("\n📋 STEP 1: Session Initialization")
            session_id = str(uuid.uuid4())
            init_message = {
                "type": "init_session",
                "session_id": session_id,
                "user_id": "debug_user",
                "config": {"debug": True}
            }
            
            print(f"📤 Sending: {json.dumps(init_message, indent=2)}")
            await websocket.send(json.dumps(init_message))
            
            # Wait for session initialized response
            response = await websocket.recv()
            print(f"📥 Received: {response}")
            session_data = json.loads(response)
            
            if session_data.get("type") == "session_initialized":
                actual_session_id = session_data.get("session_id")
                print(f"✅ Session initialized: {actual_session_id}")
            else:
                print("❌ Session initialization failed")
                return
            
            # Step 2: Send first message
            print("\n📋 STEP 2: First Chat Message")
            first_message = {
                "type": "chat_message",
                "content": "hi there",
                "session_id": actual_session_id,
                "user_id": "debug_user",
                "context": {"message_number": 1}
            }
            
            print(f"📤 Sending: {json.dumps(first_message, indent=2)}")
            await websocket.send(json.dumps(first_message))
            
            # Collect all responses for first message
            print("📥 Collecting responses...")
            first_responses = []
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    first_responses.append(response_data)
                    
                    print(f"📥 Response: {response_data.get('type')} - {response_data.get('content', response_data.get('error', ''))[:100]}...")
                    
                    if response_data.get("type") == "response_complete":
                        print("✅ First message processing complete")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            # Show first message summary
            complete_response = None
            for resp in first_responses:
                if resp.get("type") == "response_complete":
                    complete_response = resp
                    break
            
            if complete_response:
                first_content = complete_response.get("content", "")
                first_memory = complete_response.get("memory", {})
                print(f"\n🎯 FIRST MESSAGE RESULT:")
                print(f"   Content: '{first_content}'")
                print(f"   Memory: {json.dumps(first_memory, indent=4)}")
            
            # Step 3: Wait a moment
            print("\n⏳ Waiting 2 seconds before next message...")
            await asyncio.sleep(2)
            
            # Step 4: Send second message
            print("\n📋 STEP 3: Second Chat Message")
            second_message = {
                "type": "chat_message",
                "content": "Im Roniel Nuqui",
                "session_id": actual_session_id,
                "user_id": "debug_user",
                "context": {"message_number": 2}
            }
            
            print(f"📤 Sending: {json.dumps(second_message, indent=2)}")
            await websocket.send(json.dumps(second_message))
            
            # Collect all responses for second message
            print("📥 Collecting responses...")
            second_responses = []
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    second_responses.append(response_data)
                    
                    print(f"📥 Response: {response_data.get('type')} - {response_data.get('content', response_data.get('error', ''))[:100]}...")
                    
                    if response_data.get("type") == "response_complete":
                        print("✅ Second message processing complete")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            # Show second message summary
            complete_response = None
            for resp in second_responses:
                if resp.get("type") == "response_complete":
                    complete_response = resp
                    break
            
            if complete_response:
                second_content = complete_response.get("content", "")
                second_memory = complete_response.get("memory", {})
                print(f"\n🎯 SECOND MESSAGE RESULT:")
                print(f"   Content: '{second_content}'")
                print(f"   Memory: {json.dumps(second_memory, indent=4)}")
            
            # Step 5: Analysis
            print("\n📊 ANALYSIS:")
            print("=" * 60)
            if complete_response:
                if first_content == second_content:
                    print("❌ ISSUE DETECTED: Both messages got identical responses!")
                    print(f"   Both responses: '{first_content}'")
                    print("\n🔍 POTENTIAL CAUSES:")
                    print("   1. Session context not being maintained")
                    print("   2. Agent not receiving previous conversation history")
                    print("   3. Caching issue in the LLM or agent")
                    print("   4. System prompt overriding context")
                else:
                    print("✅ SUCCESS: Messages got different responses")
                    print(f"   First: '{first_content}'")
                    print(f"   Second: '{second_content}'")
            
    except Exception as e:
        print(f"❌ Error during debug: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_websocket_flow()) 