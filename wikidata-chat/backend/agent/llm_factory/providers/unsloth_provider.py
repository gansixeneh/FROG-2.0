# backend/agent/llm_factory/providers/unsloth_provider.py
import os
import logging
from typing import Dict, Any, Optional
import torch
from transformers import pipeline
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from ..base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class UnslothProvider(BaseLLMProvider):
    """
    Provider for Unsloth models using FastLanguageModel.from_pretrained()
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        super().__init__(model_name, config)
        self.pipeline = None
        self.hf_pipeline = None
        
    def load_model(self) -> None:
        """Load the Unsloth model"""
        if self._is_loaded:
            return
            
        try:
            # Import Unsloth (only when needed to avoid import errors if not installed)
            from unsloth import FastLanguageModel
            
            # Extract model loading parameters
            max_seq_length = self.config.get("max_seq_length", 2048)
            dtype = self.config.get("dtype", None)
            load_in_4bit = self.config.get("load_in_4bit", True)
            
            # Load model and tokenizer
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.model_name,
                max_seq_length=max_seq_length,
                dtype=dtype,
                load_in_4bit=load_in_4bit,
            )
            
            # Create inference pipeline
            self.pipeline = pipeline(
                task="text-generation",
                model=self.model,
                torch_dtype=torch.bfloat16,
                tokenizer=self.tokenizer,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=self.config.get("max_new_tokens", 512),
                do_sample=self.config.get("do_sample", False),
                return_full_text=False,
                repetition_penalty=self.config.get("repetition_penalty", 1.1)
            )
            
            # Create HuggingFace pipeline wrapper
            self.hf_pipeline = HuggingFacePipeline(pipeline=self.pipeline)
            
            self._is_loaded = True
            logger.info(f"Loaded Unsloth model: {self.model_name}")
            
        except ImportError as e:
            raise ImportError(
                "Unsloth is required for UnslothProvider. "
                "Please install it with: pip install unsloth"
            ) from e
        except Exception as e:
            logger.error(f"Error loading Unsloth model {self.model_name}: {e}")
            raise
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using Unsloth model
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        try:
            # Use the HuggingFace pipeline wrapper for consistency
            response = self.hf_pipeline.invoke(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating response with Unsloth: {e}")
            raise
    
    def is_chat_template_supported(self) -> bool:
        """
        Check if the model supports chat templates
        
        Returns:
            True if tokenizer has chat_template, False otherwise
        """
        if not self._is_loaded:
            self.load_model()
        
        return (
            hasattr(self.tokenizer, "chat_template") 
            and self.tokenizer.chat_template is not None
        )
    
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Apply chat template using the tokenizer's chat template
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional template parameters
            
        Returns:
            Formatted prompt string
        """
        if not self._is_loaded:
            self.load_model()
        
        try:
            return self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=kwargs.get("add_generation_prompt", True),
                **kwargs
            )
        except Exception as e:
            logger.warning(f"Error applying chat template: {e}, falling back to simple format")
            return self._fallback_template(messages)
    
    def get_pipeline(self) -> HuggingFacePipeline:
        """
        Get the HuggingFace pipeline wrapper for compatibility
        
        Returns:
            HuggingFacePipeline instance
        """
        if not self._is_loaded:
            self.load_model()
        return self.hf_pipeline
    
    def get_raw_pipeline(self):
        """
        Get the raw transformers pipeline
        
        Returns:
            Raw transformers pipeline
        """
        if not self._is_loaded:
            self.load_model()
        return self.pipeline
    
    def cleanup(self) -> None:
        """
        Clean up GPU memory
        """
        if self.model is not None:
            del self.model
        if self.tokenizer is not None:
            del self.tokenizer
        if self.pipeline is not None:
            del self.pipeline
        if self.hf_pipeline is not None:
            del self.hf_pipeline
            
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self._is_loaded = False
        logger.info(f"Cleaned up Unsloth model: {self.model_name}")
