# backend/agent/langgraph/utils/singletons/model_singletons.py
"""
Singleton module for NLP models to prevent duplicate model loading across agent instances.
This helps reduce memory usage when multiple WebSocket connections are established.
"""
import logging
from sentence_transformers import SentenceTransformer

# Configure logging
logger = logging.getLogger(__name__)

class ModelSingletons:
    """
    Singleton class to manage NLP model instances across the application.
    This prevents duplicate model loading when multiple WebSocket connections are created.
    """
    _instance = None
    _models = {}

    def __new__(cls):
        if cls._instance is None:
            logger.info("Creating ModelSingletons instance")
            cls._instance = super(ModelSingletons, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_sentence_transformer(cls, model_name, **kwargs):
        """
        Get or create a SentenceTransformer model instance.
        
        Args:
            model_name: Name of the SentenceTransformer model
            **kwargs: Additional arguments to pass to SentenceTransformer constructor
            
        Returns:
            SentenceTransformer instance
        """
        # Create a unique key for this model configuration
        model_key = f"sentence_transformer_{model_name}_{hash(frozenset(kwargs.items()))}"
        
        if model_key not in cls._models:
            logger.info(f"Creating new SentenceTransformer instance: {model_name}")
            cls._models[model_key] = SentenceTransformer(model_name, **kwargs)
        else:
            logger.info(f"Reusing existing SentenceTransformer instance: {model_name}")
            
        return cls._models[model_key]
    
    @classmethod
    def clear_models(cls):
        """Clear all cached models (useful for testing or memory management)"""
        cls._models.clear()
        logger.info("Cleared all cached models")

# Create a convenience function to get models
def get_sentence_transformer(model_name, **kwargs):
    """Get a SentenceTransformer model instance from the singleton cache"""
    return ModelSingletons.get_sentence_transformer(model_name, **kwargs)
