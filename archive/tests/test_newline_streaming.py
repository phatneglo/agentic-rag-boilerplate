#!/usr/bin/env python3
"""
Test WebSocket streaming newline handling
"""

import asyncio
import websockets
import json
import sys

async def test_newline_streaming():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server")
            
            # Send a test message that should produce markdown with newlines
            test_message = {
                "type": "chat_message",
                "content": "Please write a simple markdown example with:\n1. A header\n2. A list\n3. A code block",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(test_message))
            print(f"📤 Sent: {test_message['content']}")
            
            print("\n🔍 Streaming tokens (showing newlines as [\\n]):")
            
            token_count = 0
            newline_count = 0
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "agent_streaming":
                        content = data.get("content", "")
                        token_count += 1
                        
                        # Count and show newlines
                        if '\n' in content:
                            newline_count += content.count('\n')
                            display_content = content.replace('\n', '[\\n]')
                            print(f"Token {token_count}: '{display_content}' (contains {content.count('\\n')} newlines)")
                        else:
                            print(f"Token {token_count}: '{content}'")
                            
                    elif data.get("type") == "response_complete":
                        print(f"\n✅ Streaming complete!")
                        print(f"📊 Total tokens: {token_count}")
                        print(f"📊 Total newlines: {newline_count}")
                        break
                        
                    elif data.get("type") == "agent_thinking":
                        print(f"🤔 {data.get('status', 'Thinking...')}")
                        
                    elif data.get("type") == "response_start":
                        print("🚀 Response started")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
        
    return newline_count > 0

if __name__ == "__main__":
    print("🧪 Testing WebSocket newline streaming...")
    success = asyncio.run(test_newline_streaming())
    
    if success:
        print("\n🎉 SUCCESS: Newlines are being preserved in streaming!")
    else:
        print("\n❌ FAILED: No newlines detected in streaming")
        sys.exit(1) 