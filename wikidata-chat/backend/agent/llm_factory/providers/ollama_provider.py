# backend/agent/llm_factory/providers/ollama_provider.py
import os
import logging
import requests
import json
from typing import Dict, Any, Optional
from ..base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    """
    Provider for Ollama models optimized for macOS compatibility
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        """
        Initialize the Ollama provider
        
        Args:
            model_name: Name of the model (e.g., 'llama2', 'qwen:3b-instruct')
            config: Configuration dictionary for the model
                - base_url: URL of the Ollama server (default: http://localhost:11434)
                - quantization: Quantization level to use (e.g., 'q4_0', 'q4_1', 'q5_0', 'q5_1', 'q8_0')
                  Note: Only applies when pulling new models
        """
        super().__init__(model_name, config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self.quantization = config.get("quantization", None)
        
        # If quantization is specified and not already in model name, append it
        if self.quantization and self.quantization not in self.model_name:
            if "-" not in self.model_name:
                self.model_name = f"{self.model_name}-{self.quantization}"
            else:
                logger.info(f"Quantization specified ({self.quantization}) but model name already has a suffix. Using model name as is: {self.model_name}")
        
    def load_model(self) -> None:
        """Load the Ollama model"""
        if self._is_loaded:
            return
            
        # Ensure base URL doesn't have a trailing slash
        if self.base_url.endswith('/'):
            self.base_url = self.base_url[:-1]
        
        # Test if Ollama is available by pinging the API
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                raise ConnectionError(f"Failed to connect to Ollama at {self.base_url}: {response.status_code}")
            
            # Check if model is available
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"Model {self.model_name} not found in Ollama. It will be pulled when used.")
                
                # Attempt to pull the model if not found
                try:
                    logger.info(f"Attempting to pull model {self.model_name}...")
                    pull_response = requests.post(
                        f"{self.base_url}/api/pull",
                        json={"name": self.model_name}
                    )
                    
                    if pull_response.status_code == 200:
                        logger.info(f"Successfully pulled model {self.model_name}")
                    else:
                        logger.warning(f"Failed to pull model {self.model_name}: {pull_response.text}")
                except Exception as pull_err:
                    logger.warning(f"Error pulling model: {pull_err}")
            
            self._is_loaded = True
            logger.info(f"Successfully connected to Ollama at {self.base_url}")
            
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            raise
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using Ollama model
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        # Merge config with kwargs, giving priority to kwargs
        generation_config = self.config.copy()
        generation_config.update(kwargs)
        
        # Map config parameters to Ollama parameters
        ollama_params = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        
        # Map common parameters to Ollama's format
        if "temperature" in generation_config:
            ollama_params["temperature"] = generation_config["temperature"]
            
        if "top_p" in generation_config:
            ollama_params["top_p"] = generation_config["top_p"]
            
        if "max_new_tokens" in generation_config:
            # Ollama uses 'num_predict' instead of 'max_new_tokens'
            ollama_params["num_predict"] = generation_config["max_new_tokens"]
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=ollama_params
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Error generating response: {response.text}")
            
            result = response.json()
            return result.get("response", "")
            
        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            raise
    
    def is_chat_template_supported(self) -> bool:
        """
        Check if the model supports chat templates
        
        Returns:
            True if the model name contains 'chat' or is a known chat model
        """
        # Most Ollama models support chat templates
        chat_models = [
            "llama2-chat", "mistral-chat", "mistral-instruct", "mixtral", "zephyr", 
            "vicuna", "orca", "wizard", "qwen", "codellama-instruct"
        ]
        
        model_name_lower = self.model_name.lower()
        
        # Check if model name contains any of the chat model identifiers
        return ("chat" in model_name_lower or 
                "instruct" in model_name_lower or
                any(model in model_name_lower for model in chat_models))
    
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Apply chat template for Ollama
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional template parameters
            
        Returns:
            Formatted prompt string
        """
        # For Ollama, we'll use a simple template that works well with most models
        formatted_messages = []
        
        for message in messages:
            role = message.get("role", "user").lower()
            content = message.get("content", "")
            
            if role == "system":
                formatted_messages.append(f"<s>[SYSTEM] {content}</s>")
            elif role == "user":
                formatted_messages.append(f"<s>[USER] {content}</s>")
            elif role == "assistant":
                formatted_messages.append(f"<s>[ASSISTANT] {content}</s>")
        
        # Add assistant prompt
        if kwargs.get("add_generation_prompt", True):
            formatted_messages.append("<s>[ASSISTANT] ")
        
        return "\n".join(formatted_messages)
    
    def chat_completion(self, messages: list, **kwargs) -> str:
        """
        Generate response using Ollama's chat completion API
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        # Merge config with kwargs, giving priority to kwargs
        generation_config = self.config.copy()
        generation_config.update(kwargs)
        
        # Format messages for Ollama chat API
        ollama_messages = []
        for message in messages:
            role = message.get("role", "user").lower()
            # Map to Ollama's role format
            if role == "assistant":
                role = "assistant"
            elif role == "system":
                role = "system"
            else:
                role = "user"
                
            ollama_messages.append({
                "role": role,
                "content": message.get("content", "")
            })
        
        # Prepare request parameters
        ollama_params = {
            "model": self.model_name,
            "messages": ollama_messages,
            "stream": False,
        }
        
        # Add temperature if provided
        if "temperature" in generation_config:
            ollama_params["temperature"] = generation_config["temperature"]
            
        if "top_p" in generation_config:
            ollama_params["top_p"] = generation_config["top_p"]
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=ollama_params
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Error generating chat completion: {response.text}")
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except Exception as e:
            logger.error(f"Error generating chat completion with Ollama: {e}")
            # Fall back to generate_response with template
            logger.info("Falling back to generate_response with template")
            prompt = self.apply_chat_template(messages)
            return self.generate_response(prompt, **kwargs)