# backend/agent/langgraph/nodes/verbalization.py (further refactored)
from datetime import datetime
import re
import json
import logging
from SPARQLWrapper import SPARQLWrapper, JSON
from sentence_transformers import SentenceTransformer
import numpy as np
from ..utils.state import WikidataGraphRAGState
from ..utils.date_utils import format_reference_date
import google.generativeai as genai

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
    
    # Wikidata templates
    WIKIDATA_PO_TEMPLATE = """
SELECT distinct ?p ?o ?oLabel
WHERE {{
  BIND(wd:{entity} AS ?s) .
  
  ?s ?p ?o .
  FILTER(?p != wd:P18)
  FILTER NOT EXISTS {{ ?o a ontolex:LexicalSense }}
  ?prop wikibase:directClaim ?p .
  OPTIONAL {{
    ?o rdfs:label ?oLabel .
    FILTER (LANG(?oLabel) = "en")
  }}
}} LIMIT 1000
"""
    WIKIDATA_SP_TEMPLATE = """
SELECT ?s ?sLabel ?p
WHERE {{
  BIND(wd:{entity} AS ?o) .
  
  ?s ?p ?o .
  FILTER NOT EXISTS {{ ?s a ontolex:LexicalSense }}
  ?prop wikibase:directClaim ?p .
  OPTIONAL {{
    ?s rdfs:label ?sLabel .
    FILTER (LANG(?sLabel) = "en")
  }}
}} LIMIT 1000
"""
    
    # Curriculum templates
    CURRICULUM_PO_TEMPLATE = """
SELECT distinct ?p ?o ?pLabel ?oLabel
WHERE {{
  <{entity}> ?p ?o .
  OPTIONAL {{
    ?p rdfs:label ?pLabel .
  }}
  OPTIONAL {{
    ?o rdfs:label ?oLabel .
  }}
}} LIMIT 1000
"""
    CURRICULUM_SP_TEMPLATE = """
SELECT ?s ?p ?sLabel ?pLabel
WHERE {{
  ?s ?p <{entity}> .
  OPTIONAL {{
    ?s rdfs:label ?sLabel .
  }}
  OPTIONAL {{
    ?p rdfs:label ?pLabel .
  }}
}} LIMIT 1000
"""

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
        
        # Set up SPARQL endpoint based on source
        if knowledge_source == "curriculum":
            self.api = SPARQLWrapper("http://localhost:3030/curi/query")
            self.PO_TEMPLATE = self.CURRICULUM_PO_TEMPLATE
            self.SP_TEMPLATE = self.CURRICULUM_SP_TEMPLATE
        else:
            self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
            self.PO_TEMPLATE = self.WIKIDATA_PO_TEMPLATE
            self.SP_TEMPLATE = self.WIKIDATA_SP_TEMPLATE
            
        self.api.setReturnFormat(JSON)
        # Set a user agent to be respectful
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        logger.info(f"Initialized WikidataVerbalization with model: {model_name} for source: {knowledge_source}")
    
    def set_knowledge_source(self, knowledge_source):
        """Update the knowledge source and reconfigure templates and endpoint"""
        if knowledge_source != self.knowledge_source:
            self.knowledge_source = knowledge_source
            
            if knowledge_source == "curriculum":
                self.api = SPARQLWrapper("http://localhost:3030/curi/query")
                self.PO_TEMPLATE = self.CURRICULUM_PO_TEMPLATE
                self.SP_TEMPLATE = self.CURRICULUM_SP_TEMPLATE
            else:
                self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
                self.PO_TEMPLATE = self.WIKIDATA_PO_TEMPLATE
                self.SP_TEMPLATE = self.WIKIDATA_SP_TEMPLATE
                
            self.api.setReturnFormat(JSON)
            self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
            logger.info(f"Updated WikidataVerbalization to use source: {knowledge_source}")

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
            logger.error(f"Error executing SPARQL query: {e}")
            return [], e

    def get_po(self, entity: str, visualizer=None):
        """Get predicate-object pairs for entity"""
        query = self.PO_TEMPLATE.format(entity=entity)
        
        # Log before executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_po SPARQL execution start",
                {"entity": entity, "query_preview": query[:200] + "..."}
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
        query = self.SP_TEMPLATE.format(entity=entity)
        
        # Log before executing SPARQL
        if visualizer:
            visualizer.log_event(
                "Verbalization Node",
                "get_sp SPARQL execution start",
                {"entity": entity, "query_preview": query[:200] + "..."}
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
            
            # For Wikidata, try to get property label from property_retrieval if pLabel not available
            if not pLabel and property_retrieval and self.knowledge_source == "wikidata":
                prop_id = p.split('/')[-1]  # Extract property ID like P27 from URI
                pLabel = property_retrieval.property_id_to_label.get(prop_id)
            
            # Fallback to camelCase separation if no label found
            if not pLabel:
                pLabel = separate_camel_case(p.split("/")[-1])
            
            label_s = sLabel if sLabel else replace_using_dict(entity_uri.split("/")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel

            if label_p != curr_p:
                curr_p = label_p
                if o.startswith("http"):
                    label_o = oLabel if oLabel else replace_using_dict(o.split("/")[-1], self.MANUAL_MAPPING_DICT)
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
            
            # For Wikidata, try to get property label from property_retrieval if pLabel not available
            if not pLabel and property_retrieval and self.knowledge_source == "wikidata":
                prop_id = p.split('/')[-1]  # Extract property ID like P27 from URI
                pLabel = property_retrieval.property_id_to_label.get(prop_id)
            
            # Fallback to camelCase separation if no label found
            if not pLabel:
                pLabel = separate_camel_case(p.split("/")[-1])
            
            label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel
            label_o = oLabel if oLabel else replace_using_dict(entity_uri.split("/")[-1], self.MANUAL_MAPPING_DICT)

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

    def get_references_for_property(self, entity: str, property_uri: str):
        """Get reference information for a specific entity and property"""
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
                label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1])
                
                if o.startswith("http"):
                    label_o = oLabel if oLabel else replace_using_dict(o.split("/")[-1], self.MANUAL_MAPPING_DICT)
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
                label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1])
                label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1], self.MANUAL_MAPPING_DICT)
                result.append({label_p: s if output_uri else label_s})
                
        return result


