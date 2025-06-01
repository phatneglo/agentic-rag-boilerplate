#!/usr/bin/env python3
"""
Test improved stop button functionality and send button enablement
"""

import asyncio
import websockets
import json
import sys

async def test_improved_stop():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Send a test message that should produce a long response
            test_message = {
                "type": "chat_message",
                "content": "Please write a very detailed explanation of quantum computing with many examples and technical details. Make it very comprehensive and long.",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent request for long response")
            
            # Track streaming
            chunk_count = 0
            response_started = False
            stop_sent = False
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type')
                    content = data.get('content', '')[:30]
                    
                    print(f"📩 {msg_type}: {content}...")
                    
                    if msg_type == 'response_start':
                        response_started = True
                        print("🎬 Response streaming started")
                    
                    elif msg_type == 'agent_streaming':
                        chunk_count += 1
                        
                        # Send stop after receiving 3 chunks (much earlier)
                        if chunk_count == 3 and not stop_sent:
                            print(f"🛑 Sending stop signal after {chunk_count} chunks...")
                            stop_message = {
                                "type": "stop_generation",
                                "timestamp": asyncio.get_event_loop().time()
                            }
                            await websocket.send(json.dumps(stop_message))
                            stop_sent = True
                    
                    elif msg_type == 'generation_stopped':
                        print("✅ Generation stopped successfully!")
                        print(f"📊 Received {chunk_count} chunks before stopping")
                        return True
                        
                    elif msg_type == 'response_complete':
                        if stop_sent:
                            print("❌ Response completed despite stop signal!")
                            print(f"📊 Received {chunk_count} total chunks")
                            return False
                        else:
                            print("✅ Response completed normally (no stop sent)")
                            return True
                            
                    # Timeout after too many chunks without stopping
                    if chunk_count > 50:
                        print("⏰ Test timeout - too many chunks received")
                        return False
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {message}")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing improved stop functionality...")
    result = asyncio.run(test_improved_stop())
    
    if result:
        print("🎉 Stop functionality test PASSED!")
    else:
        print("💥 Stop functionality test FAILED!")
        sys.exit(1) 