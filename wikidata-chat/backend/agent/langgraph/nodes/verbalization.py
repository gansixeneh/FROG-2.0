# backend/agent/langgraph/nodes/verbalization.py
from datetime import datetime
import re
import json
import logging
from SPARQLWrapper import SPARQLWrapper, JSON
from sentence_transformers import SentenceTransformer
import numpy as np
from ..utils.state import WikidataGraphRAGState
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
    PO_TEMPLATE = """
SELECT distinct ?p ?o ?sLabel ?propLabel ?oLabel
WHERE {{
  BIND(wd:{entity} AS ?s) .
  
  ?s ?p ?o .
  FILTER(?p != wd:P18)
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  ?prop wikibase:directClaim ?p .
}}
"""
    SP_TEMPLATE = """
SELECT ?s ?p ?sLabel ?propLabel ?oLabel
WHERE {{
  BIND(wd:{entity} AS ?o) .
  
  ?s ?p ?o .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
  ?prop wikibase:directClaim ?p .
}}
"""

    def __init__(
        self,
        model_name="jinaai/jina-embeddings-v3",
        model_kwargs={"trust_remote_code": True},
        query_model_encode_kwargs={},
        passage_model_encode_kwargs={},
    ) -> None:
        self.model_name = model_name
        self.query_model_encode_kwargs = query_model_encode_kwargs
        self.passage_model_encode_kwargs = passage_model_encode_kwargs
        # Use the singleton instead of creating a new instance
        self.model = get_sentence_transformer(model_name, **model_kwargs)
        self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.api.setReturnFormat(JSON)
        # Set a user agent to be respectful
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        logger.info(f"Initialized WikidataVerbalization with model: {model_name}")

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
    def get_po(self, entity: str):
        """Get predicate-object pairs for entity"""
        query = self.PO_TEMPLATE.format(entity=entity)
        results, err = self.execute_sparql(query)
        if not results or err:
            return []
        
        df = []
        for result in results:
            df.append(result)
        return df

    def get_sp(self, entity: str):
        """Get subject-predicate pairs for entity"""
        query = self.SP_TEMPLATE.format(entity=entity)
        results, err = self.execute_sparql(query)
        if not results or err:
            return []
        
        df = []
        for result in results:
            df.append(result)
        return df

    def get_list_of_candidates(self, entity: str):
        """Get candidates for verbalization"""
        po, sp = self.get_po(entity), self.get_sp(entity)
        candidates = dict()

        # Process predicate-object pairs
        curr_p = None
        for result in po:
            p = result.get('p', '')
            o = result.get('o', '')
            sLabel = result.get('sLabel', '')
            pLabel = result.get('propLabel', '')
            oLabel = result.get('oLabel', '')
            
            label_s = sLabel if sLabel else replace_using_dict(entity.split("/")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1])

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
            pLabel = result.get('propLabel', '')
            oLabel = result.get('oLabel', '')
            
            label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1], self.MANUAL_MAPPING_DICT)
            label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1])
            label_o = oLabel if oLabel else replace_using_dict(entity.split("/")[-1], self.MANUAL_MAPPING_DICT)

            if label_p != curr_p:
                curr_p = label_p
                candidates[p] = self.SENTENCE_TEMPLATE.format(
                    s=str(label_s), p=str(label_p), o=str(label_o)
                )

        return candidates, po, sp

    def run(self, question: str, entity: str, output_uri=False):
        """Run the verbalization process"""
        # Get candidate sentences
        candidates, po, sp = self.get_list_of_candidates(entity)
        cands = list(candidates.values())
        if not cands:  # Handle empty candidates
            return [], 0.0
            
        # Encode question and candidates
        question_embed = self.model.encode(question, **self.query_model_encode_kwargs)
        passages_embed = self.model.encode(cands, **self.passage_model_encode_kwargs)

        # Find most similar candidate
        similarities = self.model.similarity(question_embed, passages_embed).numpy().flatten()
        similar_index = np.argmax(similarities)
        similar_score = float(max(similarities))

        # Extract results based on the most similar property
        property_used = list(candidates.keys())[similar_index]
        result = []        
        # Add predicate-object pairs
        for p_result in po:
            p = p_result.get('p', '')
            o = p_result.get('o', '')
            pLabel = p_result.get('propLabel', '')
            oLabel = p_result.get('oLabel', '')
            
            if p == property_used:
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
            pLabel = s_result.get('propLabel', '')
            
            if p == property_used:
                label_p = pLabel if pLabel else separate_camel_case(p.split("/")[-1])
                label_s = sLabel if sLabel else replace_using_dict(s.split("/")[-1], self.MANUAL_MAPPING_DICT)
                result.append({label_p: s if output_uri else label_s})
            
        return result, similar_score

