# First, let's update graph.py to set up the base logging configuration

# graph.py changes - Add at the top of the file after imports
import os
import logging
from typing import Dict, Any, TypedDict, Annotated, Literal
from dotenv import load_dotenv

import langgraph.graph as lg
from langgraph.graph import StateGraph, END

from nodes.entity_extraction import EntityExtractor
from nodes.query_generator import QueryGenerator
from nodes.query_checker import QueryChecker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# State definition
class WikidataQueryState(TypedDict):
    question: str
    entities: list
    properties: list
    generated_query: str
    query_results: list
    result_count: int
    query_success: bool
    feedback: str
    decision: Literal["satisfied", "regenerate"]
    final_query: str

def create_wikidata_graph(api_key: str = None):
    """
    Create the Wikidata query graph
    
    Args:
        api_key: Google Gemini API key
        
    Returns:
        Configured graph for Wikidata querying
    """
    # Load environment variables
    load_dotenv()
    
    logger.info("Creating Wikidata query graph")
    
    # Get API key
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("No Gemini API key provided or found in environment")
            raise ValueError("Gemini API key must be provided or set as GEMINI_API_KEY environment variable")
    
    # Initialize nodes
    logger.info("Initializing graph nodes")
    entity_extractor = EntityExtractor(api_key)
    query_generator = QueryGenerator(api_key)
    query_checker = QueryChecker(api_key)
    
    # Define state graph
    graph = StateGraph(WikidataQueryState)
    
    # Define nodes
    graph.add_node("extract_entities", entity_extractor)
    graph.add_node("generate_query", query_generator)
    graph.add_node("check_query", query_checker)
    
    # Define edges
    graph.add_edge("extract_entities", "generate_query")
    graph.add_edge("generate_query", "check_query")
    
    # Define conditional edges for the checker
    graph.add_conditional_edges(
        "check_query",
        query_checker.decide_next_step,
        {
            "continue": END,
            "regenerate": "generate_query"
        }
    )
    
    # Define the entry point
    graph.set_entry_point("extract_entities")
    
    logger.info("Graph creation complete")
    
    # Compile the graph
    return graph.compile()

class WikidataQueryAgent:
    """Agent for answering questions by querying Wikidata using SPARQL."""
    
    def __init__(self, api_key: str = None):
        logger.info("Initializing WikidataQueryAgent")
        self.graph = create_wikidata_graph(api_key)
    
    def query(self, question: str) -> Dict[str, Any]:
        """
        Process a question and generate a SPARQL query
        
        Args:
            question: The natural language question
            
        Returns:
            Dictionary with the query, results, and other information
        """
        logger.info(f"Processing question: {question}")
        
        # Initialize state
        state = {
            "question": question,
            "entities": [],
            "properties": [],
            "generated_query": "",
            "query_results": [],
            "result_count": 0,
            "query_success": False,
            "feedback": "",
            "decision": "regenerate"
        }
        
        # Run the graph
        logger.info("Invoking LangGraph execution")
        result = self.graph.invoke(state)
        
        logger.info(f"Graph execution complete. Query success: {result.get('query_success', False)}")
        
        # Prepare the final result
        final_result = {
            "question": question,
            "sparql_query": result.get("generated_query", ""),
            "results": result.get("query_results", []),
            "result_count": result.get("result_count", 0),
            "success": result.get("query_success", False)
        }
        
        return final_result