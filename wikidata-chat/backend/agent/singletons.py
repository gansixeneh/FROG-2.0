# backend/agent/singletons.py
"""
Singleton module for agent instances to prevent creating multiple agent instances.
This helps reduce memory usage when multiple WebSocket connections are established.
"""
import os
import logging
from typing import Dict, Optional, Any, Callable

# Import the WikidataAgent class
from .agent import WikidataAgent

# Configure logging
logger = logging.getLogger(__name__)

class AgentSingleton:
    """
    Singleton for managing WikidataAgent instances.
    This prevents creating new agent instances for each WebSocket connection.
    """
    _instance = None
    _agents: Dict[str, WikidataAgent] = {}
    
    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating AgentSingleton instance")
            cls._instance = super(AgentSingleton, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_agent(cls, api_key: str, debug_callback: Optional[Callable] = None) -> WikidataAgent:
        """
        Get or create a WikidataAgent instance.
        
        Args:
            api_key: The API key for the agent
            debug_callback: Optional callback for debug output
            
        Returns:
            WikidataAgent instance
        """
        # Use the API key as the key for the agent
        agent_key = f"agent_{api_key[:8]}"  # Use first 8 chars of API key as identifier
        
        if agent_key not in cls._agents:
            logger.info(f"Creating new WikidataAgent instance with key: {agent_key}")
            cls._agents[agent_key] = WikidataAgent(gemini_api_key=api_key, debug_callback=debug_callback)
        else:
            logger.info(f"Reusing existing WikidataAgent instance with key: {agent_key}")
            # Update the debug callback for the existing agent
            # This is necessary because each WebSocket connection needs its own callback
            if debug_callback:
                cls._agents[agent_key].update_debug_callback(debug_callback)
                logger.info(f"Updated debug callback for agent with key: {agent_key}")
        
        return cls._agents[agent_key]
    
    @classmethod
    def clear_agents(cls):
        """Clear all cached agents (useful for testing or memory management)"""
        cls._agents.clear()
        logger.info("Cleared all cached agents")

# Create convenience function
def get_agent(api_key: Optional[str] = None, debug_callback: Optional[Callable] = None) -> WikidataAgent:
    """
    Get a WikidataAgent instance from the singleton cache
    
    Args:
        api_key: The API key for the agent (uses environment variable if not provided)
        debug_callback: Optional callback for debug output
        
    Returns:
        WikidataAgent instance
    """
    if api_key is None:
        api_key = os.environ.get('GEMINI_API_KEY', '')
        if not api_key:
            raise ValueError("No Gemini API key provided or found in environment variables")
    
    return AgentSingleton.get_agent(api_key, debug_callback)
