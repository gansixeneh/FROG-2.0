# backend/agent/llm_factory/providers/kaggle_provider.py
import os
import logging
from typing import Dict, Any, Optional
from ..base_provider import BaseLLMProvider
from .unsloth_provider import UnslothProvider

logger = logging.getLogger(__name__)

class KaggleProvider(BaseLLMProvider):
    """
    Provider for Kaggle models that downloads datasets and loads them with Unsloth
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        super().__init__(model_name, config)
        self.unsloth_provider = None
        self.model_path = None
        
    def _validate_kaggle_credentials(self) -> None:
        """Validate that Kaggle credentials are available"""
        kaggle_username = os.environ.get("KAGGLE_USERNAME")
        kaggle_key = os.environ.get("KAGGLE_KEY")
        
        if not kaggle_username or not kaggle_key:
            raise ValueError(
                "KAGGLE_USERNAME and KAGGLE_KEY environment variables are required for Kaggle provider"
            )
    
    def _download_kaggle_dataset(self) -> str:
        """
        Download dataset from Kaggle if needed
        
        Returns:
            Path to the downloaded model
        """
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
        except ImportError as e:
            raise ImportError(
                "Kaggle API is required for KaggleProvider. "
                "Please install it with: pip install kaggle"
            ) from e
        
        # Get configuration
        dataset = self.config.get("dataset")
        model_files = self.config.get("model_files")
        cache_dir = self.config.get("cache_dir", "./kaggle_models")
        force_download = self.config.get("force_download", False)
        
        if not dataset:
            raise ValueError("dataset must be specified in config for Kaggle provider")
        if not model_files:
            raise ValueError("model_files must be specified in config for Kaggle provider")
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Construct model path
        model_path = os.path.join(cache_dir, model_files)
        
        # Check if model already exists and force_download is False
        if os.path.exists(model_path) and not force_download:
            logger.info(f"Model already exists at {model_path}, skipping download")
            return model_path
        
        # Initialize Kaggle API
        api = KaggleApi()
        api.authenticate()
        
        logger.info(f"Downloading Kaggle dataset: {dataset} to {cache_dir}")
        
        try:
            # Download and extract dataset
            api.dataset_download_files(dataset, path=cache_dir, unzip=True)
            logger.info(f"Successfully downloaded dataset {dataset}")
        except Exception as e:
            logger.error(f"Error downloading Kaggle dataset {dataset}: {e}")
            raise
        
        # Verify model path exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model files not found at expected path: {model_path}. "
                f"Check the model_files configuration: {model_files}"
            )
        
        return model_path
    
    def load_model(self) -> None:
        """Load the Kaggle model by downloading it and using Unsloth"""
        if self._is_loaded:
            return
        
        # Validate credentials
        self._validate_kaggle_credentials()
        
        # Download model if needed
        self.model_path = self._download_kaggle_dataset()
        
        # Create Unsloth provider configuration
        unsloth_config = self.config.copy()
        
        # Remove Kaggle-specific keys that shouldn't be passed to Unsloth
        kaggle_keys = {"dataset", "model_files", "cache_dir", "force_download"}
        for key in kaggle_keys:
            unsloth_config.pop(key, None)
        
        # Create Unsloth provider with the downloaded model path
        self.unsloth_provider = UnslothProvider(
            model_name=self.model_path,
            config=unsloth_config
        )
        
        # Load the model using Unsloth
        self.unsloth_provider.load_model()
        
        # Delegate to Unsloth provider
        self.model = self.unsloth_provider.model
        self.tokenizer = self.unsloth_provider.tokenizer
        
        self._is_loaded = True
        logger.info(f"Loaded Kaggle model from: {self.model_path}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using the downloaded Kaggle model via Unsloth
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.unsloth_provider.generate_response(prompt, **kwargs)
    
    def is_chat_template_supported(self) -> bool:
        """
        Check if the model supports chat templates (delegated to Unsloth provider)
        
        Returns:
            True if chat templates are supported, False otherwise
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.unsloth_provider.is_chat_template_supported()
    
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Apply chat template using Unsloth provider
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional template parameters
            
        Returns:
            Formatted prompt string
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.unsloth_provider._apply_chat_template_impl(messages, **kwargs)
    
    def get_pipeline(self):
        """
        Get the HuggingFace pipeline wrapper
        
        Returns:
            HuggingFacePipeline instance
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.unsloth_provider.get_pipeline()
    
    def get_raw_pipeline(self):
        """
        Get the raw transformers pipeline
        
        Returns:
            Raw transformers pipeline
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.unsloth_provider.get_raw_pipeline()
    
    def cleanup(self) -> None:
        """
        Clean up resources
        """
        if self.unsloth_provider:
            self.unsloth_provider.cleanup()
            self.unsloth_provider = None
        
        self.model = None
        self.tokenizer = None
        self._is_loaded = False
        
        logger.info(f"Cleaned up Kaggle model: {self.model_name}")
    
    def get_model_path(self) -> Optional[str]:
        """
        Get the local path to the downloaded model
        
        Returns:
            Path to the model directory
        """
        return self.model_path