class VerbalizationNode:
    """Node for retrieving entity information through verbalization"""
    def __init__(self, genai_model=None, llm_factory=None, property_retrieval=None):
        """
        Initialize VerbalizationNode
        
        Args:
            genai_model: Legacy Gemini model (for backward compatibility)
            llm_factory: LLM factory instance for multi-provider support
            property_retrieval: Property retrieval system for getting property labels
        """
        self.genai_model = genai_model
        self.llm_factory = llm_factory
        self.property_retrieval = property_retrieval
        self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.api.setReturnFormat(JSON)
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        
        # Initialize the LLM provider
        self._llm_provider = None
        if self.llm_factory:
            try:
                self._llm_provider = self.llm_factory.get_model_for_verbalization()
                logger.info("Initialized VerbalizationNode with LLM factory")
            except Exception as e:
                logger.error(f"Failed to get model from factory: {e}")
                logger.warning("Falling back to legacy Gemini model")
                self._llm_provider = None
        
        if not self._llm_provider and not self.genai_model:
            raise ValueError("Either llm_factory or genai_model must be provided")
        
        logger.info("Initialized VerbalizationNode")        
    
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
            logger.error(f"Error executing SPARQL query: {e}")
            return [], e
        
    def get_entities(self, entity: str, k: int = 5, source: str = "wikidata"):
        """Search for entities in Wikidata or Curriculum"""
        if source == "curriculum":
            # Try to use UniversityEntityRetrieval if it exists
            try:
                from ..utils.entity_retrieval import UniversityEntityRetrieval
                entity_retrieval = UniversityEntityRetrieval()
                result = entity_retrieval.get_related_entities(entity, [entity], k=k)
                return result.get("entities", []), None
            except Exception as e:
                logger.error(f"Error using UniversityEntityRetrieval: {e}")
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

    def get_most_appropriate_entity_uri(self, entity, question, retrieved_entities):
        """Get the most appropriate Wikidata entity ID from retrieved entities"""
        if not retrieved_entities:
            return None
        
        # Simple scoring function based on text similarity
        def score_entity(entity_data):
            # Base score - higher is better
            score = 0
            
            # Check if the entity label matches the entity name exactly
            label = entity_data.get("label", "").lower()
            if label == entity.lower():
                score += 10
            elif entity.lower() in label:
                score += 5
            
            # Check if description mentions relevant terms from the question
            description = entity_data.get("description", "")
            if description:  # Only process description if it exists
                description = description.lower()
                question_words = question.lower().split()
                relevant_words = [w for w in question_words if len(w) > 3 and w.lower() not in ["what", "where", "when", "who", "how", "the", "and", "for", "that"]]
                
                for word in relevant_words:
                    if word in description:
                        score += 2
            
            return score
        
        # Score and rank entities
        scored_entities = [(entity_data, score_entity(entity_data)) for entity_data in retrieved_entities]
        scored_entities.sort(key=lambda x: x[1], reverse=True)
        
        # Return the highest scoring entity
        if scored_entities:
            return scored_entities[0][0]["uri"]
        
        # Fallback to first entity if available
        if retrieved_entities:
            return retrieved_entities[0]["uri"]
            
        return None        

    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
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
            
        entity_uri = self.get_most_appropriate_entity_uri(entity, state.translated_question, retrieved_resources)
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
                    property_retrieval=self.property_retrieval,
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
                    getattr(state, 'knowledge_source', 'wikidata') == 'wikidata'):
                    # Only get references for Wikidata, not curriculum
                    logger.info(f"Fetching references for property {best_property} with similarity {similarity}")
                    raw_references = self.verbalization.get_references_for_property(entity_uri, best_property)
                    
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