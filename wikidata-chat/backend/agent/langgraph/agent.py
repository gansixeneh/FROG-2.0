import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple

# Google Generative AI imports
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

# LangGraph imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

# Import tools
from agent.tools.search_tool import SearchWikidataTool
from agent.tools.sparql_tool import ExecuteSPARQLTool
from agent.tools.google_search_tool import GoogleSearchTool

# Import helper modules
from SPARQLWrapper import SPARQLWrapper, JSON
import requests
from googletrans import Translator
import re
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import mermaid

# Custom visualization module
class BoxologyVisualizer:
    """Simplified visualizer for displaying process flow of WikidataGraphRAG"""
    def __init__(self, verbose=1):
        self.logs = []
        self.verbose = verbose
        self.start_time = datetime.now()
        self.question = None
        
    def set_question(self, question):
        """Set the question for this visualization session"""
        self.question = question
    
    def log_event(self, component, event_type, details=None, start_time=None, end_time=None):
        """Log a process event with timestamp"""
        if self.verbose < 1:
            return
            
        timestamp = datetime.now()
        self.logs.append({
            "component": component,
            "event_type": event_type,
            "details": details,
            "timestamp": timestamp.isoformat(),
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        })
    
    def _get_filename_base(self):
        """Generate the base filename from datetime and question"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Clean the question for filename
        if self.question:
            # Remove special characters and truncate
            clean_question = re.sub(r'[^\w\s-]', '', self.question).strip()
            clean_question = re.sub(r'[-\s]+', '_', clean_question)[:50]
            return f"{timestamp}_{clean_question}"
        else:
            return f"{timestamp}_unknown_question"
    
    def save_logs_to_json(self):
        """Save logs to a JSON file with datetime and question in filename"""
        if not self.logs:
            return None
        
        # Create filename
        filename_base = self._get_filename_base()
        temp_dir = tempfile.gettempdir()
        filename = f"{temp_dir}/{filename_base}.json"
        
        # Prepare data for saving
        log_data = {
            "question": self.question,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "total_duration": (datetime.now() - self.start_time).total_seconds(),
            "logs": self.logs
        }
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def save_mermaid_diagram(self):
        """Generate and save the mermaid diagram to a file"""
        if not self.logs:
            return None
            
        # Create filename
        filename_base = self._get_filename_base()
        temp_dir = tempfile.gettempdir()
        filename = f"{temp_dir}/{filename_base}.mmd"
        
        # Generate mermaid code
        mermaid_code = ["graph TD;"]
        mermaid_code.append("    title[\"WikidataGraphRAG Process Flow\"]")
        
        # Group logs by component
        components = {}
        for log in self.logs:
            comp = log["component"]
            if comp not in components:
                components[comp] = []
            components[comp].append(log)
        
        # Add nodes for each component
        for i, (comp_name, events) in enumerate(components.items()):
            node_id = f"node_{i}"
            mermaid_code.append(f"    {node_id}[\"{comp_name}\"]")
            
            # Add event nodes
            for j, event in enumerate(events):
                event_id = f"{node_id}_event_{j}"
                event_text = event["event_type"]
                mermaid_code.append(f"    {event_id}[\"{event_text}\"]")
                
                # Connect to component
                mermaid_code.append(f"    {node_id} --> {event_id}")
                
                # Add details if available
                if event["details"]:
                    detail_id = f"{event_id}_details"
                    
                    # Format details
                    if isinstance(event["details"], dict):
                        detail_text = ", ".join(f"{k}: {v}" for k, v in event["details"].items())
                    elif isinstance(event["details"], list):
                        detail_text = ", ".join(str(item) for item in event["details"])
                    else:
                        detail_text = str(event["details"])
                    
                    mermaid_code.append(f"    {detail_id}[\"{detail_text}\"]")
                    mermaid_code.append(f"    {event_id} --> {detail_id}")
            
            # Connect components in sequence
            if i > 0:
                prev_node = f"node_{i-1}"
                mermaid_code.append(f"    {prev_node} --> {node_id}")
        
        # Create markdown content with mermaid code
        markdown_content = f"""# WikidataGraphRAG Process Flow

Question: {self.question}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

```mermaid
{chr(10).join(mermaid_code)}
```
"""
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return filename
    
    def save_ttl(self):
        """Generate and save TTL file (simplified)"""
        if not self.logs:
            return None
            
        # Create filename
        filename_base = self._get_filename_base()
        temp_dir = tempfile.gettempdir()
        filename = f"{temp_dir}/{filename_base}.ttl"
        
        # Generate a very basic TTL representation
        ttl_content = f"""@prefix log: <https://w3id.org/sepses/ns/log#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix : <http://example.org/> .

