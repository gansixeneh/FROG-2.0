
# backend/agent/langgraph/nodes/property_generation.py
from datetime import datetime
import re
import logging
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams
from ..utils.state import FROGGraphRAGState
from ..utils.knowledge_graph_metadata import get_knowledge_graph_metadata

# Configure logging
logger = logging.getLogger(__name__)

class PropertyGenerationNode:
    """Node for enhancing and retrieving additional Wikidata properties"""
    def __init__(self, property_retrieval):
        self.property_retrieval = property_retrieval
        
    def __call__(self, state: FROGGraphRAGState) -> FROGGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Get knowledge source and use appropriate property retrieval
        knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
        current_property_retrieval = self.property_retrieval
        
        if knowledge_source == 'curriculum':
            try:
                from ..utils.property_retrieval import UniversityPropertyRetrieval
                current_property_retrieval = UniversityPropertyRetrieval()
                logger.info("Using UniversityPropertyRetrieval for curriculum in PropertyGenerationNode")
            except Exception as e:
                logger.warning(f"Failed to initialize UniversityPropertyRetrieval: {e}")
                logger.info("Falling back to standard property retrieval")
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Property Generation Node", 
                "start",
                {"question": state.translated_question, "initial_properties": state.related_properties, "knowledge_source": knowledge_source},
                start_time=start_time
            )
        
        # If properties were already extracted, use those as a starting point
        initial_properties = state.related_properties if state.related_properties else []
        
        # Get n-gram properties to supplement the extracted properties
        try:
            # First, get n-gram based properties
            ngram_start_time = datetime.now()
            
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Property Generation Node",
                    "n-gram processing start",
                    None,
                    start_time=ngram_start_time
                )
                
            # Tokenize the question for n-grams
            tokenizer = RegexpTokenizer(r"\\w+")
            tokens = tokenizer.tokenize(state.translated_question)
            tokens = [tok.lower() for tok in tokens if tok.lower() not in self.property_retrieval.stopwords]
            
            # Generate n-grams
            max_n = min(len(tokens), 3)
            ngrams_list = []
            for n in range(1, max_n + 1):
                n_grams = ngrams(tokens, n)
                ngrams_list.extend([" ".join(ng) for ng in n_grams])
            
            # Get top 5 n-gram properties
            top_ngram_properties = []
            for ngram in ngrams_list:
                df_res = current_property_retrieval._search(ngram, k=5)
                if not df_res.empty:
                    df_res = df_res[df_res["score"] >= 0.6]
                    if not df_res.empty:
                        # Handle both Wikidata and curriculum property formats
                        if hasattr(current_property_retrieval, 'property_id_to_label'):
                            # Wikidata format
                            df_res["idWithLabel"] = df_res["propertyId"] + " - " + df_res["label"]
                        else:
                            # Curriculum format - use appropriate property ID field
                            prop_id_field = "propertyId" if "propertyId" in df_res.columns else "label"
                            df_res["idWithLabel"] = df_res[prop_id_field] + " - " + df_res["label"]
                        top_ngram_properties.extend(df_res["idWithLabel"].tolist())
                        if len(top_ngram_properties) >= 5:
                            break
            
            top_ngram_properties = list(set(top_ngram_properties))[:5]
            
            # End n-gram timing
            ngram_end_time = datetime.now()
            
            # Log n-gram properties
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Property Generation Node",
                    "n-gram properties",
                    {"top_5_ngram_properties": top_ngram_properties},
                    start_time=ngram_start_time,
                    end_time=ngram_end_time
                )
            
            # Get combined properties
            combined_start_time = datetime.now()
            
            # Log combined start
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Property Generation Node",
                    "combined property retrieval start",
                    {"initial_properties": initial_properties, "ngram_properties": top_ngram_properties[:5]},
                    start_time=combined_start_time
                )
            
            # Get all related properties, combining extracted and n-gram properties
            combined_properties = []
            
            # Process initial properties from entity extraction
            for prop in initial_properties:
                # Add raw property name
                combined_properties.append(prop)
                
                # Add camelCase version if it contains spaces
                if " " in prop:
                    words = prop.lower().split()
                    camel_prop = words[0]
                    for word in words[1:]:
                        camel_prop += word.capitalize()
                    combined_properties.append(camel_prop)
            
            # Get related properties from vector DB
            threshold = 0.6
            related_candidates = current_property_retrieval.get_related_candidates(
                state.translated_question, 
                property_candidates=combined_properties, 
                threshold=threshold
            )
            
            # Update the properties in state
            state.related_properties = related_candidates["properties"]
            
            # End combined timing
            combined_end_time = datetime.now()
            
            # Log combined properties
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Property Generation Node",
                    "final properties",
                    {"final_properties": state.related_properties[:10]},
                    start_time=combined_start_time,
                    end_time=combined_end_time
                )
                
            if state.verbose > 0:
                print(f"Enhanced Properties: {state.related_properties[:10]}")
                
        except Exception as e:
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Property Generation Node",
                    "property generation error",
                    {"error": str(e)}
                )
                
            if state.verbose > 0:
                print(f"Error enhancing properties: {e}")
                
            # Make sure we have at least the initial properties
            if not state.related_properties:
                state.related_properties = initial_properties if initial_properties else state.extracted_entities
        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Property Generation Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state
