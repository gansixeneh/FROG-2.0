import requests
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class WikidataUtils:
    """Utility functions for working with Wikidata."""
    
    def __init__(self):
        self.wikidata_api_url = "https://www.wikidata.org/w/api.php"
        self.entity_url_prefix = "http://www.wikidata.org/entity/"
    
    def get_entity_details(self, entity_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific entity.
        
        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID (Q number)
            
        Returns:
        --------
        dict
            Entity details
        """
        try:
            params = {
                'action': 'wbgetentities',
                'ids': entity_id,
                'languages': 'en',
                'format': 'json'
            }
            
            response = requests.get(self.wikidata_api_url, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting entity details: {e}")
            return {}
    
    def extract_entity_id(self, uri: str) -> str:
        """
        Extract entity ID from a Wikidata URI.
        
        Parameters:
        -----------
        uri : str
            Wikidata URI
            
        Returns:
        --------
        str
            Entity ID (Q number or P number)
        """
        if self.entity_url_prefix in uri:
            return uri.split(self.entity_url_prefix)[-1]
        return uri
    
    def format_sparql_prefixes(self) -> str:
        """
        Return common SPARQL prefixes for Wikidata queries.
        
        Returns:
        --------
        str
            Formatted SPARQL prefixes
        """
        return """
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wikibase: <http://wikiba.se/ontology#>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX ps: <http://www.wikidata.org/prop/statement/>
        PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX bd: <http://www.bigdata.com/rdf#>
        """
    
    def prepare_entity_label(self, entity: Dict[str, Any]) -> str:
        """
        Format entity information for display.
        
        Parameters:
        -----------
        entity : Dict[str, Any]
            Entity information
            
        Returns:
        --------
        str
            Formatted entity label with description if available
        """
        label = entity.get("label", entity.get("entity_id", "Unknown entity"))
        description = entity.get("description", "")
        
        if description:
            return f"{label} ({description})"
        return label
    
    def validate_entity_id(self, entity_id: str) -> bool:
        """
        Validate if a string is a proper Wikidata entity ID.
        
        Parameters:
        -----------
        entity_id : str
            Entity ID to validate
            
        Returns:
        --------
        bool
            True if valid, False otherwise
        """
        if not entity_id:
            return False
        
        # Q entities (items) or P entities (properties)
        return (entity_id.startswith('Q') or entity_id.startswith('P')) and entity_id[1:].isdigit()
    
    def get_label_and_description(self, entity_id: str) -> Tuple[str, str]:
        """
        Get the English label and description for an entity.
        
        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID
            
        Returns:
        --------
        Tuple[str, str]
            (label, description) for the entity
        """
        entity_data = self.get_entity_details(entity_id)
        
        label = "Unknown"
        description = ""
        
        if entity_data and "entities" in entity_data and entity_id in entity_data["entities"]:
            entity = entity_data["entities"][entity_id]
            
            if "labels" in entity and "en" in entity["labels"]:
                label = entity["labels"]["en"]["value"]
                
            if "descriptions" in entity and "en" in entity["descriptions"]:
                description = entity["descriptions"]["en"]["value"]
                
        return label, description