:Process rdfs:label "WikidataGraphRAG Process" .
:Question rdfs:label "{self.question}" .
:StartTime rdfs:label "{self.start_time.isoformat()}"^^xsd:dateTime .
"""

        # Add log entries
        for i, log in enumerate(self.logs):
            ttl_content += f"""
:Event{i} a log:Event ;
    rdfs:label "{log['event_type']}" ;
    log:component "{log['component']}" ;
    log:timestamp "{log['timestamp']}"^^xsd:dateTime .
"""
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(ttl_content)
        
        return filename
    
    def save_visualization_files(self):
        """Save all visualization files and return their paths"""
        json_path = self.save_logs_to_json()
        mermaid_path = self.save_mermaid_diagram()
        ttl_path = self.save_ttl()
        
        return {
            'json_path': json_path,
            'mermaid_path': mermaid_path,
            'ttl_path': ttl_path
        }

# WikidataAPI helper class
class WikidataAPI:
    def __init__(self, url="https://query.wikidata.org/sparql") -> None:
        self.sparqlwd = SPARQLWrapper(
            url,
            agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11",
        )

    def execute_sparql(self, q: str) -> tuple:
        self.sparqlwd.setQuery(q)
        self.sparqlwd.setReturnFormat(JSON)
        try:
            results = self.sparqlwd.query().convert()
            results_cleaned = []
            for result in results["results"]["bindings"]:
                tmp = dict()
                for header in results["head"]["vars"]:
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

# State class for LangGraph
class WikidataGraphState(BaseModel):
    """State for the WikidataGraph workflow"""
    question: str
    translated_question: Optional[str] = None
    extracted_entities: List[str] = Field(default_factory=list)
    entity_uri: Optional[str] = None
    sparql_query: Optional[str] = None
    query_result: List[Dict] = Field(default_factory=list)
    final_answer: Optional[str] = None
    next: Optional[str] = None
    approach_used: Optional[str] = None
    debug_callback: Optional[Any] = None

# Node implementations
class TranslationNode:
    """Node for translating questions if not in English"""
    def __init__(self, debug_callback=None):
        self.translator = Translator()
        self.debug_callback = debug_callback
        
    def __call__(self, state: WikidataGraphState) -> WikidataGraphState:
        # Start timing
        start_time = datetime.now()
        
        # Debug notification - start
        if self.debug_callback:
            self.debug_callback({
                "component": "Translation Node",
                "event_type": "start",
                "details": {"question": state.question}
            })
        
        # Detect language
        detected = self.translator.detect(state.question)
        original_lang = detected.lang
        
        # Debug notification - language detection
        if self.debug_callback:
            self.debug_callback({
                "component": "Translation Node",
                "event_type": "language detection",
                "details": {"detected_language": original_lang}
            })
        
        # Translate if not English
        if original_lang != "en":
            translated_question = self.translator.translate(state.question, dest="en").text
            
            # Debug notification - translation
            if self.debug_callback:
                self.debug_callback({
                    "component": "Translation Node",
                    "event_type": "translation",
                    "details": {"original": state.question, "translated": translated_question}
                })
        else:
            translated_question = state.question
            
            # Debug notification - no translation needed
            if self.debug_callback:
                self.debug_callback({
                    "component": "Translation Node",
                    "event_type": "no translation needed",
                    "details": {"question": state.question}
                })
        
        # Update state
        state.translated_question = translated_question
        
        # Debug notification - end
        if self.debug_callback:
            self.debug_callback({
                "component": "Translation Node",
                "event_type": "end",
                "details": None
            })
        
        return state

class EntityExtractionNode:
    """Node for extracting entities from questions"""
    def __init__(self, llm, debug_callback=None):
        self.llm = llm
        self.debug_callback = debug_callback
        
    def __call__(self, state: WikidataGraphState) -> WikidataGraphState:
        # Start timing
        start_time = datetime.now()
        
        # Debug notification - start
        if self.debug_callback:
            self.debug_callback({
                "component": "Entity Extraction Node",
                "event_type": "start",
                "details": {"question": state.translated_question}
            })
        
        # Use Gemini to extract entities
        prompt = f"""You are an expert entity extractor for knowledge graph querying. Analyze this question and identify all entities mentioned:

Question: {state.translated_question}

Extract ALL entities mentioned in the question, outputting only a JSON array of entity names.
For example, for "Who is the president of France?", output: ["France"].
For "What's the height of Mount Everest?", output: ["Mount Everest"].
For "When did Leonardo DiCaprio win an Oscar?", output: ["Leonardo DiCaprio", "Oscar"].

