# backend/agent/langgraph/nodes/verbalization.py (further refactored)
from datetime import datetime
import re
import json
import logging
from SPARQLWrapper import SPARQLWrapper, JSON
from sentence_transformers import SentenceTransformer
import numpy as np
from ..utils.state import FROGGraphRAGState
from ..utils.date_utils import format_reference_date
from ..utils.knowledge_graph_metadata import get_knowledge_graph_metadata

# Import our model singleton
from ..utils.singletons.model_singletons import get_sentence_transformer

# Configure logging
logger = logging.getLogger(__name__)

def replace_using_dict(original_string, replacements):
    """Replace substrings according to replacement dictionary"""
    for old, new in replacements.items():
        original_string = original_string.replace(old, new)
    return original_string

def separate_camel_case(s):
    """Separate camel case strings with spaces"""
    separated = re.sub("([a-z])([A-Z])", r"\1 \2", s)
    return separated

class WikidataVerbalization:
    SENTENCE_TEMPLATE = "{s}'s {p} is {o}"
    MANUAL_MAPPING_DICT = {"_": " "}
    
    def __init__(
        self,
        model_name="jinaai/jina-embeddings-v3",
        model_kwargs={"trust_remote_code": True},
        query_model_encode_kwargs={},
        passage_model_encode_kwargs={},
        knowledge_source="wikidata"
    ) -> None:
        self.model_name = model_name
        self.query_model_encode_kwargs = query_model_encode_kwargs
        self.passage_model_encode_kwargs = passage_model_encode_kwargs
        self.knowledge_source = knowledge_source
        
        # Use the singleton instead of creating a new instance
        self.model = get_sentence_transformer(model_name, **model_kwargs)
        
        # Get knowledge graph metadata
        self.kg_metadata = get_knowledge_graph_metadata()
        
        # Set up SPARQL endpoint and templates based on metadata
        self._setup_sparql_components()
        
        logger.info(f"Initialized WikidataVerbalization with model: {model_name} for source: {knowledge_source}")
    
    def _setup_sparql_components(self):
        """Setup SPARQL endpoint and templates from metadata"""
        endpoint = self.kg_metadata.get_endpoint(self.knowledge_source)
        user_agent = self.kg_metadata.get_user_agent(self.knowledge_source)
        
        self.api = SPARQLWrapper(endpoint)
        self.api.setReturnFormat(JSON)
        self.api.addCustomHttpHeader("User-Agent", user_agent)
        
        # Get templates from metadata
        self.PO_TEMPLATE = self.kg_metadata.get_verbalization_template(self.knowledge_source, "po_template")
        self.SP_TEMPLATE = self.kg_metadata.get_verbalization_template(self.knowledge_source, "sp_template")
        
        if not self.PO_TEMPLATE or not self.SP_TEMPLATE:
            logger.warning(f"Missing verbalization templates for {self.knowledge_source}")
    
    def set_knowledge_source(self, knowledge_source):
        """Update the knowledge source and reconfigure templates and endpoint"""
        if knowledge_source != self.knowledge_source:
            self.knowledge_source = knowledge_source
            self._setup_sparql_components()
            logger.info(f"Updated WikidataVerbalization to use source: {knowledge_source}")

    def execute_sparql(self, q: str):
        """Execute a SPARQL query"""
        logger.debug(f"WikidataVerbalization executing SPARQL query on {self.knowledge_source}: {q}")
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
            logger.error(f"Error executing SPARQL query in WikidataVerbalization on {self.knowledge_source}: {e}")
            logger.error(f"Query that failed: {q}")
            return [], e

    def get_po(self, entity: str, visualizer=None):
        """Get predicate-object pairs for entity"""
        # Handle prefixed URIs vs full URIs
        if self.knowledge_source == "curriculum":
            # For curriculum, entity might be prefixed (e.g., ns1:ethical_hacking)
            # Don't wrap in angle brackets if it contains a colon (indicating a prefix)
            if ':' in entity and not entity.startswith('http'):
                formatted_entity = entity
            else:
                formatted_entity = f"<{entity}>"
        else:
            # For Wikidata, use the entity ID without additional angle brackets
            # since the templates already expect the proper format (wd:Q123)
            formatted_entity = entity
            
        query = self.PO_TEMPLATE.format(entity=formatted_entity)
        
        # Log before executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_po SPARQL execution start",
                {"entity": entity, "formatted_entity": formatted_entity, "query_preview": query[:200] + "..."}
            )
            
        start_time = datetime.now()
        results, err = self.execute_sparql(query)
        end_time = datetime.now()
        
        # Log after executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_po SPARQL execution complete",
                {
                    "entity": entity,
                    "result_count": len(results) if results else 0,
                    "error": str(err) if err else None,
                    "duration_seconds": (end_time - start_time).total_seconds()
                }
            )
            
        if not results or err:
            return []
        
        df = []
        for result in results:
            df.append(result)
        return df

    def get_sp(self, entity: str, visualizer=None):
        """Get subject-predicate pairs for entity"""
        # Handle prefixed URIs vs full URIs
        if self.knowledge_source == "curriculum":
            # For curriculum, entity might be prefixed (e.g., ns1:ethical_hacking)
            # Don't wrap in angle brackets if it contains a colon (indicating a prefix)
            if ':' in entity and not entity.startswith('http'):
                formatted_entity = entity
            else:
                formatted_entity = f"<{entity}>"
        else:
            # For Wikidata, use the entity ID without additional angle brackets
            # since the templates already expect the proper format (wd:Q123)
            formatted_entity = entity
            
        query = self.SP_TEMPLATE.format(entity=formatted_entity)
        
        # Log before executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_sp SPARQL execution start",
                {"entity": entity, "formatted_entity": formatted_entity, "query_preview": query[:200] + "..."}
            )
            
        start_time = datetime.now()
        results, err = self.execute_sparql(query)
        end_time = datetime.now()
        
        # Log after executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_sp SPARQL execution complete",
                {
                    "entity": entity,
                    "result_count": len(results) if results else 0,
                    "error": str(err) if err else None,
                    "duration_seconds": (end_time - start_time).total_seconds()
                }
            )
            
        if not results or err:
            return []
        
        df = []
        for result in results:
            df.append(result)
        return df

    def get_list_of_candidates(self, entity_uri: str, entity_label: str, property_retrieval=None, visualizer=None):
        """Get candidates for verbalization"""
        po, sp = self.get_po(entity_uri, visualizer), self.get_sp(entity_uri, visualizer)
        candidates = dict()

        # Process predicate-object pairs
        curr_p = None
        for result in po:
            p = result.get('p', '')
            o = result.get('o', '')
            sLabel = entity_label  # We know the subject is the entity
            pLabel = result.get('pLabel', '')  # For curriculum, this comes from the query
            oLabel = result.get('oLabel', '')
            
            # Try to get property label from property_retrieval if pLabel not available
            if not pLabel and property_retrieval:
                if self.knowledge_source == "wikidata" and hasattr(property_retrieval, 'property_id_to_label'):
                    prop_id = p.split('/')[-1]  # Extract property ID like P27 from URI
                    pLabel = property_retrieval.property_id_to_label.get(prop_id)
                elif self.knowledge_source == "curriculum" and hasattr(property_retrieval, 'get_related_candidates'):
                    # For curriculum properties, try to find the label using related candidates
                    prop_name = p.split('/')[-1]
                    if ':' in prop_name:
                        prop_name = prop_name.split(':')[-1]  # Extract name from prefixed property
                    try:
                        # Do a quick search for this property
                        results = property_retrieval.get_related_candidates(prop_name, [prop_name], threshold=0.4)
                        if results and results.get("properties"):
                            for prop_result in results.get("properties"):
                                if prop_name in prop_result:
                                    if " - " in prop_result:
                                        pLabel = prop_result.split(" - ")[1]
                                        break
                    except Exception as e:
                        pass  # Silently continue if property search fails
            
            # Fallback to camelCase separation if no label found
            if not pLabel:
                pLabel = separate_camel_case(p.split("/")[-1].split(":")[-1])  # Handle prefixed URIs
            
            label_s = sLabel if sLabel else replace_using_dict(entity_uri.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel

            if label_p != curr_p:
                curr_p = label_p
                if o.startswith("http") or ":" in o:
                    label_o = oLabel if oLabel else replace_using_dict(o.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)
                else:
                    label_o = o
                candidates[p] = self.SENTENCE_TEMPLATE.format(
                    s=str(label_s), p=str(label_p), o=str(label_o)
                )
        
        # Process subject-predicate pairs
        curr_p = None
        for result in sp:
            s = result.get('s', '')
            p = result.get('p', '')
            sLabel = result.get('sLabel', '')
            pLabel = result.get('pLabel', '')  # For curriculum, this comes from the query
            oLabel = entity_label  # We know the object is the entity
            
            # Try to get property label from property_retrieval if pLabel not available
            if not pLabel and property_retrieval:
                if self.knowledge_source == "wikidata" and hasattr(property_retrieval, 'property_id_to_label'):
                    prop_id = p.split('/')[-1]  # Extract property ID like P27 from URI
                    pLabel = property_retrieval.property_id_to_label.get(prop_id)
                elif self.knowledge_source == "curriculum" and hasattr(property_retrieval, 'get_related_candidates'):
                    # For curriculum properties, try to find the label using related candidates
                    prop_name = p.split('/')[-1]
                    if ':' in prop_name:
                        prop_name = prop_name.split(':')[-1]  # Extract name from prefixed property
                    try:
                        # Do a quick search for this property
                        results = property_retrieval.get_related_candidates(prop_name, [prop_name], threshold=0.4)
                        if results and results.get("properties"):
                            for prop_result in results.get("properties"):
                                if prop_name in prop_result:
                                    if " - " in prop_result:
                                        pLabel = prop_result.split(" - ")[1]
                                        break
                    except Exception as e:
                        pass  # Silently continue if property search fails
            
            # Fallback to camelCase separation if no label found
            if not pLabel:
                pLabel = separate_camel_case(p.split("/")[-1].split(":")[-1])  # Handle prefixed URIs
            
            label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel
            label_o = oLabel if oLabel else replace_using_dict(entity_uri.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)

            if label_p != curr_p:
                curr_p = label_p
                candidates[p] = self.SENTENCE_TEMPLATE.format(
                    s=str(label_s), p=str(label_p), o=str(label_o)
                )

        return candidates, po, sp

    def extract_property_id(self, property_uri):
        """Extract property ID (e.g., P27) from full property URI"""
        if not property_uri:
            return None
        
        # Extract property ID from URI like http://www.wikidata.org/prop/direct/P27
        match = re.search(r'/(P\d+)$', property_uri)
        if match:
            return match.group(1)
        return None

    def get_references_for_property(self, entity: str, property_uri: str, knowledge_source: str = "wikidata"):
        """Get reference information for a specific entity and property (if supported by knowledge source)"""
        # Check if the knowledge source supports references using metadata
        if not self.kg_metadata.supports_references(knowledge_source):
            return []
            
        try:
            # Extract property ID
            prop_id = self.extract_property_id(property_uri)
            if not prop_id:
                logger.warning(f"Could not extract property ID from URI: {property_uri}")
                return []

            # Build a simpler reference query
            reference_query = f"""
SELECT DISTINCT ?p ?o ?sLabel ?propLabel ?oLabel ?refUrl ?refDate WHERE {{
  BIND(wd:{entity} AS ?s) .
  BIND(wdt:{prop_id} AS ?p) .
  
  # Get the full statement, not just direct property
  ?s p:{prop_id} ?statement .
  ?statement ps:{prop_id} ?o .
  
  # Get property for labeling
  ?prop wikibase:directClaim ?p .
  
  # Get reference information
  OPTIONAL {{
    ?statement prov:wasDerivedFrom ?reference .
    OPTIONAL {{ ?reference pr:P854 ?refUrl }}
    OPTIONAL {{ ?reference pr:P813 ?refDate }}
  }}
  
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""
            
            logger.info(f"Executing reference query for entity {entity} and property {prop_id}")
            results, err = self.execute_sparql(reference_query)
            
            if err:
                logger.error(f"Error executing reference query: {err}")
                return []
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting references for property {property_uri}: {e}")
            return []

    def encode_with_progress(self, texts, debug_callback=None, **encode_kwargs):
        """Encode texts with progress reporting"""
        if debug_callback:
            from ..utils.custom_encoding import encode_with_progress
            return encode_with_progress(
                self.model,
                texts,
                batch_size=16 if len(texts) > 16 else 1,
                show_progress_bar=True,
                debug_callback=debug_callback,
                **encode_kwargs
            )
        else:
            # Standard encoding without progress reporting
            return self.model.encode(texts, **encode_kwargs)

    def extract_results_for_property(self, property_uri, po, sp, output_uri=False):
        """Extract results for a specific property"""
        result = []
        
        # Add predicate-object pairs
        for p_result in po:
            p = p_result.get('p', '')
            o = p_result.get('o', '')
            pLabel = p_result.get('pLabel', '')  # For curriculum, this comes directly from query
            oLabel = p_result.get('oLabel', '')
            
            if p == property_uri:
                # Use pLabel if available, otherwise fall back to camelCase separation
                label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1].split(":")[-1])  # Handle prefixed URIs
                
                if o.startswith("http") or ":" in o:
                    label_o = oLabel if oLabel else replace_using_dict(o.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)
                else:
                    label_o = o
                result.append({label_p: o if output_uri else label_o})
        
        # Add subject-predicate pairs
        for s_result in sp:
            s = s_result.get('s', '')
            p = s_result.get('p', '')
            sLabel = s_result.get('sLabel', '')
            pLabel = s_result.get('pLabel', '')  # For curriculum, this comes directly from query
            
            if p == property_uri:
                # Use pLabel if available, otherwise fall back to camelCase separation
                label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1].split(":")[-1])  # Handle prefixed URIs
                label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1].split(":")[-1], self.MANUAL_MAPPING_DICT)
                result.append({label_p: s if output_uri else label_s})
                
        return result


class VerbalizationNode:
    """Node for retrieving entity information through verbalization"""
    def __init__(self, llm_factory=None, property_retrieval=None):
        """
        Initialize VerbalizationNode
        
        Args:
            llm_factory: LLM factory instance for multi-provider support
            property_retrieval: Property retrieval system for getting property labels
        """
        self.llm_factory = llm_factory
        self.property_retrieval = property_retrieval
        self.json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        
        # Initialize a default SPARQL endpoint
        self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.api.setReturnFormat(JSON)
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        
        # Get property retrieval factory for different sources
        from ..utils.property_retrieval_factory import get_property_retrieval_factory
        self.property_factory = get_property_retrieval_factory()
        # This factory will also handle entity retrieval
        
        if not self.llm_factory:
            raise ValueError("llm_factory must be provided")
        
        # Initialize the LLM provider
        try:
            self._llm_provider = self.llm_factory.get_model_for_verbalization()
            logger.info("Initialized VerbalizationNode with LLM factory")
        except Exception as e:
            logger.error(f"Failed to get model from factory: {e}")
            raise ValueError(f"Failed to initialize LLM provider: {e}")
        
        logger.info("Initialized VerbalizationNode")        
    
    def execute_sparql(self, q: str):
        """Execute a SPARQL query"""
        logger.debug(f"VerbalizationNode executing SPARQL query: {q}")
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
            logger.error(f"Error executing SPARQL query in VerbalizationNode: {e}")
            logger.error(f"Query that failed: {q}")
            return [], e
        
    def get_entities(self, entity: str, k: int = 5, source: str = "wikidata"):
        """Search for entities in Wikidata or other knowledge sources"""
        # Use property retriever with get_related_entities method
        if source != "wikidata":
            property_retriever = self.property_factory.get_property_retriever(source)
            if property_retriever and hasattr(property_retriever, 'get_related_entities'):
                try:
                    # Now all sources (curriculum, legal, gesis) have get_related_entities method
                    result = property_retriever.get_related_entities(entity, [entity], k=k)
                    return result.get("entities", []), None
                except Exception as e:
                    logger.error(f"Error using property retriever for entity search in {source}: {e}")
        
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

    def get_most_appropriate_entity_uri(self, entity, question, retrieved_entities, knowledge_source="wikidata"):
        """Get the most appropriate entity ID from retrieved entities using LLM"""
        if not retrieved_entities:
            return None
        
        # Get source name from metadata
        kg_metadata = get_knowledge_graph_metadata()
        source_name = kg_metadata.get_name(knowledge_source)
        
        # Define system prompt
        system_prompt = f"""You are an expert entity selector for knowledge graph querying. Your task is to analyze a natural language question and select the most appropriate entity from a list of retrieved entities from {source_name}.

Guidelines:
1. Select the entity whose description and context best matches the question's intent
2. Consider the entity's description and how it relates to the question
3. Choose the entity that would be most useful for answering the given question
4. Return your response as a JSON object with a single 'entity_id' field containing the selected entity's ID

Your output should look like:
```json
{{
  "entity_id": "selected_entity_id"
}}
```"""

        # Format retrieved entities for display
        entities_text = ""
        for i, entity_data in enumerate(retrieved_entities):
            entity_id = entity_data.get("uri", "")
            label = entity_data.get("label", "")
            description = entity_data.get("description", "No description available")
            entities_text += f"{i+1}. ID: {entity_id}\n   Label: {label}\n   Description: {description}\n\n"

        # Create user prompt
        user_prompt = f"""Question: {question}

Target Entity: {entity}

Retrieved Entities:
{entities_text}

Select the most appropriate entity ID that best matches the target entity "{entity}" for answering the question "{question}"."""

        try:
            # Generate response using configured model
            if self._llm_provider.is_chat_template_supported():
                # Use chat template
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                prompt = self._llm_provider.apply_chat_template(messages)
            else:
                # Fallback to simple concatenation
                prompt = f"{system_prompt}\n\n{user_prompt}"
            
            completion = self._llm_provider.generate_response(prompt)
            
            # Extract JSON content from completion
            match = re.search(self.json_pattern, completion)
            if match:
                json_str = match.group(1).strip()
                try:
                    extracted_data = json.loads(json_str)
                    selected_entity_id = extracted_data.get("entity_id", "")
                    
                    # Validate that the selected entity ID exists in retrieved entities
                    for entity_data in retrieved_entities:
                        if entity_data.get("uri", "") == selected_entity_id:
                            return selected_entity_id
                    
                    # If not found, log warning and fall back
                    logger.warning(f"LLM selected entity ID {selected_entity_id} not found in retrieved entities")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse LLM response JSON: {e}")
            else:
                # Try direct parsing if no JSON code block found
                try:
                    extracted_data = json.loads(completion)
                    selected_entity_id = extracted_data.get("entity_id", "")
                    
                    # Validate that the selected entity ID exists in retrieved entities
                    for entity_data in retrieved_entities:
                        if entity_data.get("uri", "") == selected_entity_id:
                            return selected_entity_id
                    
                    logger.warning(f"LLM selected entity ID {selected_entity_id} not found in retrieved entities")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse direct LLM response as JSON: {e}")
        
        except Exception as e:
            logger.error(f"Error in LLM entity selection: {e}")
        
        # Fallback to first entity if LLM approach fails
        logger.info("Falling back to first retrieved entity")
        if retrieved_entities:
            return retrieved_entities[0]["uri"]
            
        return None        

    def __call__(self, state: FROGGraphRAGState) -> FROGGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Update verbalization object based on knowledge source
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        if hasattr(self, 'verbalization'):
            self.verbalization.set_knowledge_source(knowledge_source)
        else:
            # Create verbalization if it doesn't exist
            self.verbalization = WikidataVerbalization(
                model_name="jinaai/jina-embeddings-v3",
                query_model_encode_kwargs={
                    "task": "retrieval.query",
                    "prompt_name": "retrieval.query",
                },
                passage_model_encode_kwargs={
                    "task": "retrieval.passage",
                    "prompt_name": "retrieval.passage",
                },
                knowledge_source=knowledge_source
            )
        
        # Use appropriate property retrieval based on knowledge source
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        current_property_retrieval = self.property_factory.get_property_retriever(
            knowledge_source, 
            df_properties=self.property_retrieval.df_properties if knowledge_source == "wikidata" else None
        )
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node", 
                "start",
                {"question": state.translated_question, "entity": state.extracted_entities[0] if state.extracted_entities else None, "knowledge_source": knowledge_source},
                start_time=start_time
            )
        
        if not state.extracted_entities:
            # End timing early since we can't do anything without entities
            end_time = datetime.now()
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Verbalization Node", 
                    "end", 
                    {"error": "No entities extracted"},
                    start_time=start_time,
                    end_time=end_time
                )
            state.next = "sparql_generation"
            return state
        
        entity = state.extracted_entities[0]
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        retrieved_resources, err = self.get_entities(entity, k=5, source=knowledge_source)
        
        # Log retrieved resources
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node",
                "retrieved resources",
                {"entity": entity, "resources": retrieved_resources}
            )            
        if state.verbose > 0:
            print(f"Retrieved Resources: {retrieved_resources}")
            
        # Start entity URI selection timing
        uri_start_time = datetime.now()
        
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node",
                "entity URI selection start",
                {"entity": entity, "num_candidates": len(retrieved_resources)},
                start_time=uri_start_time
            )
            
        entity_uri = self.get_most_appropriate_entity_uri(entity, state.translated_question, retrieved_resources, knowledge_source)
        state.entity_uri = entity_uri

        entity_label = "no label found"
        for resource in retrieved_resources:
            if resource.get('uri') == entity_uri:
                entity_label = resource.get('label')
                break
        
        # End entity URI selection timing
        uri_end_time = datetime.now()
        
        # Log entity URI selection
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node",
                "entity URI selection end",
                {"selected_entity_uri": f"{entity_uri} - {entity_label}", "knowledge_source": knowledge_source},
                start_time=uri_start_time,
                end_time=uri_end_time
            )
        
        if entity_uri:
            if state.verbose > 0:
                print(f"Selected Entity URI: {entity_uri}")
                
            try:
                # Start verbalization timing
                verb_start_time = datetime.now()                
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "verbalization start",
                        {"entity_uri": f"{entity_uri} - {entity_label}"},
                        start_time=verb_start_time
                    )
                
                # Create a debug callback function to send progress to the visualizer
                debug_callback = None
                if hasattr(state, 'visualizer') and state.visualizer:
                    debug_callback = lambda msg: state.visualizer.log_event(
                        "Verbalization Node",
                        "encoding progress",
                        {"progress": msg}
                    )
                
                # Get candidates - do this ONCE only
                candidates, po, sp = self.verbalization.get_list_of_candidates(
                    entity_uri=entity_uri, 
                    entity_label=entity_label,
                    property_retrieval=current_property_retrieval,
                    visualizer=state.visualizer if hasattr(state, 'visualizer') else None
                )
                
                # Only continue if we have candidates
                if not candidates:
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "Verbalization Node", 
                            "verbalization failed",
                            {"error": "No candidate properties found"}
                        )
                    state.next = "sparql_generation"
                    end_time = datetime.now()
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "Verbalization Node", 
                            "end",
                            None,
                            start_time=start_time,
                            end_time=end_time
                        )
                    return state
                
                # ----- COMPUTE EMBEDDINGS ONCE -----
                
                # Prepare for computing similarities - just once
                cands = list(candidates.values())
                if debug_callback:
                    debug_callback(f"Computing embeddings for similarity ranking...")
                
                # Encode question once
                question_embed = self.verbalization.encode_with_progress(
                    [state.translated_question], 
                    debug_callback=debug_callback,
                    **self.verbalization.query_model_encode_kwargs
                )[0]
                
                # Encode all candidates once
                passages_embed = self.verbalization.encode_with_progress(
                    cands, 
                    debug_callback=debug_callback,
                    **self.verbalization.passage_model_encode_kwargs
                )
                
                # Compute similarities once
                similarities = self.verbalization.model.similarity(
                    question_embed, 
                    passages_embed
                ).numpy().flatten()
                
                # Log top 5 candidates with similarities
                if hasattr(state, 'visualizer') and state.visualizer:
                    # Get top 5 by similarity
                    top_indices = np.argsort(similarities)[::-1][:5]
                    top_cands = []
                    
                    for i in top_indices:
                        prop_key = list(candidates.keys())[i]
                        top_cands.append((prop_key, cands[i], similarities[i]))
                    
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "top properties by similarity",
                        [f"{idx+1}. Property: {p.split('/')[-1]}, Sentence: {s}, Similarity: {sim:.4f}" 
                         for idx, (p, s, sim) in enumerate(top_cands)]
                    )
                
                # Get the best property
                best_index = np.argmax(similarities)
                similarity = float(max(similarities))
                best_property = list(candidates.keys())[best_index]
                
                # Extract results for this property
                result = self.verbalization.extract_results_for_property(
                    best_property, 
                    po, 
                    sp, 
                    output_uri=state.output_uri
                )
                
                # Get references if needed
                references = []
                if (getattr(state, 'include_references', True) and 
                    similarity >= 0.6 and result and
                    knowledge_source == 'wikidata'):
                    # Only get references for Wikidata, not curriculum
                    logger.info(f"Fetching references for property {best_property} with similarity {similarity}")
                    raw_references = self.verbalization.get_references_for_property(entity_uri, best_property, knowledge_source)
                    
                    # Format the references with proper date formatting
                    for ref in raw_references:
                        formatted_ref = {}
                        if ref.get('refUrl'):
                            formatted_ref['refUrl'] = ref['refUrl']
                        if ref.get('refDate'):
                            formatted_ref['refDate'] = ref['refDate']
                            formatted_ref['formattedRefDate'] = format_reference_date(ref['refDate'])
                        
                        if formatted_ref:  # Only add if we have some reference data
                            references.append(formatted_ref)
                
                # Store results in state
                state.verbalization_result = result
                state.verbalization_similarity = similarity
                
                # Store references in state
                if references:
                    state.verbalization_references = references
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "Verbalization Node",
                            "references fetched",
                            {
                                "reference_count": len(references),
                                "sample_references": references[:3] if len(references) > 3 else references
                            }
                        )
                
                # End verbalization timing
                verb_end_time = datetime.now()
                
                # Log verbalization results
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "verbalization result",
                        {
                            "similarity": similarity,
                            "result": result[0] if result else None,
                            "references_available": len(references) > 0 if references else False
                        },
                        start_time=verb_start_time,
                        end_time=verb_end_time
                    )
                    
                if state.verbose > 0:
                    print(f"Verbalization Result: {result}\nSimilarity: {similarity}")
                    if references:
                        print(f"References found: {len(references)}")
                    
                # Determine if verbalization is successful
                if similarity >= 0.6 and result:
                    state.query_result = result
                    
                    # Process the results for the answer, including references
                    context_str = f'The answer to "{state.question}" is: '
                    for c in result[:50]:
                        for k, v in c.items():
                            context_str += f"{k}={v}, "
                    context_str = context_str[:-2] + "."
                    
                    # Add reference information to context if available
                    if references:
                        context_str += "\n\n**Reference sources:**"
                        unique_refs = set()
                        formatted_dates = set()
                        
                        for ref in references:
                            if ref.get('refUrl'):
                                unique_refs.add(ref['refUrl'])
                            if ref.get('formattedRefDate'):
                                formatted_dates.add(ref['formattedRefDate'])
                        
                        for ref_url in unique_refs:
                            context_str += f"\n- Source: {ref_url}"
                        
                        for date in formatted_dates:
                            context_str += f"\n- Retrieved on: {date}"
                    
                    state.context_str = context_str
                    state.next = "answer_generation"
                    
                    # Mark that verbalization was used successfully
                    state.approach_used = "verbalization"                    
                    # Log success
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "Verbalization Node",
                            "verbalization success",
                            {"similarity": similarity, "next": "answer_generation"}
                        )
                    
                    # Skip to end timing
                    end_time = datetime.now()
                    
                    # Log completion
                    if hasattr(state, 'visualizer') and state.visualizer:
                        state.visualizer.log_event(
                            "Verbalization Node", 
                            "end", 
                            None,
                            start_time=start_time,
                            end_time=end_time
                        )
                        
                    return state
                
                # Log verbalization not sufficient
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "verbalization insufficient",
                        {"similarity": similarity, "threshold": 0.6, "next": "sparql_generation"}
                    )
                
            except Exception as e:
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "verbalization error",
                        {"error": str(e)}
                    )
                    
                if state.verbose > 0:
                    print(f"Verbalization error: {e}")
        
        # Fallback to SPARQL
        state.next = "sparql_generation"
        
        # Log fallback
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node",
                "falling back to SPARQL",
                {"reason": "No entity URI" if not entity_uri else "Verbalization failed or insufficient"}
            )        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state