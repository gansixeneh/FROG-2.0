# tools/entity_ontology_retrieval.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
import requests
from sentence_transformers import SentenceTransformer, util
import torch
from utils.sparql_utils import QueryEngine
from config import SENTENCE_TRANSFORMER_MODEL, MAX_ENTITY_CANDIDATES
from tools.base import WikidataBaseTool

class EntityOntologyRetrievalInput(BaseModel):
    query: str = Field(..., description="The user's question")
    limit: int = Field(MAX_ENTITY_CANDIDATES, description="Maximum number of entities to retrieve")

class EntityOntologyRetrievalTool(WikidataBaseTool):
    name: ClassVar[str] = "entity_ontology_retrieval_tool"
    description: ClassVar[str] = "Retrieve candidate entities with their ontological context from Wikidata."
    
    _wikidata_api_url = PrivateAttr()
    _model = PrivateAttr()
    _query_engine = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wikidata_api_url = "https://www.wikidata.org/w/api.php"
        self._model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        self._query_engine = QueryEngine()
        
    def _run(self, input_data: EntityOntologyRetrievalInput) -> Dict[str, Any]:
        """
        Retrieve entities with ontological context for a given query.
        
        Parameters:
        -----------
        input_data : EntityOntologyRetrievalInput
            The query to search for and limit of results
            
        Returns:
        --------
        Dict[str, Any]
            List of entity candidates with ontology information
        """
        query = input_data.query
        limit = input_data.limit
        
        # Step 1: API call to Wikidata search
        params = {
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'format': 'json',
            'limit': limit * 2  # Get more candidates for re-ranking
        }
        
        try:
            # Make API request
            response = requests.get(self._wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Step 2: Extract entity information
            candidates = []
            for entity in data.get('search', []):
                candidates.append({
                    'entity_id': entity.get('id', ''),
                    'label': entity.get('label', ''),
                    'description': entity.get('description', ''),
                    'api_score': 1.0,  # Default API score
                    'ontology': {}  # Will be filled later
                })
            
            # Step 3: Re-rank using vector similarity if we have candidates
            if candidates:
                candidates = self._rerank_candidates(query, candidates, limit)
                
                # Step 4: Enrich top candidates with ontology information
                for candidate in candidates[:limit]:
                    ontology = self._get_entity_ontology(candidate['entity_id'])
                    candidate['ontology'] = ontology
            
            result = {
                "entities": candidates[:limit],
                "query": query
            }
            
            self._log_input_output(input_data, result)
            return result
            
        except Exception as e:
            self._logger.error(f"Error in entity retrieval: {e}")
            return {"entities": [], "query": query, "error": str(e)}
    
    def _rerank_candidates(self, query: str, candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Re-rank entity candidates using sentence transformer similarity.
        
        Parameters:
        -----------
        query : str
            The original query
        candidates : List[Dict[str, Any]]
            List of candidate entities
        limit : int
            Maximum number of candidates to return
            
        Returns:
        --------
        List[Dict[str, Any]]
            Re-ranked candidates with similarity scores
        """
        # Prepare texts for encoding
        query_text = query
        candidate_texts = []
        
        for candidate in candidates:
            # Combine label and description for better matching
            text = candidate['label']
            if candidate.get('description'):
                text += f" - {candidate['description']}"
            candidate_texts.append(text)
        
        # Calculate embeddings and similarities
        embeddings = self._model.encode([query_text] + candidate_texts, convert_to_tensor=True)
        query_embedding = embeddings[0]
        candidate_embeddings = embeddings[1:]
        
        # Calculate cosine similarities
        similarities = util.cos_sim(query_embedding, candidate_embeddings)[0]
        
        # Add similarity scores to candidates
        for i, candidate in enumerate(candidates):
            candidate['vector_score'] = float(similarities[i])
            # Combined score (can be weighted if needed)
            candidate['score'] = float(similarities[i])
        
        # Sort by score and limit results
        ranked_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)[:limit]
        
        return ranked_candidates
    
    def _get_entity_ontology(self, entity_id: str) -> Dict[str, Any]:
        """Get ontological information for an entity."""
        ontology = {
            "types": self._get_entity_types(entity_id),
            "superclasses": self._get_entity_superclasses(entity_id),
            "subclasses": self._get_entity_subclasses(entity_id),
        }
        
        # Add derived field for convenience
        ontology["is_class"] = len(ontology["subclasses"]) > 0
        
        return ontology
    
    def _get_entity_types(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the types/classes of the entity."""
        query = f"""
        SELECT ?type ?typeLabel ?typeDescription
        WHERE {{
          wd:{entity_id} wdt:P31 ?type .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 10
        """
        
        results = self._query_engine.run_query(query)
        types = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                type_id = row.get("type", "").split("/")[-1]
                types.append({
                    "type_id": type_id,
                    "label": row.get("typeLabel", ""),
                    "description": row.get("typeDescription", "")
                })
                
        return types
    
    def _get_entity_superclasses(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the superclasses of the entity (if it's a class)."""
        query = f"""
        SELECT ?superclass ?superclassLabel ?superclassDescription
        WHERE {{
          wd:{entity_id} wdt:P279 ?superclass .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 10
        """
        
        results = self._query_engine.run_query(query)
        superclasses = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                superclass_id = row.get("superclass", "").split("/")[-1]
                superclasses.append({
                    "superclass_id": superclass_id,
                    "label": row.get("superclassLabel", ""),
                    "description": row.get("superclassDescription", "")
                })
                
        return superclasses
    
    def _get_entity_subclasses(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the subclasses of the entity (if it's a class)."""
        query = f"""
        SELECT ?subclass ?subclassLabel ?subclassDescription
        WHERE {{
          ?subclass wdt:P279 wd:{entity_id} .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 10
        """
        
        results = self._query_engine.run_query(query)
        subclasses = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                subclass_id = row.get("subclass", "").split("/")[-1]
                subclasses.append({
                    "subclass_id": subclass_id,
                    "label": row.get("subclassLabel", ""),
                    "description": row.get("subclassDescription", "")
                })
                
        return subclasses