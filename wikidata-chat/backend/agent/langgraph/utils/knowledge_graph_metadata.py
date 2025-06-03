# backend/agent/langgraph/utils/knowledge_graph_metadata.py
import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class KnowledgeGraphMetadata:
    """
    Manager class for knowledge graph metadata including endpoints, prefixes, 
    templates, and other configuration data.
    """
    
    def __init__(self, metadata_path: str = None):
        """
        Initialize the metadata manager
        
        Args:
            metadata_path: Path to the metadata JSON file
        """
        if metadata_path is None:
            # Default path relative to the backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            metadata_path = os.path.join(backend_dir, "config", "knowledge_graph_metadata.json")
        
        self.metadata_path = metadata_path
        self._metadata_cache = None
        self.load_metadata()
    
    def load_metadata(self) -> None:
        """Load metadata from the JSON file"""
        try:
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self._metadata_cache = json.load(f)
            logger.info(f"Loaded knowledge graph metadata from {self.metadata_path}")
        except Exception as e:
            logger.error(f"Failed to load knowledge graph metadata: {e}")
            # Fallback to minimal default metadata
            self._metadata_cache = {
                "wikidata": {
                    "name": "Wikidata",
                    "description": "Wikidata knowledge graph",
                    "endpoint": "https://query.wikidata.org/sparql",
                    "prefixes": {"wd": "http://www.wikidata.org/entity/", "wdt": "http://www.wikidata.org/prop/direct/"},
                    "sparql_instructions": ["Use PREFIX NOTATION ONLY (e.g., wd:Q123, wdt:P123), NOT full URIs"],
                    "supports_references": True
                }
            }    
    def get_metadata(self, knowledge_source: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific knowledge source
        
        Args:
            knowledge_source: The knowledge source identifier (e.g., 'wikidata', 'curriculum')
            
        Returns:
            Dictionary containing metadata for the knowledge source, or None if not found
        """
        if self._metadata_cache is None:
            self.load_metadata()
        
        return self._metadata_cache.get(knowledge_source)
    
    def get_endpoint(self, knowledge_source: str) -> str:
        """Get SPARQL endpoint for a knowledge source"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("endpoint", "")
        return ""
    
    def get_prefixes(self, knowledge_source: str) -> Dict[str, str]:
        """Get namespace prefixes for a knowledge source"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("prefixes", {})
        return {}
    
    def get_prefixes_declaration(self, knowledge_source: str) -> str:
        """Get formatted PREFIX declarations for SPARQL queries"""
        prefixes = self.get_prefixes(knowledge_source)
        declarations = []
        for prefix, uri in prefixes.items():
            declarations.append(f"PREFIX {prefix}: <{uri}>")
        return "\n".join(declarations)    
    def get_name(self, knowledge_source: str) -> str:
        """Get display name for a knowledge source"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("name", knowledge_source)
        return knowledge_source
    
    def get_description(self, knowledge_source: str) -> str:
        """Get description for a knowledge source"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("description", knowledge_source)
        return knowledge_source
    
    def get_sparql_instructions(self, knowledge_source: str) -> list:
        """Get SPARQL generation instructions for a knowledge source"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("sparql_instructions", [])
        return []
    
    def get_verbalization_template(self, knowledge_source: str, template_type: str) -> str:
        """Get verbalization template (po_template or sp_template)"""
        metadata = self.get_metadata(knowledge_source)
        if metadata and "verbalization_templates" in metadata:
            return metadata["verbalization_templates"].get(template_type, "")
        return ""
    
    def get_user_agent(self, knowledge_source: str) -> str:
        """Get user agent string for SPARQL requests"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("user_agent", "FROG Wikidata Agent/1.0")
        return "FROG Wikidata Agent/1.0"
    
    def supports_references(self, knowledge_source: str) -> bool:
        """Check if knowledge source supports reference information"""
        metadata = self.get_metadata(knowledge_source)
        if metadata:
            return metadata.get("supports_references", False)
        return False
    
    def get_available_sources(self) -> list:
        """Get list of available knowledge sources"""
        if self._metadata_cache is None:
            self.load_metadata()
        return list(self._metadata_cache.keys())

# Global metadata manager instance
_metadata_manager = None

def get_knowledge_graph_metadata() -> KnowledgeGraphMetadata:
    """Get the global knowledge graph metadata manager instance"""
    global _metadata_manager
    if _metadata_manager is None:
        _metadata_manager = KnowledgeGraphMetadata()
    return _metadata_manager
