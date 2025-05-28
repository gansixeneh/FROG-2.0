# backend/agent/llm_factory/providers/huggingface_provider.py
import os
import logging
import gc
from typing import Dict, Any, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
from langchain_community.llms.huggingface_pipeline import HuggingFacePipeline
from ..base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

class HuggingFaceProvider(BaseLLMProvider):
    """
    Provider for Hugging Face models using AutoModelForCausalLM with quantization
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        super().__init__(model_name, config)
        self.pipeline = None
        self.hf_pipeline = None
        self.adapter_path = config.get("adapter_path", None)
        
    def load_model(self) -> None:
        """Load the model using AutoModelForCausalLM with quantization"""
        if self._is_loaded:
            return
            
        try:
            # Clear memory first
            if hasattr(self, 'model') and self.model is not None:
                del self.model
            if hasattr(self, 'tokenizer') and self.tokenizer is not None:
                del self.tokenizer
                
            # Run garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Extract model loading parameters
            load_in_4bit = self.config.get("load_in_4bit", True)
            use_double_quant = self.config.get("use_double_quant", True)
            quant_type = self.config.get("quant_type", "nf4")
            trust_remote_code = self.config.get("trust_remote_code", True)
            adapter_path = self.adapter_path
            
            # Configure BitsAndBytes for quantization
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=load_in_4bit,
                bnb_4bit_use_double_quant=use_double_quant,
                bnb_4bit_quant_type=quant_type,
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8 else torch.float16
            )
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=trust_remote_code
            )
            
            # Set padding token if needed
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with adapter if specified
            if adapter_path and not adapter_path.endswith('.pt'):
                # For loading with adapter weights, first load the base model
                try:
                    from peft import PeftModel
                    base_model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        quantization_config=bnb_config,
                        device_map="auto",
                        trust_remote_code=trust_remote_code
                    )
                    self.model = PeftModel.from_pretrained(base_model, adapter_path)
                    logger.info(f"Loaded model {self.model_name} with adapter {adapter_path}")
                except ImportError:
                    logger.error("PEFT not installed. Please install it with: pip install peft")
                    raise
                except Exception as e:
                    logger.error(f"Error loading model with adapter: {e}")
                    raise
            else:
                # Load base model with quantization
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=bnb_config,
                    device_map="auto",
                    trust_remote_code=trust_remote_code
                )
                logger.info(f"Loaded model {self.model_name}")
            
            # Create inference pipeline
            self.pipeline = pipeline(
                task="text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                max_new_tokens=self.config.get("max_new_tokens", 512),
                do_sample=self.config.get("do_sample", False),
                temperature=self.config.get("temperature", 0.2),
                repetition_penalty=self.config.get("repetition_penalty", 1.1),
                return_full_text=False
            )
            
            # Create HuggingFace pipeline wrapper
            self.hf_pipeline = HuggingFacePipeline(pipeline=self.pipeline)
            
            self._is_loaded = True
            logger.info(f"Successfully loaded HuggingFace model: {self.model_name}")
            
        except Exception as e:
            logger.error(f"Error loading HuggingFace model {self.model_name}: {e}")
            raise
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using the loaded model
        
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
            logger.error(f"Error generating response with HuggingFace model: {e}")
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
        if hasattr(self, 'model') and self.model is not None:
            del self.model
        if hasattr(self, 'tokenizer') and self.tokenizer is not None:
            del self.tokenizer
        if hasattr(self, 'pipeline') and self.pipeline is not None:
            del self.pipeline
        if hasattr(self, 'hf_pipeline') and self.hf_pipeline is not None:
            del self.hf_pipeline
            
        # Clear GPU cache
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        # Run garbage collection
        gc.collect()
            
        self._is_loaded = False
        logger.info(f"Cleaned up HuggingFace model: {self.model_name}")
