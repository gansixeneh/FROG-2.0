# backend/agent/llm_factory/config.py
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def load_llm_config(config_path: str = "config/llm_config.json") -> Dict[str, Any]:
    """
    Load LLM configuration from JSON file
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dictionary containing the configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
        ValueError: If config validation fails
    """
    # Make path relative to backend directory if not absolute
    if not os.path.isabs(config_path):
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(backend_dir, config_path)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"LLM configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON in config file {config_path}: {e}")
    
    # Validate the configuration
    validate_config(config)
    
    logger.info(f"Loaded LLM configuration from {config_path}")
    return config

def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate LLM configuration structure
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_keys = ["default", "nodes", "providers"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required configuration key: {key}")
    
    # Validate default configuration
    default_config = config["default"]
    if not isinstance(default_config, dict):
        raise ValueError("Default configuration must be a dictionary")
    
    required_default_keys = ["provider", "model", "config"]
    for key in required_default_keys:
        if key not in default_config:
            raise ValueError(f"Missing required key in default configuration: {key}")
    
    # Validate providers
    providers = config["providers"]
    if not isinstance(providers, dict):
        raise ValueError("Providers configuration must be a dictionary")
    
    supported_providers = ["gemini", "huggingface", "kaggle"]
    for provider in supported_providers:
        if provider not in providers:
            raise ValueError(f"Missing provider configuration: {provider}")
        
        if not isinstance(providers[provider], dict):
            raise ValueError(f"Provider {provider} configuration must be a dictionary")
        
        if "default_config" not in providers[provider]:
            raise ValueError(f"Missing default_config for provider: {provider}")
    
    # Validate nodes configuration
    nodes = config["nodes"]
    if not isinstance(nodes, dict):
        raise ValueError("Nodes configuration must be a dictionary")
    
    for node_name, node_config in nodes.items():
        if not isinstance(node_config, dict):
            raise ValueError(f"Node {node_name} configuration must be a dictionary")
        
        required_node_keys = ["provider", "model", "config"]
        for key in required_node_keys:
            if key not in node_config:
                raise ValueError(f"Missing required key in node {node_name} configuration: {key}")
        
        # Check if provider is supported
        if node_config["provider"] not in supported_providers:
            raise ValueError(f"Unsupported provider in node {node_name}: {node_config['provider']}")
    
    logger.info("LLM configuration validation passed")

def get_node_config(config: Dict[str, Any], node_name: str) -> Dict[str, Any]:
    """
    Get configuration for a specific node, falling back to default if not found
    
    Args:
        config: Full configuration dictionary
        node_name: Name of the node to get configuration for
        
    Returns:
        Node configuration dictionary
    """
    if node_name in config["nodes"]:
        return config["nodes"][node_name]
    else:
        logger.warning(f"No specific configuration found for node {node_name}, using default")
        return config["default"]

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries, with override_config taking precedence
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    merged = base_config.copy()
    for key, value in override_config.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged

def validate_environment_variables() -> Dict[str, bool]:
    """
    Validate required environment variables for different providers
    
    Returns:
        Dictionary with provider names as keys and availability as boolean values
    """
    env_status = {}
    
    # Check Gemini API key
    env_status["gemini"] = bool(os.environ.get("GEMINI_API_KEY"))
    
    # Check Kaggle credentials
    kaggle_username = os.environ.get("KAGGLE_USERNAME")
    kaggle_key = os.environ.get("KAGGLE_KEY")
    env_status["kaggle"] = bool(kaggle_username and kaggle_key)
    
    # HuggingFace doesn't require API keys for most models, just local setup
    env_status["huggingface"] = True
    
    return env_status