Output only the JSON array of entity names with no additional text:"""
        
        # Debug notification - prompt preparation
        if self.debug_callback:
            self.debug_callback({
                "component": "Entity Extraction Node",
                "event_type": "prompt prepared",
                "details": {"prompt": prompt[:100] + "..."}
            })
        
        try:
            # Extract entities using Gemini
            response = self.llm.invoke(prompt)
            content = response.content
            
            # Debug notification - raw response
            if self.debug_callback:
                self.debug_callback({
                    "component": "Entity Extraction Node",
                    "event_type": "llm response",
                    "details": {"response": content}
                })
            
            # Parse entities from response
            entities = []
            try:
                # Try to extract JSON
                match = re.search(r'\[.*\]', content)
                if match:
                    entities = json.loads(match.group(0))
                else:
                    # If no JSON format, try to extract entities from text
                    lines = content.split('\n')
                    for line in lines:
                        if line.strip() and not line.startswith("```") and not line.endswith("```"):
                            entities.append(line.strip())
            except Exception as e:
                if self.debug_callback:
                    self.debug_callback({
                        "component": "Entity Extraction Node",
                        "event_type": "parsing error",
                        "details": {"error": str(e), "content": content}
                    })
            
            # Update state with extracted entities
            state.extracted_entities = entities
            
            # Debug notification - entities extracted
            if self.debug_callback:
                self.debug_callback({
                    "component": "Entity Extraction Node",
                    "event_type": "entities extracted",
                    "details": {"entities": entities}
                })
            
        except Exception as e:
            if self.debug_callback:
                self.debug_callback({
                    "component": "Entity Extraction Node",
                    "event_type": "extraction error",
                    "details": {"error": str(e)}
                })
            state.extracted_entities = []
        
        # Debug notification - end
        if self.debug_callback:
            self.debug_callback({
                "component": "Entity Extraction Node",
                "event_type": "end",
                "details": None
            })
        
        return state

class SPARQLGenerationNode:
    """Node for generating SPARQL queries"""
    def __init__(self, llm, api, debug_callback=None):
        self.llm = llm
        self.api = api
        self.debug_callback = debug_callback
        
    def __call__(self, state: WikidataGraphState) -> WikidataGraphState:
        # Start timing
        start_time = datetime.now()
        
        # Debug notification - start
        if self.debug_callback:
            self.debug_callback({
                "component": "SPARQL Generation Node",
                "event_type": "start",
                "details": {"question": state.translated_question, "entities": state.extracted_entities}
            })
        
        # Gather entity information for the query generation
        entities_info = []
        for entity in state.extracted_entities:
            entity_resources, _ = self.api.get_entities(entity, k=5)
            entities_info.append({
                "entity": entity,
                "resources": entity_resources
            })
            
            # Debug notification - entity resources
            if self.debug_callback:
                self.debug_callback({
                    "component": "SPARQL Generation Node",
                    "event_type": f"entity resources for '{entity}'",
                    "details": {"resources": entity_resources[:2]}  # Only show first 2 for brevity
                })
        
        # Format entity information
        entities_matches_formatted = ""
        for info in entities_info:
            entities_matches_formatted += f"Entity: {info['entity']}\n"
            for resource in info['resources']:
                entities_matches_formatted += f"- id: {resource['uri']}, label: {resource['label']}, description: {resource['description']}\n"
        
        # Create prompt for SPARQL generation
        prompt = f"""You are a SPARQL query expert for Wikidata. Generate a SPARQL query for the following question:

Question: {state.translated_question}

Available Wikidata entities:
{entities_matches_formatted}

Important guidelines:
1. Always use PREFIX notation (wd:Q123, wdt:P123) not full URIs
2. Return entity IDs directly without using label services
3. Always include DISTINCT to avoid duplicates
4. Filter results appropriately
5. For counts, use (COUNT(?var) as ?count)
6. For ordering, use ORDER BY DESC(?var) LIMIT X
7. Only include the minimum necessary properties

