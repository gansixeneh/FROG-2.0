# backend/agent/llm_factory/factory.py
import os
import logging
from typing import Dict, Any, Optional, Union
from .config import load_llm_config, get_node_config, validate_environment_variables
from .base_provider import BaseLLMProvider
from .providers import GeminiProvider, OllamaProvider

logger = logging.getLogger(__name__)

class LLMFactory:
    """
    Factory class for creating and managing LLM providers based on configuration
    """
    
    def __init__(self, config_path: str = "config/llm_config.json"):
        """
        Initialize the LLM factory
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self._model_cache: Dict[str, BaseLLMProvider] = {}
        self.config = load_llm_config(config_path)
        
        # Validate environment variables
        self.env_status = validate_environment_variables()
        self._log_environment_status()
        
        logger.info("Initialized LLMFactory")
    
    def _log_environment_status(self) -> None:
        """Log the status of environment variables for different providers"""
        for provider, available in self.env_status.items():
            status = "✓" if available else "✗"
            logger.info(f"Provider {provider}: {status} {'Available' if available else 'Missing credentials'}")
    
    def _get_provider_class(self, provider_name: str) -> type:
        """
        Get the provider class for a given provider name
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider class
            
        Raises:
            ValueError: If provider is not supported
        """
        provider_classes = {
            "gemini": GeminiProvider,
            "ollama": OllamaProvider
        }
        
        if provider_name not in provider_classes:
            raise ValueError(f"Unsupported provider: {provider_name}")
        
        return provider_classes[provider_name]    
    def _create_cache_key(self, node_name: Optional[str], provider: str, model: str) -> str:
        """
        Create a cache key for a model instance
        
        Args:
            node_name: Name of the node (None for default)
            provider: Provider name
            model: Model name
            
        Returns:
            Cache key string
        """
        node_key = node_name or "default"
        return f"{node_key}_{provider}_{model}"
    
    def _check_provider_availability(self, provider_name: str) -> None:
        """
        Check if a provider is available (has required credentials)
        
        Args:
            provider_name: Name of the provider to check
            
        Raises:
            ValueError: If provider is not available
        """
        if not self.env_status.get(provider_name, False):
            if provider_name == "gemini":
                raise ValueError(
                    "Gemini provider is not available. "
                    "Please set the GEMINI_API_KEY environment variable."
                )
    
    def get_model(self, node_name: Optional[str] = None, 
                  force_reload: bool = False) -> BaseLLMProvider:
        """
        Get a model instance for the specified node or default configuration
        
        Args:
            node_name: Name of the node to get model for (None for default)
            force_reload: If True, reload the model even if cached
            
        Returns:
            LLM provider instance
            
        Raises:
            ValueError: If configuration is invalid or provider is unavailable
        """
        # Get configuration for the node
        node_config = get_node_config(self.config, node_name or "default")
        
        provider_name = node_config["provider"]
        model_name = node_config["model"]
        model_config = node_config["config"]        
        # Check provider availability
        self._check_provider_availability(provider_name)
        
        # Create cache key
        cache_key = self._create_cache_key(node_name, provider_name, model_name)
        
        # Return cached model if available and not forcing reload
        if cache_key in self._model_cache and not force_reload:
            logger.info(f"Using cached model for {cache_key}")
            return self._model_cache[cache_key]
        
        # Get provider class
        provider_class = self._get_provider_class(provider_name)
        
        # Merge with provider defaults
        provider_defaults = self.config["providers"][provider_name]["default_config"]
        merged_config = {**provider_defaults, **model_config}
        
        # Create provider instance
        logger.info(f"Creating new {provider_name} model: {model_name}")
        provider = provider_class(model_name, merged_config)
        
        # Cache the provider
        self._model_cache[cache_key] = provider
        
        logger.info(f"Created and cached model for {cache_key}")
        return provider
    
    def get_model_for_entity_extraction(self) -> BaseLLMProvider:
        """Get model specifically for entity extraction"""
        return self.get_model("EntityExtractionNode")
    
    def get_model_for_verbalization(self) -> BaseLLMProvider:
        """Get model specifically for verbalization"""
        return self.get_model("VerbalizationNode")
    
    def get_model_for_sparql_generation(self) -> BaseLLMProvider:
        """Get model specifically for SPARQL generation"""
        return self.get_model("SparqlGenerationNode")
    
    def get_model_for_answer_generation(self) -> BaseLLMProvider:
        """Get model specifically for answer generation"""
        return self.get_model("AnswerGenerationNode")    
    def list_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available models from configuration
        
        Returns:
            Dictionary with node names as keys and model info as values
        """
        models = {}
        
        # Add default model
        default_config = self.config["default"]
        models["default"] = {
            "provider": default_config["provider"],
            "model": default_config["model"],
            "available": self.env_status.get(default_config["provider"], False)
        }
        
        # Add node-specific models
        for node_name, node_config in self.config["nodes"].items():
            models[node_name] = {
                "provider": node_config["provider"],
                "model": node_config["model"],
                "available": self.env_status.get(node_config["provider"], False)
            }
        
        return models
    
    def clear_cache(self) -> None:
        """Clear all cached models"""
        for provider in self._model_cache.values():
            if hasattr(provider, 'cleanup'):
                provider.cleanup()
        
        self._model_cache.clear()
        logger.info("Cleared model cache")
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self.config = load_llm_config(self.config_path)
        self.env_status = validate_environment_variables()
        self._log_environment_status()
        logger.info("Reloaded configuration")
    
    def get_cached_models(self) -> Dict[str, str]:
        """
        Get information about currently cached models
        
        Returns:
            Dictionary with cache keys and model names
        """
        return {
            cache_key: provider.model_name 
            for cache_key, provider in self._model_cache.items()
        }
    
    def __del__(self):
        """Cleanup when factory is destroyed"""
        self.clear_cache()