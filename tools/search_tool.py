# tools/search_tool.py
import logging
import requests
from typing import List, Dict, Any, Literal

# Setup logger
logger = logging.getLogger(__name__)

class WikidataSearchTool:
    """Tool for searching entities or properties in Wikidata."""
    
    def __init__(self):
        logger.info("Initializing WikidataSearchTool")
    
    def search(self, term: str, type: Literal["entity", "property"] = "entity", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for entities or properties in Wikidata
        
        Args:
            term: The search term
            type: Type of search ("entity" or "property")
            limit: Maximum number of results to return
            
        Returns:
            A list of matching entities or properties with their details
        """
        logger.info(f"WikidataSearchTool: Searching for {type} with term '{term}', limit={limit}")
        
        if type == "entity":
            return self._search_entity(term, limit)
        elif type == "property":
            return self._search_property(term, limit)
        else:
            logger.error(f"WikidataSearchTool: Invalid search type: {type}")
            raise ValueError(f"Invalid search type: {type}. Must be 'entity' or 'property'")
    
    def _search_entity(self, term: str, limit: int) -> List[Dict[str, Any]]:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "search": term,
            "limit": limit
        }
        
        logger.info(f"WikidataSearchTool: Calling Wikidata API to search for entity '{term}'")
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("search", []):
                result = {
                    "id": item.get("id"),
                    "label": item.get("label", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", "")
                }
                results.append(result)
            
            logger.info(f"WikidataSearchTool: Found {len(results)} entity results for '{term}'")
            if results:
                logger.debug(f"WikidataSearchTool: First result: {results[0]['label']} ({results[0]['id']})")
            
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WikidataSearchTool: Error searching for entity '{term}': {str(e)}")
            return []
    
    def _search_property(self, term: str, limit: int) -> List[Dict[str, Any]]:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "search": term,
            "type": "property",
            "limit": limit
        }
        
        logger.info(f"WikidataSearchTool: Calling Wikidata API to search for property '{term}'")
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("search", []):
                result = {
                    "id": item.get("id"),
                    "label": item.get("label", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", "")
                }
                results.append(result)
            
            logger.info(f"WikidataSearchTool: Found {len(results)} property results for '{term}'")
            if results:
                logger.debug(f"WikidataSearchTool: First result: {results[0]['label']} ({results[0]['id']})")
                
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"WikidataSearchTool: Error searching for property '{term}': {str(e)}")
            return []