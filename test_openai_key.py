#!/usr/bin/env python3
"""
Test OpenAI API key and agent responses
"""

import asyncio
import os
from app.core.config import get_settings
from app.agents.agent_orchestrator import AgentOrchestrator

async def test_openai_setup():
    """Test OpenAI configuration and agent responses."""
    
    print("🔍 Testing OpenAI Configuration...")
    
    # Check settings
    settings = get_settings()
    
    print(f"✅ OpenAI API Key configured: {'Yes' if settings.openai_api_key else 'No'}")
    if settings.openai_api_key:
        # Show only first and last few characters for security
        masked_key = f"{settings.openai_api_key[:7]}...{settings.openai_api_key[-4:]}"
        print(f"   Key: {masked_key}")
        print(f"   Length: {len(settings.openai_api_key)} characters")
    
    print("\n🧠 Testing Agent Orchestrator...")
    
    # Test orchestrator
    orchestrator = AgentOrchestrator()
    
    # Test simple message
    print("\n📝 Testing with simple message: 'Hello there'")
    
    response = await orchestrator.process_request(
        "Hello there",
        context={"test": True},
        config={"user_id": "test_user"}
    )
    
    print(f"✅ Response Success: {response.success}")
    print(f"📄 Content: {response.content}")
    print(f"📊 Metadata: {response.metadata}")
    if response.error:
        print(f"❌ Error: {response.error}")
    
    # Test a more complex message
    print("\n📝 Testing with complex message: 'What is recursion in programming?'")
    
    response2 = await orchestrator.process_request(
        "What is recursion in programming?",
        context={"test": True},
        config={"user_id": "test_user"}
    )
    
    print(f"✅ Response Success: {response2.success}")
    print(f"📄 Content: {response2.content[:200]}...")  # First 200 chars
    print(f"📊 Metadata: {response2.metadata}")
    if response2.error:
        print(f"❌ Error: {response2.error}")

if __name__ == "__main__":
    asyncio.run(test_openai_setup()) 