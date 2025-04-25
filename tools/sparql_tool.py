import logging
from typing import Dict, Any, List
from SPARQLWrapper import SPARQLWrapper, JSON

# Setup logger
logger = logging.getLogger(__name__)

class WikidataSPARQLTool:
    """Tool for executing SPARQL queries against Wikidata."""
    
    def __init__(self):
        logger.info("Initializing WikidataSPARQLTool")
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
        logger.info(f"WikidataSPARQLTool: Executing SPARQL query with limit={limit}")
        logger.debug(f"WikidataSPARQLTool: Query to execute:\n{query}")
        
        try:
            # Convert limit to integer explicitly to avoid float notation
            limit_value = int(limit)
            
            # Add limit if not already present in the query
            if "LIMIT" not in query.upper():
                logger.info("WikidataSPARQLTool: Adding LIMIT clause to query")
                query += f" LIMIT {limit_value}"
            
            self._sparql.setQuery(query)
            logger.info("WikidataSPARQLTool: Sending query to Wikidata SPARQL endpoint")
            results = self._sparql.query().convert()
            logger.info("WikidataSPARQLTool: Query executed successfully")
            
            # Process results to make them more readable
            processed_results = []
            
            if "results" in results and "bindings" in results["results"]:
                bindings = results["results"]["bindings"]
                logger.info(f"WikidataSPARQLTool: Processing {len(bindings)} results")
                
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
                # Handle other types of results (e.g., ASK queries)
                logger.info("WikidataSPARQLTool: Query returned non-standard results structure")
                return {
                    "success": True,
                    "results": results,
                    "count": 1
                }
        
        except Exception as e:
            error_msg = str(e).split('\n')[0]
            logger.error(f"WikidataSPARQLTool: Query execution failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "query": query
            }
            
    def get_labels_for_uris(self, uris: List[str]) -> Dict[str, str]:
        """
        Get human-readable labels for Wikidata URIs
        
        Args:
            uris: List of Wikidata entity URIs
            
        Returns:
            Dictionary mapping URIs to their labels
        """
        if not uris:
            return {}
            
        logger.info(f"WikidataSPARQLTool: Getting labels for {len(uris)} URIs")
        
        # Limit the number of URIs to process to avoid overly large queries
        if len(uris) > 50:
            logger.warning(f"WikidataSPARQLTool: Limiting label lookup to 50 URIs (out of {len(uris)})")
            uris = uris[:50]
        
        # Extract entity IDs from URIs
        entity_ids = []
        for uri in uris:
            if uri.startswith("http://www.wikidata.org/entity/"):
                entity_id = uri.split("/")[-1]
                entity_ids.append(entity_id)
                
        if not entity_ids:
            logger.warning("WikidataSPARQLTool: No valid entity IDs extracted from URIs")
            return {}
            
        # Construct VALUES clause for SPARQL query
        values_str = " ".join([f"wd:{entity_id}" for entity_id in entity_ids])
        
        # Construct SPARQL query to get labels
        query = f"""
        SELECT ?entity ?label WHERE {{
          VALUES ?entity {{ {values_str} }}
          ?entity rdfs:label ?label .
          FILTER(LANG(?label) = "en")
        }}
        """
        
        try:
            logger.info("WikidataSPARQLTool: Executing label lookup query")
            self._sparql.setQuery(query)
            results = self._sparql.query().convert()
            
            # Process results into a dictionary
            uri_to_label = {}
            if "results" in results and "bindings" in results["results"]:
                bindings = results["results"]["bindings"]
                logger.info(f"WikidataSPARQLTool: Found labels for {len(bindings)} entities")
                
                for binding in bindings:
                    if "entity" in binding and "value" in binding["entity"]:
                        entity_uri = binding["entity"]["value"]
                        label = binding["label"]["value"] if "label" in binding and "value" in binding["label"] else "Unknown"
                        uri_to_label[entity_uri] = label
            
            return uri_to_label
            
        except Exception as e:
            logger.error(f"WikidataSPARQLTool: Error getting labels: {str(e)}")
            return {}