#!/usr/bin/env python3
"""
Test stop button functionality
"""

import asyncio
import websockets
import json
import sys

async def test_stop_functionality():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Send a test message that should produce a long response
            test_message = {
                "type": "chat_message",
                "content": "Please write a very detailed explanation of how neural networks work with lots of examples",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Sent request for long response")
            
            # Wait for the response to start streaming
            response_started = False
            message_count = 0
            
            # Listen for a few streaming messages then send stop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    print(f"📩 Received: {data.get('type')} - {data.get('content', '')[:50]}...")
                    
                    if data.get('type') == 'response_start':
                        response_started = True
                        print("🎬 Response started streaming")
                    
                    if data.get('type') == 'agent_streaming':
                        message_count += 1
                        
                        # After receiving a few chunks, send stop signal
                        if message_count >= 5:
                            print("🛑 Sending stop signal...")
                            stop_message = {
                                "type": "stop_generation",
                                "timestamp": asyncio.get_event_loop().time()
                            }
                            await websocket.send(json.dumps(stop_message))
                    
                    if data.get('type') == 'generation_stopped':
                        print("✅ Generation stopped successfully!")
                        print(f"📊 Received {message_count} streaming chunks before stopping")
                        break
                        
                    if data.get('type') == 'response_complete':
                        print("⚠️  Response completed without being stopped")
                        break
                        
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {message}")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧪 Testing stop button functionality...")
    result = asyncio.run(test_stop_functionality())
    
    if result:
        print("🎉 Stop functionality test completed!")
    else:
        print("💥 Stop functionality test failed!")
        sys.exit(1) 