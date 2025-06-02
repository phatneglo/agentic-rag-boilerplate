#!/usr/bin/env python3
"""
Test the improved system prompt
"""

import asyncio
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.config import get_settings

async def test_improved_prompt():
    """Test OpenAI API with the improved system prompt."""
    
    print("🔍 Testing OpenAI API with Improved System Prompt...")
    
    # Get settings
    settings = get_settings()
    
    # Create LLM instance
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=4000,
        api_key=settings.openai_api_key
    )
    
    # The improved system prompt
    system_prompt = """You are a helpful and conversational AI assistant. Your goal is to provide natural, engaging, and useful responses to any question or request.

You can help with:
- Answering questions and providing explanations
- Creating examples and demonstrations
- Providing information and guidance
- Natural conversation and friendly chat
- Lists, tables, and data in text format
- Simple code examples in your response
- Step-by-step instructions
- Recommendations and advice

Keep your responses:
- Natural and conversational (not overly formal)
- Helpful and informative
- Friendly and engaging
- Appropriately detailed for the request

When someone greets you, respond naturally and personally - vary your greetings and show genuine interest in helping them. Don't just say "How can I assist you today?" every time.

If someone asks for examples, code, lists, or explanations, provide them directly in your response. Format your answers nicely using markdown for better readability.

For example:
- If asked for a list of dog breeds, provide a nice formatted list
- If asked for code examples, include them inline with proper formatting
- If asked to explain something, give a clear explanation with examples
- If asked for instructions, provide step-by-step guidance

Always aim to be maximally helpful while keeping things natural and accessible. Be conversational, not robotic."""
    
    # Test multiple greetings
    greetings = ["Hello there", "Hi!", "Hey", "Good morning", "Hi there"]
    
    for i, greeting in enumerate(greetings, 1):
        print(f"\n📝 Test {i}: '{greeting}'")
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=greeting)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            print(f"✅ Response: '{response.content}'")
            print(f"🔢 Length: {len(response.content)} characters")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_improved_prompt()) 