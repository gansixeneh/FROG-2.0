# backend/agent/langgraph/utils/sparql_wrapper.py
from SPARQLWrapper import SPARQLWrapper, JSON
import logging

# Configure logging
logger = logging.getLogger(__name__)

class SourceAwareSPARQLWrapper:
    """SPARQL wrapper that switches endpoints based on source"""
    
    WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
    CURRICULUM_ENDPOINT = "http://localhost:3030/curi/query"
    
    def __init__(self, source="wikidata") -> None:
        self.source = source
        self.sparql = self._create_sparql_wrapper()
        
    def _create_sparql_wrapper(self) -> SPARQLWrapper:
        """Create a SPARQLWrapper with the appropriate endpoint"""
        if self.source == "curriculum":
            endpoint = self.CURRICULUM_ENDPOINT
            logger.info(f"Using Curriculum SPARQL endpoint: {endpoint}")
        else:
            endpoint = self.WIKIDATA_ENDPOINT
            logger.info(f"Using Wikidata SPARQL endpoint: {endpoint}")
            
        sparql = SPARQLWrapper(
            endpoint,
            agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.36",
        )
        sparql.setReturnFormat(JSON)
        return sparql
    
    def set_source(self, source: str) -> None:
        """Set the source and update the SPARQL wrapper"""
        if source != self.source:
            self.source = source
            self.sparql = self._create_sparql_wrapper()
    
    def execute_sparql(self, q: str) -> tuple:
        """Execute a SPARQL query"""
        self.sparql.setQuery(q)
        try:
            results = self.sparql.query().convert()
            results_cleaned = []
            for result in results["results"]["bindings"]:
                tmp = dict()
                for header in results["head"]["vars"]:
                    if header in result:
                        tmp[header] = result[header]["value"]
                results_cleaned.append(tmp)
            return results_cleaned, None
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            return [], e