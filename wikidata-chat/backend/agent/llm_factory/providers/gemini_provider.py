# backend/agent/llm_factory/providers/gemini_provider.py
import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai
from ..base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """
    Provider for Google's Gemini models using the generativeai library
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        super().__init__(model_name, config)
        self.api_key = None
        
    def load_model(self) -> None:
        """Load the Gemini model"""
        if self._is_loaded:
            return
            
        # Get API key from environment
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required for Gemini provider")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Initialize the model
        self.model = genai.GenerativeModel(model_name=self.model_name)
        
        self._is_loaded = True
        logger.info(f"Loaded Gemini model: {self.model_name}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using Gemini model
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters (merged with config)
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        # Merge config with kwargs, giving priority to kwargs
        generation_config = self.config.copy()
        generation_config.update(kwargs)
        
        # Remove keys that aren't valid for Gemini generation
        valid_keys = {"temperature", "top_p", "top_k", "max_output_tokens", "candidate_count"}
        generation_config = {k: v for k, v in generation_config.items() if k in valid_keys}
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(**generation_config)
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating response with Gemini: {e}")
            raise
    
    def is_chat_template_supported(self) -> bool:
        """
        Gemini doesn't use traditional chat templates in the same way as local models
        
        Returns:
            False - we'll handle conversation formatting manually
        """
        return False
    
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Gemini doesn't use chat templates in the traditional sense,
        so this falls back to the base implementation
        """
        return self._fallback_template(messages)
    
    def generate_with_messages(self, messages: list, **kwargs) -> str:
        """
        Generate response using Gemini's chat interface
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        # For Gemini, we can use the chat interface if there are multiple messages
        if len(messages) > 1:
            # Convert messages to Gemini format
            chat_history = []
            for msg in messages[:-1]:  # All but the last message
                if msg["role"] == "user":
                    chat_history.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "assistant":
                    chat_history.append({"role": "model", "parts": [msg["content"]]})
                # Skip system messages for now in chat history
            
            # Start chat with history
            chat = self.model.start_chat(history=chat_history)
            
            # Send the last message
            last_message = messages[-1]
            if last_message["role"] == "user":
                response = chat.send_message(last_message["content"])
                return response.text
        
        # Fallback to single prompt generation
        prompt = self.apply_chat_template(messages)
        return self.generate_response(prompt, **kwargs)
