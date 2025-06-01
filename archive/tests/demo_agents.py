#!/usr/bin/env python3
"""
Demo script for the LangGraph Agent Orchestrator System
Tests all specialized agents and their capabilities.
"""

import asyncio
import json
import time
from typing import Dict, Any

from app.agents import AgentOrchestrator
from app.core.agent_config import validate_config


async def test_agent_orchestrator():
    """Test the agent orchestrator with various types of requests."""
    
    print("🤖 LangGraph Agent Orchestrator Demo")
    print("=" * 50)
    
    # Validate configuration
    config_valid = validate_config()
    if not config_valid:
        print("⚠️  Running in mock mode - configure OPENAI_API_KEY for full functionality")
    print()
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()
    
    # Test requests for different agent types
    test_requests = [
        {
            "type": "Code Agent",
            "request": "Write a Python function to calculate the Fibonacci sequence",
            "expected_artifacts": ["code"]
        },
        {
            "type": "Diagram Agent", 
            "request": "Create a flowchart for user authentication process",
            "expected_artifacts": ["mermaid"]
        },
        {
            "type": "Analysis Agent",
            "request": "Analyze the performance trends of our e-commerce platform",
            "expected_artifacts": ["analysis"]
        },
        {
            "type": "Document Agent",
            "request": "Write a technical guide for API integration",
            "expected_artifacts": ["document"]
        },
        {
            "type": "Visualization Agent",
            "request": "Create a bar chart showing quarterly sales data",
            "expected_artifacts": ["chart"]
        },
        {
            "type": "Multi-Agent",
            "request": "Create a Python script with documentation and flowchart for data processing pipeline",
            "expected_artifacts": ["code", "document", "mermaid"]
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_requests, 1):
        print(f"🧪 Test {i}: {test['type']}")
        print(f"📝 Request: {test['request']}")
        print("⏳ Processing...")
        
        start_time = time.time()
        
        try:
            response = await orchestrator.process_request(test["request"])
            
            processing_time = time.time() - start_time
            
            if response.success:
                print(f"✅ Success! ({processing_time:.2f}s)")
                print(f"📄 Response: {response.content[:100]}...")
                print(f"🎯 Artifacts Generated: {len(response.artifacts)}")
                
                for artifact in response.artifacts:
                    print(f"   - {artifact.get('type', 'unknown')}: {artifact.get('title', 'Untitled')}")
                
                print(f"🤖 Agents Used: {response.metadata.get('agents_used', ['unknown'])}")
                
                results.append({
                    "test": test["type"],
                    "success": True,
                    "processing_time": processing_time,
                    "artifacts_count": len(response.artifacts),
                    "agents_used": response.metadata.get("agents_used", [])
                })
            else:
                print(f"❌ Failed: {response.error}")
                results.append({
                    "test": test["type"],
                    "success": False,
                    "error": response.error
                })
                
        except Exception as e:
            print(f"💥 Exception: {e}")
            results.append({
                "test": test["type"],
                "success": False,
                "error": str(e)
            })
        
        print("-" * 50)
        print()
    
    # Print summary
    print("📊 Test Summary")
    print("=" * 50)
    
    successful_tests = [r for r in results if r["success"]]
    failed_tests = [r for r in results if not r["success"]]
    
    print(f"✅ Successful: {len(successful_tests)}/{len(results)}")
    print(f"❌ Failed: {len(failed_tests)}/{len(results)}")
    
    if successful_tests:
        avg_time = sum(r["processing_time"] for r in successful_tests) / len(successful_tests)
        total_artifacts = sum(r["artifacts_count"] for r in successful_tests)
        print(f"⏱️  Average processing time: {avg_time:.2f}s")
        print(f"🎯 Total artifacts generated: {total_artifacts}")
    
    print()
    
    # Test agent capabilities
    await test_agent_capabilities(orchestrator)
    
    # Test agent suggestions
    await test_agent_suggestions(orchestrator)


async def test_agent_capabilities(orchestrator: AgentOrchestrator):
    """Test getting agent capabilities."""
    print("🔍 Agent Capabilities")
    print("=" * 50)
    
    try:
        capabilities = orchestrator.get_agent_capabilities()
        available_agents = orchestrator.get_available_agents()
        
        print(f"📋 Available Agents: {', '.join(available_agents)}")
        print()
        
        for agent_name, capability_text in capabilities.items():
            print(f"🤖 {agent_name.upper()} AGENT:")
            print(capability_text)
            print()
            
    except Exception as e:
        print(f"❌ Error getting capabilities: {e}")


async def test_agent_suggestions(orchestrator: AgentOrchestrator):
    """Test agent suggestion system."""
    print("💡 Agent Suggestions")
    print("=" * 50)
    
    test_queries = [
        "I need help with Python programming",
        "Create a system architecture diagram", 
        "Analyze our customer data",
        "Write documentation for our API",
        "Show me a chart of our performance metrics"
    ]
    
    for query in test_queries:
        try:
            suggestions = await orchestrator.get_agent_suggestions(query)
            print(f"❓ Query: {query}")
            print("🎯 Suggested agents:")
            
            if suggestions:
                for agent, confidence in suggestions.items():
                    confidence_percent = confidence * 100
                    print(f"   - {agent}: {confidence_percent:.1f}% confidence")
            else:
                print("   - No specific suggestions")
            print()
            
        except Exception as e:
            print(f"❌ Error getting suggestions for '{query}': {e}")


async def benchmark_orchestrator():
    """Benchmark the orchestrator performance."""
    print("⚡ Performance Benchmark")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    
    # Simple requests for benchmarking
    benchmark_requests = [
        "Write a hello world function",
        "Create a simple diagram",
        "Analyze this data",
        "Write a short guide",
        "Make a basic chart"
    ]
    
    print(f"🧪 Running {len(benchmark_requests)} benchmark tests...")
    
    start_time = time.time()
    
    tasks = []
    for request in benchmark_requests:
        task = orchestrator.process_request(request)
        tasks.append(task)
    
    # Run all requests in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    successful_results = [r for r in results if not isinstance(r, Exception) and r.success]
    
    print(f"✅ Completed {len(successful_results)}/{len(benchmark_requests)} requests")
    print(f"⏱️  Total time: {total_time:.2f}s")
    print(f"🚀 Average time per request: {total_time/len(benchmark_requests):.2f}s")
    print(f"📈 Requests per second: {len(benchmark_requests)/total_time:.2f}")


async def main():
    """Main demo function."""
    print("🌟 Welcome to the LangGraph Agent Orchestrator Demo!")
    print("This demo showcases the modular agent system with GPT-4o mini integration.")
    print()
    
    await test_agent_orchestrator()
    print()
    await benchmark_orchestrator()
    
    print()
    print("🎉 Demo completed!")
    print("💡 To use with real OpenAI API, set OPENAI_API_KEY environment variable.")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main()) 