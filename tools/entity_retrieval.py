# tools/entity_retrieval.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import torch
from config import SENTENCE_TRANSFORMER_MODEL, MAX_ENTITY_CANDIDATES
from tools.base import WikidataBaseTool

class EntityRetrievalInput(BaseModel):
    query: str = Field(..., description="The entity mention or query to search for")
    limit: int = Field(MAX_ENTITY_CANDIDATES, description="Maximum number of entities to retrieve")

class EntityRetrievalTool(WikidataBaseTool):
    name: str = "entity_retrieval_tool"
    description: str = "Retrieve candidate entities from Wikidata using text search and vector similarity."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wikidata_api_url = "https://www.wikidata.org/w/api.php"
        self.model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        
    def _run(self, input_data: EntityRetrievalInput) -> List[Dict[str, Any]]:
        """
        Run the entity retrieval with the given input.
        
        Parameters:
        -----------
        input_data : EntityRetrievalInput
            The query to search for and limit of results
            
        Returns:
        --------
        List[Dict[str, Any]]
            List of entity candidates with scores
        """
        query = input_data.query
        limit = input_data.limit
        
        # API call to Wikidata search
        params = {
            'action': 'wbsearchentities',
            'search': query,
            'language': 'en',
            'format': 'json',
            'limit': limit * 2  # Get more candidates for re-ranking
        }
        
        try:
            # Make API request
            response = requests.get(self.wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract entity information
            candidates = []
            for entity in data.get('search', []):
                candidates.append({
                    'entity_id': entity.get('id', ''),
                    'label': entity.get('label', ''),
                    'description': entity.get('description', ''),
                    'api_score': 1.0  # Default API score
                })
                
            # Re-rank using vector similarity if we have candidates
            if candidates:
                candidates = self._rerank_candidates(query, candidates, limit)
                
            self._log_input_output(input_data, candidates)
            return candidates
            
        except Exception as e:
            self.logger.error(f"Error in entity retrieval: {e}")
            return []
    
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
        embeddings = self.model.encode([query_text] + candidate_texts, convert_to_tensor=True)
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