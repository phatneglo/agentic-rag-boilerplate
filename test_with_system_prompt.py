#!/usr/bin/env python3
"""
Test OpenAI API with the exact system prompt from general agent
"""

import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import get_settings

async def test_with_system_prompt():
    """Test OpenAI API with the actual system prompt."""
    
    print("🔍 Testing OpenAI API with General Agent System Prompt...")
    
    # Get settings
    settings = get_settings()
    
    # Create LLM instance
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4000,
        api_key=settings.openai_api_key
    )
    
    # The exact system prompt from general agent
    system_prompt = """You are a helpful AI assistant. Your goal is to provide clear, useful, and friendly responses to any question or request.

You can help with:
- Answering questions and providing explanations
- Creating examples and demonstrations
- Providing information and guidance
- General conversation and assistance
- Lists, tables, and data in text format
- Simple code examples in your response
- Step-by-step instructions
- Recommendations and advice

Keep your responses:
- Clear and well-organized
- Helpful and informative
- Conversational and friendly
- Complete but not overwhelming

If someone asks for examples, code, lists, or explanations, provide them directly in your response. Format your answers nicely using markdown for better readability.

For example:
- If asked for a list of dog breeds, provide a nice formatted list
- If asked for code examples, include them inline with proper formatting
- If asked to explain something, give a clear explanation with examples
- If asked for instructions, provide step-by-step guidance

Always aim to be maximally helpful while keeping things simple and accessible."""
    
    # Test greeting with system prompt
    print("\n📝 Testing with system prompt: 'Hello there'")
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Hello there")
    ]
    
    try:
        response = await llm.ainvoke(messages)
        print(f"✅ Response: '{response.content}'")
        print(f"🔢 Length: {len(response.content)} characters")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test another greeting
    print("\n📝 Testing with system prompt: 'Hi!'")
    messages2 = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Hi!")
    ]
    
    try:
        response2 = await llm.ainvoke(messages2)
        print(f"✅ Response: '{response2.content}'")
        print(f"🔢 Length: {len(response2.content)} characters")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_system_prompt()) 