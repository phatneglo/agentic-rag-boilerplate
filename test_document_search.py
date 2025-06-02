#!/usr/bin/env python3
"""
Test document search functionality
"""

import asyncio
import json
import websockets
import uuid

async def test_document_search():
    """Test the document search functionality."""
    
    print("🔍 Testing Document Search Functionality...")
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
                "user_id": "search_test_user",
                "config": {"debug": True}
            }
            
            await websocket.send(json.dumps(init_message))
            response = await websocket.recv()
            session_data = json.loads(response)
            
            if session_data.get("type") == "session_initialized":
                actual_session_id = session_data.get("session_id")
                print(f"✅ Session initialized: {actual_session_id}")
            else:
                print("❌ Session initialization failed")
                return
            
            # Step 2: Test document search request
            print("\n📋 STEP 2: Document Search Test")
            search_message = {
                "type": "chat_message",
                "content": "search documents about machine learning",
                "session_id": actual_session_id,
                "user_id": "search_test_user",
                "context": {"test_search": True}
            }
            
            print(f"📤 Sending search request: {search_message['content']}")
            await websocket.send(json.dumps(search_message))
            
            # Collect all responses
            print("📥 Collecting responses...")
            responses = []
            artifacts = []
            
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    response_data = json.loads(response)
                    responses.append(response_data)
                    
                    response_type = response_data.get('type')
                    print(f"📥 Response: {response_type}")
                    
                    # Check for artifacts in agent metadata
                    if response_type == "response_complete":
                        metadata = response_data.get('metadata', {})
                        if 'artifacts' in metadata:
                            artifacts.extend(metadata['artifacts'])
                        print("✅ Search request processing complete")
                        break
                        
                except asyncio.TimeoutError:
                    print("⏰ Timeout waiting for response")
                    break
            
            # Analyze results
            print("\n📊 SEARCH ANALYSIS:")
            print("=" * 60)
            
            # Find the final response
            final_response = None
            for resp in responses:
                if resp.get("type") == "response_complete":
                    final_response = resp
                    break
            
            if final_response:
                content = final_response.get("content", "")
                metadata = final_response.get("metadata", {})
                primary_agent = metadata.get("primary_agent", "unknown")
                
                print(f"🎯 Primary Agent Used: {primary_agent}")
                print(f"📝 Response Content: {content[:200]}...")
                
                # Check if TypeSense agent was used
                if primary_agent == "typesense":
                    print("✅ SUCCESS: TypeSense agent was correctly selected for document search!")
                    
                    # Check for search artifacts
                    if artifacts:
                        print(f"🎨 Found {len(artifacts)} artifacts:")
                        for i, artifact in enumerate(artifacts):
                            print(f"   {i+1}. Type: {artifact.get('type', 'unknown')}")
                            print(f"      Title: {artifact.get('title', 'untitled')}")
                            if artifact.get('type') == 'document_search_results':
                                print("   ✅ Document search results artifact found!")
                                # Parse and show search data
                                try:
                                    search_data = json.loads(artifact.get('content', '{}'))
                                    query = search_data.get('query', 'unknown')
                                    total_results = search_data.get('totalResults', 0)
                                    results_shown = len(search_data.get('results', []))
                                    print(f"      Search Query: '{query}'")
                                    print(f"      Total Results: {total_results}")
                                    print(f"      Results Shown: {results_shown}")
                                except json.JSONDecodeError:
                                    print("      ⚠️ Could not parse search data")
                    else:
                        print("⚠️ No artifacts found in response")
                        
                else:
                    print(f"❌ ISSUE: Wrong agent selected - expected 'typesense', got '{primary_agent}'")
                    print("🔍 DEBUGGING INFO:")
                    print(f"   Content contains 'search': {'search' in content.lower()}")
                    print(f"   Content contains 'documents': {'documents' in content.lower()}")
                    
            else:
                print("❌ No final response found")
            
            # Step 3: Test another search query
            print("\n📋 STEP 3: Second Search Test")
            search_message2 = {
                "type": "chat_message",
                "content": "find documents related to Python programming",
                "session_id": actual_session_id,
                "user_id": "search_test_user",
                "context": {"test_search": True}
            }
            
            print(f"📤 Sending second search: {search_message2['content']}")
            await websocket.send(json.dumps(search_message2))
            
            # Quick check of response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                print(f"📥 First response type: {response_data.get('type')}")
                
                # Wait for complete response
                while response_data.get('type') != 'response_complete':
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                
                agent_used = response_data.get('metadata', {}).get('primary_agent', 'unknown')
                print(f"🎯 Second search used agent: {agent_used}")
                
                if agent_used == "typesense":
                    print("✅ Second search also correctly routed to TypeSense!")
                else:
                    print(f"❌ Second search incorrectly routed to: {agent_used}")
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout on second search")
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_document_search()) 