from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
import requests
from sentence_transformers import SentenceTransformer, util
import torch
from utils.sparql_utils import QueryEngine
from config import SENTENCE_TRANSFORMER_MODEL, MAX_ENTITY_CANDIDATES
from tools.base import WikidataBaseTool
import google.generativeai as genai
from config import GEMINI_API_KEY

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
        self._query_engine = QueryEngine()
        
        # Initialize Gemini for entity extraction and ranking
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
        
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
        
        # Step 1: Extract possible entities from user's question using LLM
        possible_entities = self._extract_entities(query)
        self._logger.info(f"Extracted entities: {possible_entities}")
        
        if not possible_entities:
            return {"entities": [], "query": query, "error": "No entities identified"}
        
        # Step 2: Retrieve entity candidates from Wikidata for each possible entity
        all_candidates = []
        for entity_name in possible_entities:
            candidates = self._search_wikidata_entities(entity_name)
            all_candidates.extend(candidates)
        
        # Step 3: Enrich top candidates with ontology information
        enriched_candidates = []
        for candidate in all_candidates[:10]:  # Limit to top 10 for efficiency
            ontology = self._get_entity_ontology(candidate['entity_id'])
            candidate['ontology'] = ontology
            enriched_candidates.append(candidate)
        
        # Step 4: Rerank using LLM to get final top 5
        top_entities = self._rerank_with_llm(query, enriched_candidates, limit)
        
        result = {
            "entities": top_entities[:limit],
            "query": query
        }
        
        self._log_input_output(input_data, result)
        return result
            
    def _extract_entities(self, query: str) -> List[str]:
        """
        Extract potential entity mentions from the query using LLM.
        
        Parameters:
        -----------
        query : str
            The user's question
            
        Returns:
        --------
        List[str]
            List of potential entity names
        """
        prompt = f"""
        Extract the main entities from this question that I should search for in Wikidata:
        
        Question: {query}
        
        Return only the entity names as a comma-separated list, with no additional text.
        """
        
        try:
            response = self._model.generate_content(prompt)
            entity_text = response.text.strip()
            entities = [e.strip() for e in entity_text.split(",")]
            return entities
        except Exception as e:
            self._logger.error(f"Error extracting entities: {e}")
            # Fallback: simple extraction based on capitalized words
            words = query.split()
            candidates = [w for w in words if w[0].isupper() and len(w) > 1]
            return candidates or [query]  # Return the whole query if no candidates
    
    def _search_wikidata_entities(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Search for entities in Wikidata by name.
        
        Parameters:
        -----------
        entity_name : str
            The entity name to search for
            
        Returns:
        --------
        List[Dict[str, Any]]
            List of entity candidates
        """
        params = {
            'action': 'wbsearchentities',
            'search': entity_name,
            'language': 'en',
            'format': 'json',
            'limit': 5  # Get top 5 for each entity mention
        }
        
        try:
            # Make API request
            response = requests.get(self._wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract entity information
            candidates = []
            for entity in data.get('search', []):
                candidates.append({
                    'entity_id': entity.get('id', ''),
                    'label': entity.get('label', ''),
                    'description': entity.get('description', ''),
                    'search_term': entity_name
                })
            
            return candidates
            
        except Exception as e:
            self._logger.error(f"Error in Wikidata search: {e}")
            return []
    
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
    
    def _rerank_with_llm(self, question: str, candidates: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Rerank entity candidates using LLM based on relevance to the question.
        
        Parameters:
        -----------
        question : str
            The user's question
        candidates : List[Dict[str, Any]]
            List of entity candidates with ontology information
        limit : int
            Maximum number of entities to return
            
        Returns:
        --------
        List[Dict[str, Any]]
            Reranked entities
        """
        if not candidates:
            return []
        
        # Format candidate entities for LLM prompt
        candidate_descriptions = []
        for i, candidate in enumerate(candidates):
            # Format the ontology information
            types = ", ".join([t.get("label", "") for t in candidate.get("ontology", {}).get("types", [])])
            
            description = (
                f"Entity {i+1}: {candidate['label']}\n"
                f"ID: {candidate['entity_id']}\n"
                f"Description: {candidate.get('description', 'N/A')}\n"
                f"Types: {types or 'N/A'}\n"
            )
            candidate_descriptions.append(description)
        
        # Create the prompt
        prompt = f"""
        Rank these entity candidates based on their relevance to the following question:
        
        Question: {question}
        
        Entity candidates:
        {''.join(candidate_descriptions)}
        
        Return a ranking as a comma-separated list of entity numbers, from most relevant to least relevant.
        For example: "2, 5, 1, 3, 4" means Entity 2 is most relevant, followed by Entity 5, etc.
        """
        
        try:
            # Generate ranking
            response = self._model.generate_content(prompt)
            ranking_text = response.text.strip()
            
            # Parse the ranking
            ranking = []
            for item in ranking_text.replace(" ", "").split(","):
                try:
                    index = int(item) - 1  # Convert to zero-based index
                    if 0 <= index < len(candidates):
                        ranking.append(index)
                except ValueError:
                    continue
            
            # If ranking failed, return candidates in original order
            if not ranking:
                return candidates[:limit]
            
            # Reorder candidates based on ranking
            ranked_candidates = []
            for index in ranking:
                if index < len(candidates):
                    ranked_candidates.append(candidates[index])
            
            # Add any remaining candidates not in the ranking
            for i, candidate in enumerate(candidates):
                if i not in ranking and len(ranked_candidates) < limit:
                    ranked_candidates.append(candidate)
            
            return ranked_candidates[:limit]
            
        except Exception as e:
            self._logger.error(f"Error in LLM ranking: {e}")
            return candidates[:limit]