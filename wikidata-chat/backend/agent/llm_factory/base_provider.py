# backend/agent/llm_factory/base_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMProvider(ABC):
    """
    Base class for all LLM providers.
    Defines the interface that all providers must implement.
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        """
        Initialize the LLM provider
        
        Args:
            model_name: Name/identifier of the model
            config: Configuration dictionary for the model
        """
        self.model_name = model_name
        self.config = config
        self.model = None
        self.tokenizer = None
        self._is_loaded = False
    
    @abstractmethod
    def load_model(self) -> None:
        """
        Load the model and tokenizer.
        This method should be implemented by each provider.
        """
        pass
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate a response using the loaded model
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        pass
    
    @abstractmethod
    def is_chat_template_supported(self) -> bool:
        """
        Check if the model supports chat templates
        
        Returns:
            True if chat templates are supported, False otherwise
        """
        pass
    
    def apply_chat_template(self, messages: list, **kwargs) -> str:
        """
        Apply chat template to messages if supported
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            **kwargs: Additional template parameters
            
        Returns:
            Formatted prompt string
        """
        if self.is_chat_template_supported():
            return self._apply_chat_template_impl(messages, **kwargs)
        else:
            # Fallback to simple concatenation
            return self._fallback_template(messages)
    
    @abstractmethod
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Provider-specific implementation of chat template application
        """
        pass
    
    def _fallback_template(self, messages: list) -> str:
        """
        Fallback template when chat templates are not supported
        """
        prompt = ""
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                prompt += f"{content}\n"
            elif role == "user":
                prompt += f"{content}\n"
            elif role == "assistant":
                prompt += f"{content}\n"
        return prompt
    
    def is_loaded(self) -> bool:
        """
        Check if the model is loaded
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self._is_loaded
    
    def get_config(self) -> Dict[str, Any]:
        """
        Get the current configuration
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Update configuration parameters
        
        Args:
            new_config: New configuration values to merge
        """
        self.config.update(new_config)
