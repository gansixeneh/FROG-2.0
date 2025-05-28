# backend/agent/llm_factory/providers/kaggle_provider.py
import os
import logging
from typing import Dict, Any, Optional
from ..base_provider import BaseLLMProvider
from .ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

class KaggleProvider(BaseLLMProvider):
    """
    Provider for Kaggle models that downloads datasets and loads them with Ollama
    """
    
    def __init__(self, model_name: str, config: Dict[str, Any]):
        super().__init__(model_name, config)
        self.ollama_provider = None
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
        """Load the Kaggle model by downloading it and using Ollama"""
        if self._is_loaded:
            return
        
        # Validate credentials
        self._validate_kaggle_credentials()
        
        # Download model if needed
        self.model_path = self._download_kaggle_dataset()
        
        # Create Ollama provider configuration
        ollama_config = self.config.copy()
        
        # Remove Kaggle-specific keys that shouldn't be passed to Ollama
        kaggle_keys = {"dataset", "model_files", "cache_dir", "force_download"}
        for key in kaggle_keys:
            ollama_config.pop(key, None)
        
        # Create a model name for Ollama based on the Kaggle dataset
        # This assumes the user has imported the model into Ollama already
        dataset_name = self.config.get("dataset", "").split("/")[-1]
        model_name = self.config.get("ollama_model_name", f"kaggle-{dataset_name}")
        
        # Create Ollama provider with the specified model name
        self.ollama_provider = OllamaProvider(
            model_name=model_name,
            config=ollama_config
        )
        
        # Load the model using Ollama
        self.ollama_provider.load_model()
        
        # Consider the model loaded
        self._is_loaded = True
        logger.info(f"Loaded Kaggle model {dataset_name} using Ollama as {model_name}")
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """
        Generate response using the downloaded Kaggle model via Ollama
        
        Args:
            prompt: Input prompt
            **kwargs: Additional generation parameters
            
        Returns:
            Generated response text
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.ollama_provider.generate_response(prompt, **kwargs)
    
    def is_chat_template_supported(self) -> bool:
        """
        Check if the model supports chat templates (delegated to Ollama provider)
        
        Returns:
            True if chat templates are supported, False otherwise
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.ollama_provider.is_chat_template_supported()
    
    def _apply_chat_template_impl(self, messages: list, **kwargs) -> str:
        """
        Apply chat template using Ollama provider
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional template parameters
            
        Returns:
            Formatted prompt string
        """
        if not self._is_loaded:
            self.load_model()
        
        return self.ollama_provider._apply_chat_template_impl(messages, **kwargs)
    
    def cleanup(self) -> None:
        """
        Clean up resources
        """
        self.ollama_provider = None
        self._is_loaded = False
        
        logger.info(f"Cleaned up Kaggle model: {self.model_name}")
    
    def get_model_path(self) -> Optional[str]:
        """
        Get the local path to the downloaded model
        
        Returns:
            Path to the model directory
        """
        return self.model_path