# backend/agent/langgraph/utils/entity_retrieval_factory.py
import logging
from typing import Optional, Dict, Any
import os

# Import source-specific entity retrieval classes
from .entity_retrieval import UniversityEntityRetrieval
from .property_retrieval_legal import LegalPropertyRetrieval
from .property_retrieval_gesis import GesisPropertyRetrieval

# Import knowledge graph metadata
from .knowledge_graph_metadata import get_knowledge_graph_metadata

# Configure logging
logger = logging.getLogger(__name__)

class EntityRetrievalFactory:
    """
    Factory class for creating appropriate entity retrieval instances
    based on the knowledge source.
    """
    
    def __init__(self):
        self._retrievers = {}
        self.kg_metadata = get_knowledge_graph_metadata()
        
    def get_entity_retriever(self, knowledge_source: str = "wikidata"):
        """
        Get or create an entity retriever for the specified knowledge source
        
        Args:
            knowledge_source: The knowledge source identifier (e.g., 'wikidata', 'curriculum')
            
        Returns:
            An appropriate entity retriever instance
        """
        # Return cached instance if available
        if knowledge_source in self._retrievers:
            logger.info(f"Using cached entity retriever for {knowledge_source}")
            return self._retrievers[knowledge_source]
            
        # Create a new instance based on the knowledge source
        logger.info(f"Creating new entity retriever for {knowledge_source}")
        
        if knowledge_source == "curriculum":
            try:
                retriever = UniversityEntityRetrieval()
                self._retrievers[knowledge_source] = retriever
                return retriever
            except Exception as e:
                logger.error(f"Error creating UniversityEntityRetrieval: {e}")
                return None
        
        elif knowledge_source == "legal":
            try:
                # Get endpoint from metadata
                endpoint = self.kg_metadata.get_endpoint(knowledge_source)
                retriever = LegalPropertyRetrieval(endpoint_url=endpoint)
                self._retrievers[knowledge_source] = retriever
                return retriever
            except Exception as e:
                logger.error(f"Error creating LegalPropertyRetrieval: {e}")
                return None
                
        elif knowledge_source == "gesis":
            try:
                # Get endpoint from metadata
                endpoint = self.kg_metadata.get_endpoint(knowledge_source)
                retriever = GesisPropertyRetrieval(endpoint_url=endpoint)
                self._retrievers[knowledge_source] = retriever
                return retriever
            except Exception as e:
                logger.error(f"Error creating GesisPropertyRetrieval: {e}")
                return None
        
        # Default case - return None for wikidata as it doesn't use entity retrieval
        logger.info(f"No specific entity retriever needed for {knowledge_source}")
        return None
        
    def close_all(self):
        """Close all retrievers"""
        for source, retriever in self._retrievers.items():
            if hasattr(retriever, 'close'):
                try:
                    retriever.close()
                    logger.info(f"Closed entity retriever for {source}")
                except Exception as e:
                    logger.error(f"Error closing entity retriever for {source}: {e}")

# Global factory instance
_entity_retrieval_factory = None

def get_entity_retrieval_factory():
    """Get the global entity retrieval factory instance"""
    global _entity_retrieval_factory
    if _entity_retrieval_factory is None:
        _entity_retrieval_factory = EntityRetrievalFactory()
    return _entity_retrieval_factory
