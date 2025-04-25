import requests
from typing import List, Dict, Any, Literal

class WikidataSearchTool:
    """Tool for searching entities or properties in Wikidata."""
    
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
        if type == "entity":
            return self._search_entity(term, limit)
        elif type == "property":
            return self._search_property(term, limit)
        else:
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
            
        return results
    
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
            
        return results