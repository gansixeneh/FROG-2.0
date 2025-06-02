# backend/agent/langgraph/agent.py
import os
import json
import tempfile
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

# Import helper modules
from SPARQLWrapper import SPARQLWrapper, JSON
import requests
from googletrans import Translator
import re
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

# Import LLM factory
from ..llm_factory import LLMFactory

# Import visualization classes
from .utils.visualization import BoxologyVisualizer
from .utils.property_retrieval import WikidataPropertyRetrieval
from .utils.state import WikidataGraphRAGState
from .utils.date_utils import format_reference_date
from .nodes import (
    TranslationNode,
    EntityExtractionNode,
    StrategySelectionNode,
    VerbalizationNode,
    PropertyGenerationNode,
    SparqlGenerationNode,
    AnswerGenerationNode,
    GoogleSearchNode,
)

# Configure logging
logger = logging.getLogger(__name__)


# WikidataAPI helper class
class WikidataAPI:
    def __init__(self, url="https://query.wikidata.org/sparql", source="wikidata") -> None:
        self.source = source
        self.wikidata_url = "https://query.wikidata.org/sparql"
        self.curriculum_url = "http://localhost:3030/curi/query"
        self.current_url = self.wikidata_url if source == "wikidata" else self.curriculum_url
        self.sparqlwd = SPARQLWrapper(
            self.current_url,
            agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.36",
        )

    def set_source(self, source: str) -> None:
        """Update the source and endpoint URL"""
        if source != self.source:
            self.source = source
            self.current_url = self.wikidata_url if source == "wikidata" else self.curriculum_url
            self.sparqlwd = SPARQLWrapper(
                self.current_url,
                agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.36",
            )

    def execute_sparql(self, q: str) -> tuple:
        """Execute a SPARQL query"""
        self.sparqlwd.setQuery(q)
        self.sparqlwd.setReturnFormat(JSON)
        try:
            results = self.sparqlwd.query().convert()
            results_cleaned = []
            for result in results["results"]["bindings"]:
                tmp = dict()
                for header in results["head"]["vars"]:
                    if header in result:
                        tmp[header] = result[header]["value"]
                results_cleaned.append(tmp)
            return results_cleaned, None
        except Exception as e:
            return [], e

    def get_entities(self, entity: str, k: int = 5, lang: str = "en") -> tuple:
        wikidata_api = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "search": entity,
            "language": lang,
        }
        try:
            data = requests.get(wikidata_api, params=params)
        except Exception as e:
            return [], e

        json_data = data.json()
        parsed_data = [
            {
                "uri": item["id"],
                "label": item["label"],
                "description": item.get("description", ""),
            }
            for item in json_data["search"][:k]
        ]
        return parsed_data, None