Output ONLY the SPARQL query without any other text:"""
        
        # Debug notification - prompt
        if self.debug_callback:
            self.debug_callback({
                "component": "SPARQL Generation Node",
                "event_type": "prompt prepared",
                "details": {"prompt": prompt[:200] + "..."}
            })
        
        try:
            # Generate SPARQL query
            response = self.llm.invoke(prompt)
            query_text = response.content.strip()
            
            # Extract the query (remove markdown code blocks if present)
            query_text = re.sub(r'^```sparql\n', '', query_text)
            query_text = re.sub(r'\n```$', '', query_text)
            
            # Debug notification - generated query
            if self.debug_callback:
                self.debug_callback({
                    "component": "SPARQL Generation Node",
                    "event_type": "query generated",
                    "details": {"query": query_text}
                })
            
            # Update state
            state.sparql_query = query_text
            
            # Execute the query
            try:
                # Debug notification - executing query
                if self.debug_callback:
                    self.debug_callback({
                        "component": "SPARQL Generation Node",
                        "event_type": "executing query",
                        "details": {"query": query_text}
                    })
                
                result, err = self.api.execute_sparql(query_text)
                
                if err:
                    # Debug notification - query error
                    if self.debug_callback:
                        self.debug_callback({
                            "component": "SPARQL Generation Node",
                            "event_type": "query execution error",
                            "details": {"error": str(err)}
                        })
                else:
                    # Debug notification - query results
                    if self.debug_callback:
                        self.debug_callback({
                            "component": "SPARQL Generation Node",
                            "event_type": "query execution results",
                            "details": {"results": result[:5], "result_count": len(result)}
                        })
                    
                    # Update state with results
                    state.query_result = result
                    state.approach_used = "sparql"
            except Exception as e:
                # Debug notification - execution error
                if self.debug_callback:
                    self.debug_callback({
                        "component": "SPARQL Generation Node",
                        "event_type": "query execution error",
                        "details": {"error": str(e)}
                    })
        except Exception as e:
            # Debug notification - generation error
            if self.debug_callback:
                self.debug_callback({
                    "component": "SPARQL Generation Node",
                    "event_type": "query generation error",
                    "details": {"error": str(e)}
                })
        
        # Debug notification - end
        if self.debug_callback:
            self.debug_callback({
                "component": "SPARQL Generation Node",
                "event_type": "end",
                "details": None
            })
        
        return state

class AnswerGenerationNode:
    """Node for generating final answers"""
    def __init__(self, llm, debug_callback=None):
        self.llm = llm
        self.debug_callback = debug_callback
        self.translator = Translator()
        
    def __call__(self, state: WikidataGraphState) -> WikidataGraphState:
        # Start timing
        start_time = datetime.now()
        
        # Debug notification - start
        if self.debug_callback:
            self.debug_callback({
                "component": "Answer Generation Node",
                "event_type": "start",
                "details": {"question": state.question}
            })
        
        # Format the query results for the prompt
        results_formatted = ""
        if state.query_result:
            results_formatted = "Query Results:\n"
            for i, result in enumerate(state.query_result[:10]):  # Limit to 10 results
                results_formatted += f"Result {i+1}: {result}\n"
            if len(state.query_result) > 10:
                results_formatted += f"... and {len(state.query_result) - 10} more results\n"
        else:
            results_formatted = "No results found."
        
        # Create prompt for answer generation
        prompt = f"""Answer the following question based on the provided query results.
Be detailed, yet concise (typically 2-3 sentences). If the results don't answer
the question, say so clearly.

Question: {state.question}

SPARQL Query Used:
{state.sparql_query}

{results_formatted}

