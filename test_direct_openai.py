#!/usr/bin/env python3
"""
Test OpenAI API directly to see what responses we get
"""

import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import get_settings

async def test_direct_openai():
    """Test OpenAI API directly."""
    
    print("🔍 Testing Direct OpenAI API...")
    
    # Get settings
    settings = get_settings()
    
    print(f"✅ OpenAI API Key: {settings.openai_api_key[:7]}...{settings.openai_api_key[-4:]}")
    
    # Create LLM instance
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4000,
        api_key=settings.openai_api_key
    )
    
    # Test greeting
    print("\n📝 Testing greeting: 'Hello there'")
    messages1 = [
        SystemMessage(content="You are a helpful AI assistant. Respond naturally and conversationally."),
        HumanMessage(content="Hello there")
    ]
    
    try:
        response1 = await llm.ainvoke(messages1)
        print(f"✅ Response: {response1.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test another greeting
    print("\n📝 Testing another greeting: 'Hi!'")
    messages2 = [
        SystemMessage(content="You are a helpful AI assistant. Respond naturally and conversationally."),
        HumanMessage(content="Hi!")
    ]
    
    try:
        response2 = await llm.ainvoke(messages2)
        print(f"✅ Response: {response2.content}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test a question
    print("\n📝 Testing question: 'What is the capital of France?'")
    messages3 = [
        SystemMessage(content="You are a helpful AI assistant. Respond naturally and conversationally."),
        HumanMessage(content="What is the capital of France?")
    ]
    
    try:
        response3 = await llm.ainvoke(messages3)
        print(f"✅ Response: {response3.content}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_direct_openai()) 