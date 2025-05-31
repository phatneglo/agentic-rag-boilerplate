#!/usr/bin/env python3
"""
Simple WebSocket client to test streaming functionality
"""

import asyncio
import websockets
import json
import sys

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")
            
            # Send a test message
            test_message = {
                "type": "chat_message",
                "content": "Hello, can you help me with a simple coding task?",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"Sent: {test_message['content']}")
            
            # Listen for responses
            response_buffer = ""
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    
                    if msg_type == "agent_thinking":
                        print(f"🤔 {data.get('status', 'Thinking...')}")
                    
                    elif msg_type == "response_start":
                        print("🚀 Response starting...")
                        response_buffer = ""
                    
                    elif msg_type == "agent_streaming":
                        content = data.get("content", "")
                        response_buffer += content
                        print(f"📝 Token: '{content}' (Total so far: {len(response_buffer)} chars)")
                    
                    elif msg_type == "response_complete":
                        final_content = data.get("content", "")
                        artifacts = data.get("artifacts", [])
                        print(f"✅ Response complete!")
                        print(f"📄 Final content length: {len(final_content)} chars")
                        print(f"📎 Artifacts: {len(artifacts)}")
                        print(f"💬 Streamed content: '{response_buffer}'")
                        break
                    
                    elif msg_type == "agent_error":
                        print(f"❌ Agent error: {data.get('error', 'Unknown error')}")
                        break
                    
                    elif msg_type == "error":
                        print(f"❌ Error: {data.get('message', 'Unknown error')}")
                        break
                    
                    else:
                        print(f"🔍 Unknown message: {msg_type} - {data}")
                
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON: {message}")
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
    
    except ConnectionRefusedError:
        print("❌ Could not connect to WebSocket server. Is it running on localhost:8000?")
        return False
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        return False
    
    return True

def main():
    print("🚀 Testing WebSocket streaming...")
    success = asyncio.run(test_websocket())
    
    if success:
        print("\n✅ WebSocket test completed successfully!")
    else:
        print("\n❌ WebSocket test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 