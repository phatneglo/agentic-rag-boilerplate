#!/usr/bin/env python3
"""
Demo script for the AI Chat Interface
Shows how to interact with the chat API programmatically.
"""

import asyncio
import json
import websockets
import requests
import time
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/chat"

def test_health_check():
    """Test if the server is running and healthy"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy - Version: {data.get('version')}")
            print(f"   Uptime: {data.get('uptime', 0):.2f}s")
            return True
        else:
            print(f"❌ Server health check failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_chat_preferences():
    """Test chat preferences API"""
    print("\n🔧 Testing Chat Preferences API...")
    
    try:
        # Get current preferences
        response = requests.get(f"{BASE_URL}/api/v1/chat/preferences")
        if response.status_code == 200:
            prefs = response.json()
            print(f"   Current preferences: {prefs['preferences']}")
            
            # Update preferences
            new_prefs = {
                "theme": "dark",
                "language": "en",
                "notifications": True,
                "auto_save": False
            }
            
            update_response = requests.put(
                f"{BASE_URL}/api/v1/chat/preferences",
                json=new_prefs
            )
            
            if update_response.status_code == 200:
                print("   ✅ Preferences updated successfully")
            else:
                print(f"   ❌ Failed to update preferences: {update_response.status_code}")
        else:
            print(f"   ❌ Failed to get preferences: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing preferences: {e}")

def test_http_chat():
    """Test HTTP chat endpoint"""
    print("\n💬 Testing HTTP Chat API...")
    
    try:
        test_messages = [
            "Hello! Can you help me with Python code?",
            "Show me a mermaid diagram of a simple workflow",
            "What's the weather like today?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"   Sending message {i}: {message[:50]}...")
            
            response = requests.post(
                f"{BASE_URL}/api/v1/chat/message",
                json={
                    "content": message,
                    "attachments": [],
                    "timestamp": time.time()
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                ai_response = data.get('response', {})
                print(f"   ✅ AI Response: {ai_response.get('content', '')[:100]}...")
                
                # Check for artifacts
                artifacts = ai_response.get('artifacts', [])
                if artifacts:
                    print(f"   🎨 Artifacts: {len(artifacts)} items")
                    for artifact in artifacts:
                        print(f"      - {artifact.get('type')}: {artifact.get('title')}")
            else:
                print(f"   ❌ HTTP request failed: {response.status_code}")
                
    except Exception as e:
        print(f"   ❌ Error testing HTTP chat: {e}")

async def test_websocket_chat():
    """Test WebSocket chat functionality"""
    print("\n🔌 Testing WebSocket Chat...")
    
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("   ✅ WebSocket connected successfully")
            
            # Send test messages
            test_messages = [
                {
                    "type": "chat_message",
                    "content": "Hello via WebSocket! Can you show me some Python code?",
                    "timestamp": time.time()
                },
                {
                    "type": "ping",
                    "timestamp": time.time()
                }
            ]
            
            for i, message in enumerate(test_messages, 1):
                print(f"   Sending WebSocket message {i}...")
                await websocket.send(json.dumps(message))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "chat_response":
                        print(f"   ✅ Received AI response: {response_data.get('content', '')[:100]}...")
                        artifacts = response_data.get('artifacts', [])
                        if artifacts:
                            print(f"   🎨 Artifacts: {len(artifacts)} items")
                    elif response_data.get("type") == "pong":
                        print("   ✅ Received pong response")
                    else:
                        print(f"   📨 Received: {response_data.get('type', 'unknown')}")
                        
                except asyncio.TimeoutError:
                    print("   ⚠️ Response timeout")
                
                # Small delay between messages
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"   ❌ WebSocket error: {e}")

def test_chat_history():
    """Test chat history API"""
    print("\n📚 Testing Chat History API...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/chat/history?limit=5")
        if response.status_code == 200:
            data = response.json()
            messages = data.get('messages', [])
            print(f"   ✅ Retrieved {len(messages)} messages from history")
            
            for i, msg in enumerate(messages[:3], 1):  # Show first 3
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:50]
                print(f"   {i}. [{role}]: {content}...")
        else:
            print(f"   ❌ Failed to get history: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing history: {e}")

def test_chat_ui():
    """Test chat UI accessibility"""
    print("\n🌐 Testing Chat UI...")
    
    try:
        response = requests.get(f"{BASE_URL}/chat")
        if response.status_code == 200:
            html_content = response.text
            if "AI Chat - Agentic RAG" in html_content:
                print("   ✅ Chat UI loads successfully")
                print("   🎯 You can access it at: http://localhost:8000/chat")
            else:
                print("   ⚠️ Chat UI loaded but content may be incorrect")
        else:
            print(f"   ❌ Failed to load chat UI: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error testing chat UI: {e}")

async def main():
    """Run all demo tests"""
    print("🚀 Starting AI Chat Interface Demo")
    print("=" * 50)
    
    # Test server health
    if not test_health_check():
        print("\n❌ Server is not running. Please start with: python -m app.main")
        return
    
    # Test various functionalities
    test_chat_preferences()
    test_http_chat()
    await test_websocket_chat()
    test_chat_history()
    test_chat_ui()
    
    print("\n" + "=" * 50)
    print("🎉 Demo completed!")
    print("\n📖 Next steps:")
    print("   1. Open http://localhost:8000/chat in your browser")
    print("   2. Try sending messages and interacting with artifacts")
    print("   3. Test file upload functionality")
    print("   4. Integrate with a real LLM service")

if __name__ == "__main__":
    asyncio.run(main()) 