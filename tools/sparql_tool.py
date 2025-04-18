from typing import Optional, Dict, Any, ClassVar
from langchain_core.tools import BaseTool
from SPARQLWrapper import SPARQLWrapper, JSON

class ExecuteSPARQLTool(BaseTool):
    name: str = "execute_sparql"
    description: str = """Execute a SPARQL query against Wikidata.
    
    Args:
        query: The complete SPARQL query string to execute
        limit: Maximum number of results to return (default: 5)
    
    Returns:
        The query results or error information if the query fails
    """
    
    def __init__(self):
        super().__init__()
        # These are not Pydantic fields, just instance attributes
        self._endpoint = "https://query.wikidata.org/sparql"
        self._sparql = SPARQLWrapper(self._endpoint)
        self._sparql.setReturnFormat(JSON)
        # Set a user agent to be respectful to the Wikidata service
        self._sparql.addCustomHttpHeader("User-Agent", "LangChain Wikidata Agent/1.0")
        
    def _run(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Execute a SPARQL query against Wikidata
        
        Args:
            query: The SPARQL query string
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            The query results or error information
        """
        try:
            # Add limit if not already present in the query
            if "LIMIT" not in query.upper():
                if "}" in query:
                    query = query.replace("}", f" LIMIT {limit}" + " }")
                else:
                    query += f" LIMIT {limit}"
            
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
                "error": str(e),
                "query": query
            }