class VerbalizationNode:
    """Node for retrieving entity information through verbalization"""
    def __init__(self, genai_model):
        self.genai_model = genai_model
        self.api = SPARQLWrapper("https://query.wikidata.org/sparql")
        self.api.setReturnFormat(JSON)
        self.api.addCustomHttpHeader("User-Agent", "FROG Wikidata Agent/1.0")
        
        # Create WikidataVerbalization with optimized parameters
        # Uses singleton model under the hood
        self.verbalization = WikidataVerbalization(
            model_name="jinaai/jina-embeddings-v3",
            query_model_encode_kwargs={
                "task": "retrieval.query",
                "prompt_name": "retrieval.query",
            },
            passage_model_encode_kwargs={
                "task": "retrieval.passage",
                "prompt_name": "retrieval.passage",
            }
        )
        logger.info("Initialized VerbalizationNode with WikidataVerbalization")        
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
            logger.error(f"Error searching for entities: {e}")
            return [], e        
    def get_most_appropriate_entity_uri(self, entity, question, retrieved_entities):
        """Get the most appropriate Wikidata entity ID from retrieved entities"""
        if not retrieved_entities:
            return None
        
        prompt = f"""Find the most appropriate Wikidata entity ID for "{entity}" to answer the question: "{question}".
Here are the retrieved entities:
{json.dumps(retrieved_entities, indent=2)}

Return ONLY the entity ID (e.g., Q123) and nothing else.
"""
        
        try:
            response = self.genai_model.generate_content(prompt)
            # Extract just the entity ID using regex
            match = re.search(r'(?:^|\s)(Q\d+)(?:$|\s)', response.text)
            if match:
                return match.group(1)
            return retrieved_entities[0]["uri"]  # Fallback to first entity
        except Exception as e:
            logger.error(f"Error identifying entity URI: {e}")
            if retrieved_entities:
                return retrieved_entities[0]["uri"]  # Fallback to first entity
            return None        
    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Verbalization Node", 
                "start",
                {"question": state.translated_question, "entity": state.extracted_entities[0] if state.extracted_entities else None},
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
        retrieved_resources, err = self.get_entities(entity, k=5)
        
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
                {"selected_entity_uri": f"{entity_uri} - {entity_label}"},
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
                    
                # Get all candidates for visualization
                candidates, po, sp = self.verbalization.get_list_of_candidates(entity_uri)
                
                if hasattr(state, 'visualizer') and state.visualizer:
                    # Get top 5 candidates with similarities
                    question_embed = self.verbalization.model.encode(
                        state.translated_question, 
                        **self.verbalization.query_model_encode_kwargs
                    )
                    cands = list(candidates.values())
                    
                    if cands:
                        passages_embed = self.verbalization.model.encode(
                            cands, 
                            **self.verbalization.passage_model_encode_kwargs
                        )
                        
                        similarities = self.verbalization.model.similarity(
                            question_embed, 
                            passages_embed
                        ).numpy().flatten()
                        
                        # Sort by similarity and get top 5
                        top_cands = []
                        for i in range(len(cands)):
                            prop_key = list(candidates.keys())[i]
                            top_cands.append((prop_key, cands[i], similarities[i]))
                            
                        top_cands.sort(key=lambda x: x[2], reverse=True)
                        top_cands = top_cands[:5]
                        
                        state.visualizer.log_event(
                            "Verbalization Node",
                            "top properties by similarity",
                            [f"{i+1}. Property: {p.split('/')[-1]}, Sentence: {s}, Similarity: {sim:.4f}" 
                             for i, (p, s, sim) in enumerate(top_cands)]
                        )                
                # Run verbalization
                result, similarity = self.verbalization.run(
                    state.translated_question, 
                    entity_uri, 
                    output_uri=state.output_uri
                )
                
                state.verbalization_result = result
                state.verbalization_similarity = similarity
                
                # End verbalization timing
                verb_end_time = datetime.now()
                
                # Log verbalization results
                if hasattr(state, 'visualizer') and state.visualizer:
                    state.visualizer.log_event(
                        "Verbalization Node",
                        "verbalization result",
                        {
                            "similarity": similarity,
                            "result": result[0] if result else None
                        },
                        start_time=verb_start_time,
                        end_time=verb_end_time
                    )
                    
                if state.verbose > 0:
                    print(f"Verbalization Result: {result}\nSimilarity: {similarity}")
                    
                # Determine if verbalization is successful
                if similarity >= 0.6 and result:
                    state.query_result = result
                    
                    # Process the results for the answer
                    context_str = f'The answer to "{state.question}" is: '
                    for c in result[:50]:
                        for k, v in c.items():
                            context_str += f"{k}={v}, "
                    context_str = context_str[:-2] + "."
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