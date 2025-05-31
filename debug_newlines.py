#!/usr/bin/env python3
"""
Debug WebSocket streaming to see exact characters
"""

import asyncio
import websockets
import json

async def debug_streaming():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send test message  
            test_message = {
                "type": "chat_message", 
                "content": "Write a markdown list with line breaks",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await websocket.send(json.dumps(test_message))
            print("📤 Message sent")
            
            print("\n🔍 Raw character analysis:")
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(response)
                    
                    if data.get("type") == "agent_streaming":
                        content = data.get("content", "")
                        
                        # Show exact characters 
                        print(f"Raw: {repr(content)}")
                        
                        # Check for actual newlines
                        if '\n' in content:
                            print(f"  ✅ Contains actual newline(s): {content.count(chr(10))}")
                        if '\\n' in content:
                            print(f"  ⚠️  Contains escaped newlines: {content.count('\\\\n')}")
                            
                    elif data.get("type") == "response_complete":
                        print("\n✅ Complete!")
                        break
                        
                    elif data.get("type") in ["agent_thinking", "response_start"]:
                        print(f"ℹ️  {data.get('type')}")
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout")
                    break
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_streaming()) 