# Main agent class
class WikidataGraphAgent:
    """Agent that uses LangGraph for Wikidata question answering"""

    def __init__(
        self,
        gemini_api_key=None,
        print_output=False,
        debug_callback=None,
    ):
        # Set API key
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError(
                "Gemini API key must be provided or set as GEMINI_API_KEY environment variable"
            )

        # Store configuration
        self.print_output = print_output
        self.debug_callback = debug_callback
        self.visualizer = (
            None  # Will be set when running a query with boxology_verbose > 0
        )

        # Initialize LLM Factory
        try:
            self.llm_factory = LLMFactory()
            logger.info("Initialized LLM Factory with configuration")
        except Exception as e:
            logger.error(f"Failed to initialize LLM Factory: {e}")
            logger.info("Creating LLM Factory with default Gemini configuration")
            # Create a minimal default config for Gemini
            import tempfile
            import json
            default_config = {
                "default": {
                    "provider": "gemini",
                    "model": "gemini-2.0-flash",
                    "config": {"temperature": 0.2}
                },
                "nodes": {},
                "providers": {
                    "gemini": {
                        "default_config": {"temperature": 0.2}
                    }
                }
            }
            # Write to temp file and initialize factory
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(default_config, f)
                temp_config_path = f.name
            
            self.llm_factory = LLMFactory(config_path=temp_config_path)

        # Initialize Wikidata API
        self.api = WikidataAPI()

        # Initialize source-aware SPARQL wrapper
        from .utils.sparql_wrapper import SourceAwareSPARQLWrapper
        self.sparql_wrapper = SourceAwareSPARQLWrapper(source="wikidata")

        # Initialize entity retrieval for curriculum
        from .utils.entity_retrieval import UniversityEntityRetrieval
        try:
            self.entity_retrieval = UniversityEntityRetrieval()
            logger.info("Successfully initialized UniversityEntityRetrieval")
        except Exception as e:
            logger.error(f"Failed to initialize UniversityEntityRetrieval: {e}")
            self.entity_retrieval = None

        # Load properties data
        try:
            df_properties = pd.read_csv("./data/wikidata_ontology/properties.csv")
        except FileNotFoundError:
            # Create minimal example for testing if file doesn't exist
            df_properties = pd.DataFrame(
                {
                    "propertyId": ["P31", "P279", "P17", "P131"],
                    "label": ["instance of", "subclass of", "country", "located in"],
                    "description": [
                        "that class of which this subject is a particular example",
                        "the subject is a subclass of a class",
                        "sovereign state of this item",
                        "the item is located on the territory of the following administrative entity",
                    ],
                }
            )

        # Initialize property retrieval
        self.property_retrieval = WikidataPropertyRetrieval(df_properties)

        # Build the graph
        self.build_graph()

        # Visualization files
        self.visualization_files = {}

    def build_graph(self):
        """Build the LangGraph workflow"""
        # Create nodes with LLM factory
        translation_node = TranslationNode()
        entity_extraction_node = EntityExtractionNode(llm_factory=self.llm_factory)
        verbalization_node = VerbalizationNode(llm_factory=self.llm_factory, property_retrieval=self.property_retrieval)
        sparql_generation_node = SparqlGenerationNode(
            llm_factory=self.llm_factory, 
            property_retrieval=self.property_retrieval
        )
        answer_generation_node = AnswerGenerationNode(llm_factory=self.llm_factory)
        
        strategy_selection_node = StrategySelectionNode()
        property_generation_node = PropertyGenerationNode(self.property_retrieval)
        google_search_node = GoogleSearchNode()

        # Create the graph
        workflow = StateGraph(WikidataGraphRAGState)

        # Add nodes
        workflow.add_node("translation", translation_node)
        workflow.add_node("entity_extraction", entity_extraction_node)
        workflow.add_node("strategy_selection", strategy_selection_node)
        workflow.add_node("verbalization", verbalization_node)
        workflow.add_node("property_generation", property_generation_node)
        workflow.add_node("sparql_generation", sparql_generation_node)
        workflow.add_node("answer_generation", answer_generation_node)
        workflow.add_node("google_search", google_search_node)

        # Define the flow
        workflow.set_entry_point("translation")
        workflow.add_edge("translation", "entity_extraction")
        workflow.add_edge("entity_extraction", "strategy_selection")

        # Use attribute access instead of dictionary subscription
        workflow.add_conditional_edges(
            "strategy_selection",
            lambda x: x.next,
            {
                "verbalization": "verbalization",
                "sparql_generation": "property_generation",  # Entity extraction provides initial properties, property_generation enhances them
            },
        )
        workflow.add_edge("property_generation", "sparql_generation")

        # Use attribute access instead of dictionary subscription
        workflow.add_conditional_edges(
            "verbalization",
            lambda x: x.next,
            {
                "answer_generation": "answer_generation",
                "sparql_generation": "property_generation",
            },
        )
        
        # SPARQL can either succeed and go to answer generation, or fail and go to Google search (if enabled)
        workflow.add_conditional_edges(
            "sparql_generation",
            lambda x: (
                "answer_generation" if x.approach_used == "sparql" 
                else ("google_search" if getattr(x, 'use_google_search', True) else "answer_generation")
            ),
            {
                "answer_generation": "answer_generation",
                "google_search": "google_search",
            },
        )
        
        # Google search always goes to answer generation
        workflow.add_edge("google_search", "answer_generation")
        workflow.add_edge("answer_generation", END)

        # Compile the graph
        self.graph = workflow.compile()

    def create_explanation(self, state):
        """Create a detailed explanation of the process and results"""
        approach = state.approach_used if state.approach_used else "Unknown"
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        source_name = "curriculum knowledge base" if knowledge_source == "curriculum" else "Wikidata"

        # Start with a header and the original question
        explanation = f"""## Question Answering Process
**Question:** {state.question}
**Knowledge Source:** {source_name}

"""

        # Add information about the extracted entities
        if state.extracted_entities:
            explanation += f"""### Extracted Entities
{", ".join(state.extracted_entities)}

"""

        # Add approach information
        if approach == "verbalization":
            # Get entity label if available
            entity_uri = state.entity_uri if state.entity_uri else None
            entity_label = entity_uri

            if entity_uri:
                try:
                    label_query = f"""
                    SELECT ?label WHERE {{
                      wd:{entity_uri} rdfs:label ?label .
                      FILTER(LANG(?label) = "en")
                    }}
                    """
                    label_results, _ = self.api.execute_sparql(label_query)
                    if label_results and "label" in label_results[0]:
                        entity_label = f"{label_results[0]['label']} ({entity_uri})"
                except:
                    pass

            explanation += f"""### Approach: Direct Verbalization
Using entity: {entity_label}

"""
            # Add verbalization results
            if state.verbalization_result:
                explanation += "#### Entity Information\n"
                for item in state.verbalization_result[:5]:  # Limit to first 5 results
                    for k, v in item.items():
                        explanation += f"- {k}: {v}\n"

                if len(state.verbalization_result) > 5:
                    explanation += f"...and {len(state.verbalization_result) - 5} more properties\n"

                similarity = 0
                if state.verbalization_similarity:
                    similarity = state.verbalization_similarity
                explanation += f"\n**Similarity Score**: {similarity:.2f}\n\n"

            # Add reference information if available
            if hasattr(state, 'verbalization_references') and state.verbalization_references:
                explanation += "#### Reference Sources\n"
                unique_urls = set()
                formatted_dates = set()
                
                for ref in state.verbalization_references:
                    if ref.get('refUrl'):
                        unique_urls.add(ref['refUrl'])
                    if ref.get('refDate'):
                        formatted_date = format_reference_date(ref['refDate'])
                        formatted_dates.add(formatted_date)
                
                if unique_urls:
                    explanation += "**Sources:**\n"
                    for url in unique_urls:
                        explanation += f"- {url}\n"
                
                if formatted_dates:
                    explanation += "\n**Retrieved on:**\n"
                    for date in formatted_dates:
                        explanation += f"- {date}\n"
                
                explanation += f"\n**Total references found**: {len(state.verbalization_references)}\n\n"

        elif approach == "sparql":
            # Add property information if available
            if state.related_properties:
                explanation += f"""### Related Properties
{", ".join(state.related_properties[:10])}

"""

            # Add SPARQL query if available
            if state.sparql_query:
                explanation += f"""### SPARQL Query
```sparql
{state.sparql_query}
```

"""

                # Extract entity and property IDs from the query
                entity_ids = []
                property_ids = []

                # Extract entity IDs (Q numbers)
                entity_matches = re.findall(r"wd:Q(\d+)", state.sparql_query)
                if entity_matches:
                    entity_ids = [f"Q{id}" for id in entity_matches]

                # Extract property IDs (P numbers)
                property_matches = re.findall(r"wdt:P(\d+)", state.sparql_query)
                if property_matches:
                    property_ids = [f"P{id}" for id in property_matches]

                if entity_ids or property_ids:
                    explanation += "#### Entities and Properties Used\n"

                    # Get entity labels
                    if entity_ids:
                        entity_labels = {}

                        # Build a query to get entity labels
                        if len(entity_ids) > 0:
                            values_str = " ".join([f"wd:{eid}" for eid in entity_ids])
                            label_query = f"""
                            SELECT ?item ?itemLabel WHERE {{
                              VALUES ?item {{ {values_str} }}
                              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
                            }}
                            """

                            try:
                                label_results, _ = self.api.execute_sparql(label_query)
                                for result in label_results:
                                    if "item" in result and "itemLabel" in result:
                                        item_id = result["item"].split("/")[-1]
                                        entity_labels[item_id] = result["itemLabel"]
                            except Exception as e:
                                print(f"Error getting entity labels: {e}")

                        explanation += "**Entities:**\n"
                        for entity_id in entity_ids:
                            label = entity_labels.get(entity_id, entity_id)
                            explanation += f"- {entity_id}: {label}\n"

                    # Get property labels
                    if property_ids:
                        property_labels = {}

                        # Look up property labels in the properties dataframe
                        for prop_id in property_ids:
                            prop_row = self.property_retrieval.df_properties[
                                self.property_retrieval.df_properties["propertyId"]
                                == prop_id
                            ]
                            if not prop_row.empty:
                                property_labels[prop_id] = prop_row.iloc[0]["label"]
                            else:
                                property_labels[prop_id] = prop_id

                        explanation += "\n**Properties:**\n"
                        for prop_id in property_ids:
                            label = property_labels.get(prop_id, prop_id)
                            explanation += f"- {prop_id}: {label}\n"

                    explanation += "\n"

            # Add reference information for SPARQL if available
            if hasattr(state, 'sparql_references') and state.sparql_references:
                explanation += "#### Reference Sources\n"
                unique_urls = set()
                formatted_dates = set()
                
                for ref in state.sparql_references:
                    if ref.get('refUrl'):
                        unique_urls.add(ref['refUrl'])
                    if ref.get('formattedRefDate'):
                        formatted_dates.add(ref['formattedRefDate'])
                    elif ref.get('refDate'):
                        formatted_date = format_reference_date(ref['refDate'])
                        formatted_dates.add(formatted_date)
                
                if unique_urls:
                    explanation += "**Sources:**\n"
                    for url in unique_urls:
                        explanation += f"- {url}\n"
                
                if formatted_dates:
                    explanation += "\n**Retrieved on:**\n"
                    for date in formatted_dates:
                        explanation += f"- {date}\n"
                
                explanation += f"\n**Total references found**: {len(state.sparql_references)}\n\n"

        elif approach == "google_search":
            explanation += f"""### Approach: Google Web Search
{source_name} methods did not provide sufficient results, so web search was used as a fallback.

"""
            if state.google_search_result:
                if state.google_search_result.get("content"):
                    explanation += "#### Search Result\n"
                    explanation += state.google_search_result["content"][:500]
                    if len(state.google_search_result["content"]) > 500:
                        explanation += "..."
                    explanation += "\n\n"
                    
                if state.google_search_result.get("citations"):
                    explanation += "#### Sources\n"
                    for citation in state.google_search_result["citations"]:
                        explanation += f"- [{citation.get('title', 'Unknown')}]({citation.get('url', '')})\n"
                    explanation += "\n"

        # Add query results if available
        if state.query_result and approach not in ["sparql_failed", "google_search"]:
            explanation += "### Query Results\n"

            # Format the query results as a markdown table
            if state.query_result:
                # Get column headers
                headers = list(state.query_result[0].keys())

                # Create table header
                explanation += "| " + " | ".join(headers) + " |\n"
                explanation += "| " + " | ".join(["---"] * len(headers)) + " |\n"

                # Add rows (limit to 10 rows for readability)
                max_rows = min(10, len(state.query_result))
                for row in state.query_result[:max_rows]:
                    explanation += (
                        "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n"
                    )

                if len(state.query_result) > 10:
                    explanation += (
                        f"\n*...and {len(state.query_result) - 10} more rows*\n"
                    )
            else:
                explanation += "*No results found*\n"

            explanation += "\n"

        # Add the final answer
        explanation += f"""### Final Answer
{state.final_answer}
"""

        return explanation

    def query(self, question, verbose=0, boxology_verbose=0, settings=None):
        """Process a question and return answer, explanation, and visualization data

        Args:
            question: The question to process
            verbose: Level of verbosity for process logging (0-2)
            boxology_verbose: Level of verbosity for boxology visualization (0-2)
            settings: Runtime settings dict with useVerbalization and useGoogleSearch flags

        Returns:
            Tuple of (final_answer, explanation, visualization_data)
        """
        # Initialize visualizer if boxology_verbose > 0
        visualizer = None
        if boxology_verbose > 0:
            visualizer = BoxologyVisualizer(
                boxology_verbose, debug_callback=self.debug_callback
            )
            visualizer.set_question(question)
            # Save reference to visualizer for debug callback updates
            self.visualizer = visualizer

        # Initialize the state
        settings = settings or {}
        knowledge_source = settings.get('knowledgeSource', 'wikidata')
        
        # Update SPARQL endpoints based on source
        if hasattr(self.api, 'set_source'):
            self.api.set_source(knowledge_source)
        if hasattr(self.sparql_wrapper, 'set_source'):
            self.sparql_wrapper.set_source(knowledge_source)
            
        initial_state = WikidataGraphRAGState(
            question=question,
            use_cot=True,
            verbose=verbose,
            try_threshold=5,
            visualizer=visualizer,
            boxology_verbose=boxology_verbose,
            debug_callback=self.debug_callback,
            include_references=True,  # Enable references by default
            use_verbalization=settings.get('useVerbalization', True),  # Default to True
            use_google_search=settings.get('useGoogleSearch', True),   # Default to True
            knowledge_source=knowledge_source,  # Set the knowledge source
        )

        # Run the graph
        final_state_dict = self.graph.invoke(initial_state)

        # Convert the AddableValuesDict back to our state type
        final_state = WikidataGraphRAGState(**dict(final_state_dict))

        # Pass the approach information to the visualizer
        if boxology_verbose > 0 and visualizer and final_state.approach_used:
            visualizer.set_approach_used(final_state.approach_used)
            logger.info(f"Set approach in visualizer: {final_state.approach_used}")

        # Generate explanation
        explanation = self.create_explanation(final_state)

        # Generate visualization files if requested
        visualization_data = None
        if boxology_verbose > 0 and visualizer:
            visualization_data = visualizer.save_visualization_files()
            # Store visualization files for later access
            self.visualization_files = visualization_data

        return final_state.final_answer, explanation, visualization_data