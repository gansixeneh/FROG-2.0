# backend/agent/langgraph/utils/property_retrieval_factory.py
import logging
from typing import Optional, Dict, Any
import os

# Import source-specific property retrieval classes
from .wikidata_property_retrieval import WikidataPropertyRetrieval
from .university_property_retrieval import UniversityPropertyRetrieval
from .property_retrieval_legal import LegalPropertyRetrieval
from .property_retrieval_gesis import GesisPropertyRetrieval

# Import knowledge graph metadata
from .knowledge_graph_metadata import get_knowledge_graph_metadata

# Configure logging
logger = logging.getLogger(__name__)

class PropertyRetrievalFactory:
    """
    Factory class for creating appropriate property retrieval instances
    based on the knowledge source.
    """
    
    def __init__(self):
        self._retrievers = {}
        self.kg_metadata = get_knowledge_graph_metadata()
        
    def get_property_retriever(self, knowledge_source: str = "wikidata", df_properties=None):
        """
        Get or create a property retriever for the specified knowledge source
        
        Args:
            knowledge_source: The knowledge source identifier (e.g., 'wikidata', 'curriculum')
            df_properties: Optional DataFrame of properties (for Wikidata)
            
        Returns:
            An appropriate property retriever instance
        """
        # Return cached instance if available
        if knowledge_source in self._retrievers:
            logger.info(f"Using cached property retriever for {knowledge_source}")
            return self._retrievers[knowledge_source]
            
        # Create a new instance based on the knowledge source
        logger.info(f"Creating new property retriever for {knowledge_source}")
        
        if knowledge_source == "wikidata":
            if df_properties is None:
                logger.error("DataFrame of properties is required for WikidataPropertyRetrieval")
                return None
                
            try:
                retriever = WikidataPropertyRetrieval(df_properties)
                self._retrievers[knowledge_source] = retriever
                return retriever
            except Exception as e:
                logger.error(f"Error creating WikidataPropertyRetrieval: {e}")
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
        
        # For curriculum, return UniversityPropertyRetrieval
        elif knowledge_source == "curriculum":
            try:
                retriever = UniversityPropertyRetrieval()
                self._retrievers[knowledge_source] = retriever
                return retriever
            except Exception as e:
                logger.error(f"Error creating UniversityPropertyRetrieval: {e}")
                return None
        
        # Default case - return None
        logger.warning(f"Unsupported knowledge source: {knowledge_source}")
        return None
        
    def close_all(self):
        """Close all retrievers"""
        for source, retriever in self._retrievers.items():
            if hasattr(retriever, 'close'):
                try:
                    retriever.close()
                    logger.info(f"Closed property retriever for {source}")
                except Exception as e:
                    logger.error(f"Error closing property retriever for {source}: {e}")

# Global factory instance
_property_retrieval_factory = None

def get_property_retrieval_factory():
    """Get the global property retrieval factory instance"""
    global _property_retrieval_factory
    if _property_retrieval_factory is None:
        _property_retrieval_factory = PropertyRetrievalFactory()
    return _property_retrieval_factory