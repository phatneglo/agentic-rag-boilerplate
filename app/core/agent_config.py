"""
Agent Configuration Module
Handles configuration for OpenAI API and agent system settings.
"""

import os
from typing import Dict, Any
from app.core.config import get_settings

# Get settings instance
settings = get_settings()

# Agent System Configuration (these can stay as os.getenv since they're agent-specific)
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "30"))
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "3"))
ENABLE_AGENT_CACHING = os.getenv("ENABLE_AGENT_CACHING", "true").lower() == "true"

# Agent Selection Thresholds
AGENT_SELECTION_THRESHOLD = float(os.getenv("AGENT_SELECTION_THRESHOLD", "1.0"))
MAX_PARALLEL_AGENTS = int(os.getenv("MAX_PARALLEL_AGENTS", "2"))

def get_openai_api_key() -> str:
    """Get OpenAI API key from settings."""
    return settings.openai_api_key

def get_openai_model() -> str:
    """Get OpenAI model from environment variables."""
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def get_openai_temperature() -> float:
    """Get OpenAI temperature from environment variables."""
    return float(os.getenv("OPENAI_TEMPERATURE", "0.7"))

def get_openai_max_tokens() -> int:
    """Get OpenAI max tokens from environment variables."""
    return int(os.getenv("OPENAI_MAX_TOKENS", "4000"))

# Backwards compatibility - these will now use settings
def OPENAI_API_KEY() -> str:
    """Dynamic OpenAI API key that reads from settings."""
    return settings.openai_api_key

def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration dictionary."""
    return {
        "api_key": settings.openai_api_key,
        "model": get_openai_model(),
        "temperature": get_openai_temperature(),
        "max_tokens": get_openai_max_tokens()
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
    if not settings.openai_api_key:
        print("Warning: OPENAI_API_KEY not set. Agent system will use mock responses.")
        return False
    
    temp = get_openai_temperature()
    if temp < 0 or temp > 2:
        print(f"Warning: OPENAI_TEMPERATURE ({temp}) should be between 0 and 2.")
    
    max_tokens = get_openai_max_tokens()
    if max_tokens < 1:
        print(f"Warning: OPENAI_MAX_TOKENS ({max_tokens}) should be greater than 0.")
    
    return True 