Answer in a natural, conversational way. Do not mention SPARQL or the queries in your answer.
"""
        
        # Debug notification - prompt
        if self.debug_callback:
            self.debug_callback({
                "component": "Answer Generation Node",
                "event_type": "prompt prepared",
                "details": {"prompt": prompt[:200] + "..."}
            })
        
        try:
            # Generate answer
            response = self.llm.invoke(prompt)
            answer = response.content.strip()
            
            # Debug notification - generated answer
            if self.debug_callback:
                self.debug_callback({
                    "component": "Answer Generation Node",
                    "event_type": "answer generated",
                    "details": {"answer": answer}
                })
            
            # Update state
            state.final_answer = answer
            
        except Exception as e:
            # Debug notification - generation error
            if self.debug_callback:
                self.debug_callback({
                    "component": "Answer Generation Node",
                    "event_type": "answer generation error",
                    "details": {"error": str(e)}
                })
            
            # Set a fallback answer
            state.final_answer = "I'm sorry, I couldn't generate an answer based on the available information."
        
        # Debug notification - end
        if self.debug_callback:
            self.debug_callback({
                "component": "Answer Generation Node",
                "event_type": "end",
                "details": None
            })
        
        return state

# Main agent class
class WikidataGraphAgent:
    """Agent that uses LangGraph for Wikidata question answering"""
    
    def __init__(
        self,
        gemini_api_key=None,
        always_use_generate_sparql=False,
        print_output=False,
        debug_callback=None
    ):
        # Set API key
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not self.gemini_api_key:
            raise ValueError(
                "Gemini API key must be provided or set as GEMINI_API_KEY environment variable"
            )
        
        # Initialize Gemini
        genai.configure(api_key=self.gemini_api_key)
        
        # Initialize Wikidata API
        self.api = WikidataAPI()
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", 
                                          temperature=0.2, 
                                          google_api_key=self.gemini_api_key)
        
        # Set debug callback
        self.debug_callback = debug_callback
        
        # Build the graph
        self.build_graph()
        
        # Visualization files
        self.visualization_files = {}

    def build_graph(self):
        """Build the LangGraph workflow"""
        # Create nodes
        translation_node = TranslationNode(debug_callback=self.debug_callback)
        entity_extraction_node = EntityExtractionNode(self.llm, debug_callback=self.debug_callback)
        sparql_generation_node = SPARQLGenerationNode(self.llm, self.api, debug_callback=self.debug_callback)
        answer_generation_node = AnswerGenerationNode(self.llm, debug_callback=self.debug_callback)
        
        # Create the graph
        workflow = StateGraph(WikidataGraphState)
        
        # Add nodes
        workflow.add_node("translation", translation_node)
        workflow.add_node("entity_extraction", entity_extraction_node)
        workflow.add_node("sparql_generation", sparql_generation_node)
        workflow.add_node("answer_generation", answer_generation_node)
        
        # Define the flow
        workflow.set_entry_point("translation")
        workflow.add_edge("translation", "entity_extraction")
        workflow.add_edge("entity_extraction", "sparql_generation")
        workflow.add_edge("sparql_generation", "answer_generation")
        workflow.add_edge("answer_generation", END)
        
        # Compile the graph
        self.graph = workflow.compile()

    def create_explanation(self, state):
        """Create a detailed explanation of the process and results"""
        explanation = f"""## Question Answering Process
**Question:** {state.question}

"""
        # Add extracted entities
        if state.extracted_entities:
            explanation += f"""### Extracted Entities
{", ".join(state.extracted_entities)}

"""
        
        # Add SPARQL query
        if state.sparql_query:
            explanation += f"""### SPARQL Query
```sparql
{state.sparql_query}
```

"""
        
        # Add query results
        if state.query_result:
            explanation += f"""### Query Results
"""
            # Format as table
            if state.query_result:
                # Get column headers
                headers = list(state.query_result[0].keys())
                
                # Create table header
                explanation += "| " + " | ".join(headers) + " |\n"
                explanation += "| " + " | ".join(["---"] * len(headers)) + " |\n"
                
                # Add rows (limit to 10 rows for readability)
                max_rows = min(10, len(state.query_result))
                for row in state.query_result[:max_rows]:
                    explanation += "| " + " | ".join(str(row.get(h, "")) for h in headers) + " |\n"
                
                if len(state.query_result) > 10:
                    explanation += f"\n*...and {len(state.query_result) - 10} more rows*\n"
            else:
                explanation += "*No results found*\n"
            
            explanation += "\n"
        
        # Add final answer
        explanation += f"""### Final Answer
{state.final_answer}
"""
        
        return explanation

    def query(self, question, verbose=0, boxology_verbose=0):
        """Process a question and return answer, explanation, and visualization data
        
        Args:
            question: The question to process
            verbose: Level of verbosity for process logging (0-2)
            boxology_verbose: Level of verbosity for boxology visualization (0-2)
        
        Returns:
            Tuple of (final_answer, explanation, visualization_data)
        """
        # Initialize visualizer if boxology_verbose > 0
        visualizer = None
        if boxology_verbose > 0:
            visualizer = BoxologyVisualizer(boxology_verbose)
            visualizer.set_question(question)
            
            # Register visualizer with debug callback
            original_debug_callback = self.debug_callback
            
            def combined_callback(data):
                if original_debug_callback:
                    original_debug_callback(data)
                visualizer.log_event(
                    data["component"],
                    data["event_type"],
                    data["details"]
                )
            
            debug_callback = combined_callback
        else:
            debug_callback = self.debug_callback
        
        # Initialize the state
        initial_state = WikidataGraphState(
            question=question,
            debug_callback=debug_callback
        )
        
        # Run the graph
        final_state_dict = self.graph.invoke(initial_state)
        
        # Convert the AddableValuesDict back to our state type
        final_state = WikidataGraphState(**dict(final_state_dict))
        
        # Generate explanation
        explanation = self.create_explanation(final_state)
        
        # Generate visualization files if requested
        visualization_data = None
        if boxology_verbose > 0 and visualizer:
            visualization_data = visualizer.save_visualization_files()
        
        return final_state.final_answer, explanation, visualization_data
