# backend/agent/langgraph/nodes/sparql_generation.py
import re
import json
import logging
from datetime import datetime
from typing import Optional
from SPARQLWrapper import SPARQLWrapper, JSON
from ..utils.state import FROGGraphRAGState
from ..utils.date_utils import format_reference_date
from ..utils.knowledge_graph_metadata import get_knowledge_graph_metadata

logger = logging.getLogger(__name__)

class SparqlGenerationNode:
    """Node for generating and executing SPARQL queries"""
    def __init__(self, llm_factory=None, property_retrieval=None):
        """
        Initialize SparqlGenerationNode
        
        Args:
            llm_factory: LLM factory instance for multi-provider support
            property_retrieval: Property retrieval system
        """
        self.llm_factory = llm_factory
        self.property_retrieval = property_retrieval
        self.sparql_pattern = r"```(?:sparql)?\s*([\s\S]*?)```"
        
        if not self.llm_factory:
            raise ValueError("llm_factory must be provided")
        
        # Use source-aware SPARQL wrapper if available
        try:
            from ..utils.sparql_wrapper import SourceAwareSPARQLWrapper
            self.api = SourceAwareSPARQLWrapper("wikidata")
        except ImportError:
            # Fallback to standard SPARQLWrapper
            self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
            self.api.setReturnFormat(JSON)
            self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        
        # Initialize the LLM provider
        try:
            self._llm_provider = self.llm_factory.get_model_for_sparql_generation()
            logger.info("Initialized SparqlGenerationNode with LLM factory")
        except Exception as e:
            logger.error(f"Failed to get model from factory: {e}")
            raise ValueError(f"Failed to initialize LLM provider: {e}")
        
    def execute_sparql(self, q: str, state=None):
        """Execute a SPARQL query"""
        # Set source if available in state
        if hasattr(state, 'knowledge_source') and hasattr(self.api, 'set_source'):
            self.api.set_source(state.knowledge_source)
            
        if hasattr(self.api, 'execute_sparql'):
            # Use our source-aware wrapper
            return self.api.execute_sparql(q)
        else:
            # Legacy method
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
            
    def _enhance_query_with_references(self, query: str, state: FROGGraphRAGState):
        """
        Enhance a SPARQL query to include reference information if requested
        
        Args:
            query: The original SPARQL query
            state: The current state containing include_references flag
            
        Returns:
            An enhanced query that includes reference information
        """
        # Check if we should include references
        if not state.include_references:
            return query
            
        # Check if the knowledge source supports references
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        kg_metadata = get_knowledge_graph_metadata()
        if not kg_metadata.supports_references(knowledge_source):
            return query
            
        # Parse the query to find wdt: patterns
        # Pattern to find triple patterns like: wd:Q142 wdt:P35 ?president
        wdt_patterns = re.findall(r'(\w+:[\w\d]+)\s+(wdt:P\d+)\s+(\?\w+)', query)
        
        if not wdt_patterns:
            return query  # No patterns to enhance
            
        # Build the enhanced query
        enhanced_parts = []
        counter = 1
        new_select_vars = []
        
        # Extract the SELECT clause variables
        select_match = re.search(r'SELECT\s+(.*?)\s+WHERE', query, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_vars = select_match.group(1).strip()
        else:
            return query  # Not a standard SELECT query
            
        # Process each wdt: pattern
        for subject, predicate, obj in wdt_patterns:
            # Extract property ID from predicate (remove the 'wdt:' prefix)
            property_id = predicate[4:]
            
            statement_var = f"?statement{counter}"
            ref_url_var = f"?refUrl{counter}"
            ref_date_var = f"?refDate{counter}"
            
            # Create reference patterns
            ref_patterns = [
                f"  OPTIONAL {{",
                f"    {subject} p:{property_id} {statement_var} .",
                f"    {statement_var} ps:{property_id} {obj} .",
                f"    OPTIONAL {{",
                f"      {statement_var} prov:wasDerivedFrom ?reference{counter} .",
                f"      OPTIONAL {{ ?reference{counter} pr:P854 {ref_url_var} }}",
                f"      OPTIONAL {{ ?reference{counter} pr:P813 {ref_date_var} }}",
                f"    }}",
                f"  }}"
            ]
            
            enhanced_parts.extend(ref_patterns)
            new_select_vars.extend([ref_url_var, ref_date_var])
            counter += 1
            
        # Add new variables to SELECT clause
        if new_select_vars:
            for var in new_select_vars:
                if var not in select_vars:
                    select_vars += f" {var}"
                    
        # Rebuild the query
        # Find the WHERE clause
        where_match = re.search(r'(WHERE\s*\{)(.*?)(\})', query, re.IGNORECASE | re.DOTALL)
        if where_match:
            before_where = query[:where_match.start()]
            where_content = where_match.group(2)
            after_where = query[where_match.end():]
            
            # Update the SELECT clause
            before_select = before_where[:select_match.start()]
            enhanced_query = before_select + f"SELECT {select_vars} WHERE {{\n{where_content}\n"
            
            # Add the reference patterns
            enhanced_query += "\n".join(enhanced_parts)
            enhanced_query += "\n}" + after_where
            
            return enhanced_query
            
        return query
        
    def get_entities(self, entity: str, k: int = 5, source: str = "wikidata"):
        """Search for entities in knowledge base"""
        # Use property retrieval factory to get the appropriate entity retriever
        from ..utils.property_retrieval_factory import get_property_retrieval_factory
        property_factory = get_property_retrieval_factory()
        property_retriever = property_factory.get_property_retriever(source)
        
        if property_retriever and hasattr(property_retriever, 'get_related_entities'):
            try:
                # Use the get_related_entities method
                result = property_retriever.get_related_entities(entity, [entity], k=k)
                return result.get("entities", []), None
            except Exception as e:
                logger.error(f"Error using property retriever for entity search in {source}: {e}")
                return [], e
        
        # For legal and gesis, use property retrieval for entity search
        if source in ["legal", "gesis"]:
            try:
                from ..utils.property_retrieval_factory import get_property_retrieval_factory
                property_factory = get_property_retrieval_factory()
                property_retriever = property_factory.get_property_retriever(source)
                
                if property_retriever:
                    result = property_retriever.get_related_candidates(entity, [entity], k=k)
                    return result.get("entities", []), None
            except Exception as e:
                logger.error(f"Error using property retriever for entity search in {source}: {e}")
                return [], e
        
        # Default to Wikidata API
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
            logger.error(f"Error searching for entities: {e}")
            return [], e
    
    def _extract_references_from_results(self, results):
        """
        Extract reference information from SPARQL query results
        
        Args:
            results: List of SPARQL query result dictionaries
            
        Returns:
            List of reference dictionaries with formatted dates
        """
        references = []
        seen_refs = set()  # To avoid duplicates
        
        for result in results:
            # Look for reference URL and date fields
            ref_url = None
            ref_date = None
            
            # Check for various reference field names that might be in the results
            for key, value in result.items():
                if key.lower().startswith('refurl') and value:
                    ref_url = value
                elif key.lower().startswith('refdate') and value:
                    ref_date = value
            
            # If we found reference information, add it to our list
            if ref_url or ref_date:
                ref_key = f"{ref_url}_{ref_date}"  # Create unique key
                if ref_key not in seen_refs:
                    seen_refs.add(ref_key)
                    ref_dict = {}
                    if ref_url:
                        ref_dict['refUrl'] = ref_url
                    if ref_date:
                        ref_dict['refDate'] = ref_date
                        ref_dict['formattedRefDate'] = format_reference_date(ref_date)
                    references.append(ref_dict)
        
        return references
        
    def __call__(self, state: FROGGraphRAGState) -> FROGGraphRAGState:
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
        
        # Determine the knowledge source
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        
        # Get knowledge graph metadata
        kg_metadata = get_knowledge_graph_metadata()
        source_name = kg_metadata.get_name(knowledge_source)
        instructions = kg_metadata.get_sparql_instructions(knowledge_source)
        
        # Build the system prompt based on metadata
        instructions_text = "\n".join([f"{i+1}. {instruction}" for i, instruction in enumerate(instructions)])
        
        system_prompt = f"""You are a SPARQL generator expert for {source_name} knowledge graph. Your task is to convert the following natural language question to a SPARQL query for {source_name} using the provided entity and property resolutions.

Guidelines:
1. First identify which entities from the list match the question's intent
2. Identify which entities are relevant to the question and select EXACTLY ONE entity ID for each distinct concept in the question
3. When multiple entities have similar labels, choose the one whose description best matches the question's context
4. From the properties list, choose which properties are needed to answer the question
5. Select only the minimum necessary properties required to answer the question correctly
6. Use ALL identified entities and necessary properties in your SPARQL query
7. {instructions_text}
8. Optimize your query by using appropriate SPARQL features (DISTINCT, FILTER, ORDER BY, LIMIT) when needed
9. Return ONLY the raw SPARQL query with no explanations or comments in this format:
   ```sparql
   <your_sparql_query_here>
   ```"""
        
        # Gather resources for the query generation
        entities_matches_formatted = ""
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        for entity in state.extracted_entities:
            entity_resources, _ = self.get_entities(entity, k=5, source=knowledge_source)
            for resource in entity_resources:
                if 'description' in resource and resource['description']:
                    entities_matches_formatted += f"- id: {resource['uri']}, label: {resource['label']}, description: {resource['description']}\n"
                else:
                    entities_matches_formatted += f"- id: {resource['uri']}, label: {resource['label']}\n"
            
            # Log entity resources
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event( 
                    "SPARQL Generation Node",
                    f"entity resources for '{entity}'",
                    {"resources": entity_resources}
                )

        # Get knowledge source and use appropriate property retrieval
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        
        # Use property retrieval factory to get the appropriate property retrieval
        from ..utils.property_retrieval_factory import get_property_retrieval_factory
        property_factory = get_property_retrieval_factory()
        current_property_retrieval = property_factory.get_property_retriever(
            knowledge_source, 
            df_properties=self.property_retrieval.df_properties if knowledge_source == "wikidata" else None
        )
                
        # Get ontology candidates
        ontology = current_property_retrieval.get_related_candidates(
            state.translated_question, property_candidates=state.related_properties, threshold=0.6
        )
        
        # Format properties context
        properties_matches_formatted = ""
        for prop in ontology.get("properties", []):
            # Check if we're using curriculum or wikidata format
            if knowledge_source == 'curriculum':
                if " - " in prop:
                    prop_id, prop_label = prop.split(" - ", 1)
                    properties_matches_formatted += f"- id: {prop_id}, label: {prop_label}\n"
                else:
                    properties_matches_formatted += f"- id: {prop}, label: {prop}\n"
            else:
                # Wikidata format with P-IDs
                if " - " in prop:
                    prop_id, prop_label = prop.split(" - ", 1)
                    # Get property description from df_properties if available
                    prop_desc = ""
                    if hasattr(current_property_retrieval, "df_properties"):
                        prop_row = current_property_retrieval.df_properties[current_property_retrieval.df_properties["propertyId"] == prop_id]
                        if not prop_row.empty:
                            prop_desc = prop_row.iloc[0].get("description", "")
                    properties_matches_formatted += f"- id: {prop_id}, label: {prop_label}, description: {prop_desc}\n"
        
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
                # Create combined prompt for generation
                combined_prompt = f"{system_prompt}\n\n{user_prompt_template}"
                
                # Generate SPARQL query using configured model
                if self._llm_provider.is_chat_template_supported():
                    # Use chat template
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt_template}
                    ]
                    prompt = self._llm_provider.apply_chat_template(messages)
                else:
                    # Fallback to simple concatenation
                    prompt = combined_prompt
                
                completion = self._llm_provider.generate_response(prompt)
                
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
                
                # Add PREFIX declarations if not already present (for any knowledge source)
                if sparql_query:
                    # Check if PREFIX declarations are already in the query
                    if not sparql_query.upper().startswith("PREFIX"):
                        # Get PREFIX declarations from metadata
                        prefixes_declaration = kg_metadata.get_prefixes_declaration(knowledge_source)
                        if prefixes_declaration:
                            sparql_query = prefixes_declaration + "\n\n" + sparql_query
                            # Log prefix addition
                            if hasattr(state, 'visualizer') and state.visualizer:
                                state.visualizer.log_event(
                                    "SPARQL Generation Node",
                                    f"added prefixes for {knowledge_source}",
                                    {"prefixes_added": prefixes_declaration}
                                )
                
                # Enhance the query with references if requested
                if sparql_query and state.include_references:
                    original_query = sparql_query
                    sparql_query = self._enhance_query_with_references(sparql_query, state)
                    
                    if hasattr(state, 'visualizer') and state.visualizer and original_query != sparql_query:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            f"query enhanced with references",
                            {"original": original_query, "enhanced": sparql_query}
                        )
                
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
                    print(f"\nGenerated SPARQL:\n{sparql_query}")
                    
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
                    
                result, err = self.execute_sparql(sparql_query, state)
                
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
                    
                    # Extract references if the query included reference fields
                    references = []
                    if state.include_references and result:
                        references = self._extract_references_from_results(result)
                        if references:
                            state.sparql_references = references
                            
                            # Log references found
                            if hasattr(state, 'visualizer') and state.visualizer:
                                state.visualizer.log_event(
                                    "SPARQL Generation Node",
                                    "references extracted",
                                    {
                                        "reference_count": len(references),
                                        "sample_references": references[:3] if len(references) > 3 else references
                                    }
                                )
                    
                    # Log success
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "SPARQL Generation Node",
                            "successful query execution",
                            {
                                "query": sparql_query,
                                "result_count": len(result),
                                "attempt": attempt_num,
                                "references_found": len(references) if references else 0
                            }
                        )
                    
                    # Process the results for the answer
                    if not result:
                        state.context_str = "I couldn't find information to answer this question."
                    else:
                        # Check if we need to process entity URIs (only for Wikidata)
                        if knowledge_source == "wikidata":
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
                                        
                                    label_results, _ = self.execute_sparql(label_query, state)
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
                        
                        # Add reference information to context if available
                        if hasattr(state, 'sparql_references') and state.sparql_references:
                            context_str += "\n\n**Reference sources:**"
                            unique_refs = set()
                            formatted_dates = set()
                            
                            for ref in state.sparql_references:
                                if ref.get('refUrl'):
                                    unique_refs.add(ref['refUrl'])
                                if ref.get('formattedRefDate'):
                                    formatted_dates.add(ref['formattedRefDate'])
                            
                            for ref_url in unique_refs:
                                context_str += f"\n- Source: {ref_url}"
                            
                            for date in formatted_dates:
                                context_str += f"\n- Retrieved on: {date}"
                        
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
                    print(f"\nQuery returned no results. Retrying... ({attempts_left} attempts left)")
                    
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
        use_google_search = getattr(state, 'use_google_search', True)
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        kg_metadata = get_knowledge_graph_metadata()
        source_name = kg_metadata.get_name(knowledge_source)
        
        if use_google_search:
            state.context_str = "I couldn't generate a working query to answer this question."
            # Mark that SPARQL failed
            state.approach_used = "sparql_failed"
        else:
            # Google Search is disabled, provide a more informative message
            state.context_str = f"I couldn't generate a working SPARQL query to answer this question using {source_name}. Google Search fallback is disabled in settings."
            state.approach_used = "sparql_failed_no_fallback"
        
        # Log failure after all attempts
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "SPARQL Generation Node",
                "all attempts failed",
                {
                    "total_attempts": state.try_threshold,
                    "google_search_enabled": use_google_search
                }
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