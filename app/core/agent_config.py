"""
Agent Configuration Module
Handles configuration for OpenAI API and agent system settings.
"""

import os
from typing import Dict, Any

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "4000"))

# Agent System Configuration
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "30"))
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "3"))
ENABLE_AGENT_CACHING = os.getenv("ENABLE_AGENT_CACHING", "true").lower() == "true"

# Agent Selection Thresholds
AGENT_SELECTION_THRESHOLD = float(os.getenv("AGENT_SELECTION_THRESHOLD", "1.0"))
MAX_PARALLEL_AGENTS = int(os.getenv("MAX_PARALLEL_AGENTS", "2"))

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration dictionary."""
    return {
        "api_key": OPENAI_API_KEY,
        "model": OPENAI_MODEL,
        "temperature": OPENAI_TEMPERATURE,
        "max_tokens": OPENAI_MAX_TOKENS
    }

def get_agent_config() -> Dict[str, Any]:
    """Get agent system configuration dictionary."""
    return {
        "timeout": AGENT_TIMEOUT,
        "max_retries": AGENT_MAX_RETRIES,
        "enable_caching": ENABLE_AGENT_CACHING,
        "selection_threshold": AGENT_SELECTION_THRESHOLD,
        "max_parallel_agents": MAX_PARALLEL_AGENTS
    }

def validate_config() -> bool:
    """Validate configuration settings."""
    if not OPENAI_API_KEY:
        print("Warning: OPENAI_API_KEY not set. Agent system will use mock responses.")
        return False
    
    if OPENAI_TEMPERATURE < 0 or OPENAI_TEMPERATURE > 2:
        print(f"Warning: OPENAI_TEMPERATURE ({OPENAI_TEMPERATURE}) should be between 0 and 2.")
    
    if OPENAI_MAX_TOKENS < 1:
        print(f"Warning: OPENAI_MAX_TOKENS ({OPENAI_MAX_TOKENS}) should be greater than 0.")
    
    return True 