
# backend/agent/langgraph/nodes/sparql_generation.py
import re
import json
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
from ..utils.state import WikidataGraphRAGState
import google.generativeai as genai

class SparqlGenerationNode:
    """Node for generating and executing SPARQL queries"""
    def __init__(self, genai_model, property_retrieval):
        self.genai_model = genai_model
        self.property_retrieval = property_retrieval
        self.sparql_pattern = r"```(?:sparql)?\\s*([\\s\\S]*?)```"
        self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.api.setReturnFormat(JSON)
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        
    def execute_sparql(self, q: str):
        """Execute a SPARQL query"""
        self.api.setQuery(q)
        try:
            results = self.api.query().convert()
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
        
    def get_entities(self, entity: str, k: int = 5):
        """Search for entities in Wikidata"""
        wikidata_api = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "search": entity,
            "language": "en",
        }
        
        try:
            import requests
            data = requests.get(wikidata_api, params=params)
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
        except Exception as e:
            return [], e
        
    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node", 
                "start",
                {"question": state.translated_question, "entities": state.extracted_entities},
                start_time=start_time
            )
        
        # Define the system prompt for SPARQL generation
        system_prompt = """You are a SPARQL generator expert for Wikidata knowledge graph. Your task is to convert the following natural language question to a SPARQL query for Wikidata using the provided entity and property resolutions.

Guidelines:
1. First identify which entities from the list match the question's intent
2. Identify which entities are relevant to the question and select EXACTLY ONE entity ID for each distinct concept in the question
3. When multiple entities have similar labels, choose the one whose description best matches the question's context
4. From the properties list, choose which properties are needed to answer the question
5. Select only the minimum necessary properties required to answer the question correctly
6. Use ALL identified entities and necessary properties in your SPARQL query
7. Use PREFIX NOTATION ONLY (e.g., wd:Q123, wdt:P123), NOT full URIs
8. Optimize your query by using appropriate SPARQL features (DISTINCT, FILTER, ORDER BY, LIMIT) when needed
9. Return entity IDs directly without using label services
10. Return ONLY the raw SPARQL query with no explanations or comments in this format:
   ```sparql
   <your_sparql_query_here>
   ```"""
        
        # Gather resources for the query generation
        entities_matches_formatted = ""
        for entity in state.extracted_entities:
            entity_resources, _ = self.get_entities(entity, k=5)
            for resource in entity_resources:
                entities_matches_formatted += f"- id: {resource['uri']}, label: {resource['label']}, description: {resource['description']}\\n"
            
            # Log entity resources
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "SPARQL Generation Node",
                    f"entity resources for '{entity}'",
                    {"resources": entity_resources}
                )

        # Get ontology candidates
        ontology = self.property_retrieval.get_related_candidates(
            state.translated_question, property_candidates=state.related_properties, threshold=0.6
        )
        
        # Format properties context
        properties_matches_formatted = ""
        for prop in ontology.get("properties", []):
            # Assuming prop is in format "P123 - label"
            if " - " in prop:
                prop_id, prop_label = prop.split(" - ", 1)
                # Get property description from df_properties if available
                prop_desc = ""
                if hasattr(self.property_retrieval, "df_properties"):
                    prop_row = self.property_retrieval.df_properties[self.property_retrieval.df_properties["propertyId"] == prop_id]
                    if not prop_row.empty:
                        prop_desc = prop_row.iloc[0].get("description", "")
                properties_matches_formatted += f"- id: {prop_id}, label: {prop_label}, description: {prop_desc}\\n"
        
        # Log ontology
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node",
                "ontology candidates",
                {"ontology": ontology}
            )

        # Create user prompt template
        user_prompt_template = f"""Question: {state.translated_question}

Entities:
{entities_matches_formatted}

Properties:
{properties_matches_formatted}

SPARQL:"""

        # Log query generation start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node",
                "query generation phase",
                {"max_attempts": state.try_threshold, "cot_enabled": state.use_cot}
            )
        
        query_attempts = []
        curr_question = state.translated_question
        attempts_left = state.try_threshold
        
        while attempts_left > 0:
            # Record attempt start time
            attempt_start_time = datetime.now()
            attempt_num = state.try_threshold - attempts_left + 1
            
            # Log attempt start
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "SPARQL Generation Node",
                    f"query attempt {attempt_num}",
                    {"question": curr_question},
                    start_time=attempt_start_time
                )
                
            try:
                # Create combined prompt for Gemini - avoid using system role
                combined_prompt = f"{system_prompt}\n\n{user_prompt_template}"
                
                # Generate SPARQL query
                response = self.genai_model.generate_content(combined_prompt)
                completion = response.text
                
                # Log raw completion
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "SPARQL Generation Node",
                        f"completion for attempt {attempt_num}",
                        {"completion": completion}
                    )
                
                # Extract the SPARQL query using regex
                match = re.search(self.sparql_pattern, completion)
                if match:
                    sparql_query = match.group(1).strip()
                else:
                    sparql_query = completion if "SELECT" in completion and "WHERE" in completion else ""
                
                # Record query attempt
                attempt = {
                    "attempt_number": attempt_num,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "query": sparql_query if sparql_query else "Empty query"
                }
                
                query_attempts.append(attempt)
                
                # Skip empty queries
                if not sparql_query:
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            f"empty query in attempt {attempt_num}",
                            None
                        )
                        
                    if state.verbose > 0:
                        print("Empty SPARQL query generated")
                    attempts_left -= 1
                    continue
                
                # Log the results if verbose
                if state.verbose > 0:
                    print(f"\\nGenerated SPARQL:\\n{sparql_query}")
                    
                # Execute the query
                exec_start_time = datetime.now()
                
                # Log execution start
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "SPARQL Generation Node",
                        f"executing query from attempt {attempt_num}",
                        {"query": sparql_query},
                        start_time=exec_start_time
                    )
                    
                result, err = self.execute_sparql(sparql_query)
                
                # End execution timing
                exec_end_time = datetime.now()
                
                # Log execution results
                if hasattr(state, 'visualizer') and state.visualizer:
                    log_results = []
                    if result:
                        for item in result[:10]:  # Only process first 10 items for logging
                            log_item = {}
                            for key, value in item.items():
                                if isinstance(value, str) and value.startswith("http://www.wikidata.org/entity/"):
                                    # Extract entity ID from URI
                                    log_item[key] = value.split('/')[-1]
                                else:
                                    log_item[key] = value
                            log_results.append(log_item)
                    
                    state.visualizer.log_event(
                        "SPARQL Generation Node",
                        f"query execution results from attempt {attempt_num}",
                        {
                            "results": log_results, 
                            "result_count": len(result) if result else 0,
                            "error": str(err) if err else None
                        },
                        start_time=exec_start_time,
                        end_time=exec_end_time
                    )
                
                # Check if we got results
                if result and not (len(result) == 1 and list(result[0].values())[0] == "0"):
                    state.sparql_query = sparql_query
                    state.query_result = result
                    
                    # Mark that SPARQL was successfully used
                    state.approach_used = "sparql"
                    
                    # Log success
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            "successful query execution",
                            {
                                "query": sparql_query,
                                "result_count": len(result),
                                "attempt": attempt_num
                            }
                        )
                    
                    # Process the results for the answer
                    if not result:
                        state.context_str = "I couldn't find information to answer this question."
                    else:
                        # Check if we need to process entity URIs
                        has_wikidata_entities = False
                        entity_uris = []
                        
                        for item in result:
                            for key, value in item.items():
                                if isinstance(value, str) and value.startswith("http://www.wikidata.org/entity/"):
                                    has_wikidata_entities = True
                                    entity_uris.append(value)
                        
                        # If we have Wikidata entities, get their labels
                        if has_wikidata_entities:
                            # Extract entity IDs
                            entity_ids = []
                            for uri in entity_uris:
                                entity_id = uri.split("/")[-1]
                                entity_ids.append(entity_id)
                            
                            # Generate query for entity labels
                            values_str = " ".join([f"wd:{eid}" for eid in entity_ids])
                            label_query = f"""
                            SELECT ?item ?itemLabel WHERE {{
                              VALUES ?item {{ {values_str} }}
                              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
                            }}
                            """
                            
                            # Get entity labels
                            entity_labels = {}
                            try:
                                # Log label query
                                if hasattr(state, 'visualizer') and state.visualizer:
                                    state.visualizer.log_event(
                                        "SPARQL Generation Node",
                                        "entity label lookup",
                                        {"label_query": label_query, "entity_ids": entity_ids}
                                    )
                                    
                                label_results, _ = self.execute_sparql(label_query)
                                for item in label_results:
                                    if "item" in item and "itemLabel" in item:
                                        uri = item["item"]
                                        entity_id = uri.split("/")[-1]
                                        entity_labels[uri] = f"{item['itemLabel']} ({entity_id})"
                            except Exception as e:
                                if hasattr(state, 'visualizer') and state.visualizer:
                                    state.visualizer.log_event(
                                        "SPARQL Generation Node",
                                        "entity label lookup error",
                                        {"error": str(e)}
                                    )
                                    
                                if state.verbose > 0:
                                    print(f"Error getting entity labels: {e}")
                            
                            # Replace URIs with labels
                            if entity_labels:
                                labeled_result = []
                                for item in result:
                                    new_item = {}
                                    for key, value in item.items():
                                        if isinstance(value, str) and value in entity_labels:
                                            new_item[key] = entity_labels[value]
                                        else:
                                            new_item[key] = value
                                    labeled_result.append(new_item)
                                
                                result = labeled_result
                                
                                # Log labeled results
                                if hasattr(state, 'visualizer') and state.visualizer:
                                    state.visualizer.log_event(
                                        "SPARQL Generation Node",
                                        "labeled results",
                                        {"results": result[:10] if len(result) > 10 else result}
                                    )
                        
                        # Format context as string
                        context_str = f'The answer to "{state.question}" is: '
                        for c in result[:50]:
                            for k, v in c.items():
                                context_str += f"{k}={v}, "
                        context_str = context_str[:-2] + "."
                        state.context_str = context_str
                    
                    # End attempt timing
                    attempt_end_time = datetime.now()
                    
                    # Log attempt end
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            f"query attempt {attempt_num} end",
                            {"status": "success"},
                            start_time=attempt_start_time,
                            end_time=attempt_end_time
                        )
                    
                    # End timing for the whole node
                    end_time = datetime.now()
                    
                    # Log all query attempts
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            "all query attempts",
                            {"attempts": query_attempts}
                        )
                    
                    # Log completion
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node", 
                            "end", 
                            {"status": "success"},
                            start_time=start_time,
                            end_time=end_time
                        )
                        
                    return state
                
                # Query failed, try again
                attempts_left -= 1
                
                # End attempt timing
                attempt_end_time = datetime.now()
                
                # Log attempt failure
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "SPARQL Generation Node",
                        f"query attempt {attempt_num} end",
                        {"status": "failed", "reason": "No results returned"},
                        start_time=attempt_start_time,
                        end_time=attempt_end_time
                    )
                    
                if state.verbose > 0:
                    print(f"\\nQuery returned no results. Retrying... ({attempts_left} attempts left)")
                    
                # Update the question to improve the query
                curr_question = f"""The SPARQL query you generated to answer '{state.translated_question}' produced empty results. 
Please generate a better query. Try using different properties or restructuring the query."""
                
            except Exception as e:
                # End attempt timing
                attempt_end_time = datetime.now()
                
                # Log error
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "SPARQL Generation Node",
                        f"query attempt {attempt_num} error",
                        {"error": str(e)},
                        start_time=attempt_start_time,
                        end_time=attempt_end_time
                    )
                    
                if state.verbose > 0:
                    print(f"Error generating SPARQL: {e}")
                attempts_left -= 1
        
        # Failed after all attempts
        state.context_str = "I couldn't generate a working query to answer this question."
        
        # Mark that SPARQL failed
        state.approach_used = "sparql_failed"
        
        # Log failure after all attempts
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node",
                "all attempts failed",
                {"total_attempts": state.try_threshold}
            )
            
            # Log all query attempts
            state.visualizer.log_event(
                "SPARQL Generation Node",
                "all query attempts",
                {"attempts": query_attempts}
            )
        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node", 
                "end", 
                {"status": "failed"},
                start_time=start_time,
                end_time=end_time
            )
            
        return state
