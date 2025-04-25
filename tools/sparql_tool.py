from typing import Dict, Any
from SPARQLWrapper import SPARQLWrapper, JSON

class WikidataSPARQLTool:
    """Tool for executing SPARQL queries against Wikidata."""
    
    def __init__(self):
        self._endpoint = "https://query.wikidata.org/sparql"
        self._sparql = SPARQLWrapper(self._endpoint)
        self._sparql.setReturnFormat(JSON)
        # Set a user agent to be respectful to the Wikidata service
        self._sparql.addCustomHttpHeader("User-Agent", "LangGraph Wikidata Agent/1.0")
        
    def execute(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Execute a SPARQL query against Wikidata
        
        Args:
            query: The SPARQL query string
            limit: Maximum number of results to return
            
        Returns:
            The query results or error information
        """
        try:
            # Convert limit to integer explicitly to avoid float notation
            limit_value = int(limit)
            
            # Add limit if not already present in the query
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit_value}"
            
            self._sparql.setQuery(query)
            results = self._sparql.query().convert()
            
            # Process results to make them more readable
            processed_results = []
            
            if "results" in results and "bindings" in results["results"]:
                bindings = results["results"]["bindings"]
                
                for binding in bindings:
                    processed_binding = {}
                    for key, value in binding.items():
                        processed_binding[key] = value.get("value", "")
                    processed_results.append(processed_binding)
                
                return {
                    "success": True,
                    "results": processed_results,
                    "count": len(processed_results),
                    "raw_results": bindings  # Include raw results for reference
                }
            else:
                # Handle other types of results
                return {
                    "success": True,
                    "results": results,
                    "count": 1
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e).split('\n')[0],
                "query": query
            }

    def get_labels_for_uris(self, uris: list[str]) -> Dict[str, str]:
        """
        Get labels for a list of Wikidata URIs
        
        Args:
            uris: List of Wikidata URIs
            
        Returns:
            Dictionary mapping URIs to their labels
        """
        if not uris:
            return {}
            
        # Extract entity IDs from URIs
        entity_ids = []
        for uri in uris:
            if uri.startswith("http://www.wikidata.org/entity/"):
                entity_id = uri.split("/")[-1]
                entity_ids.append(entity_id)
        
        if not entity_ids:
            return {}
            
        # Create a SPARQL query to get labels
        entities_values = " ".join([f"wd:{entity_id}" for entity_id in entity_ids])
        query = f"""
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?uri ?label WHERE {{
            VALUES ?uri {{ {entities_values} }}
            ?uri rdfs:label ?label .
            FILTER(LANG(?label) = "en")
        }}
        """
        
        result = self.execute(query, limit=len(entity_ids) * 2)
        
        # Process results
        uri_to_label = {}
        if result.get("success", False):
            for item in result.get("results", []):
                if "uri" in item and "label" in item:
                    uri = item["uri"]
                    label = item["label"]
                    uri_to_label[uri] = label
        
        return uri_to_label