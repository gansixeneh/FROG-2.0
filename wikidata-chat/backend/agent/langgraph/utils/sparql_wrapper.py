# backend/agent/langgraph/utils/sparql_wrapper.py
from SPARQLWrapper import SPARQLWrapper, JSON
import logging
from .knowledge_graph_metadata import get_knowledge_graph_metadata

# Configure logging
logger = logging.getLogger(__name__)

class SourceAwareSPARQLWrapper:
    """SPARQL wrapper that switches endpoints based on source using metadata"""
    
    def __init__(self, source="wikidata") -> None:
        self.source = source
        self.kg_metadata = get_knowledge_graph_metadata()
        self.sparql = self._create_sparql_wrapper()
        
    def _create_sparql_wrapper(self) -> SPARQLWrapper:
        """Create a SPARQLWrapper with the appropriate endpoint from metadata"""
        endpoint = self.kg_metadata.get_endpoint(self.source)
        user_agent = self.kg_metadata.get_user_agent(self.source)
        
        if not endpoint:
            # Fallback to default Wikidata endpoint
            endpoint = "https://query.wikidata.org/sparql"
            logger.warning(f"No endpoint found for source {self.source}, using default: {endpoint}")
        
        logger.info(f"Using SPARQL endpoint for {self.source}: {endpoint}")
            
        sparql = SPARQLWrapper(endpoint, agent=user_agent)
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
            logger.error(f"Error executing SPARQL query on {self.source}: {str(e):500}")
            logger.error(f"Query that failed: {q}")
            return [], e