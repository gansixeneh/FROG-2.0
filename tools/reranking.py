# tools/reranking.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from tools.base import WikidataBaseTool
from sentence_transformers import SentenceTransformer, util
from config import SENTENCE_TRANSFORMER_MODEL

class RerankingInput(BaseModel):
    question: str = Field(..., description="The original user question")
    queries: List[Dict[str, Any]] = Field(..., description="List of candidate queries with their results")

class RerankingTool(WikidataBaseTool):
    name = "reranking_tool"
    description = "Score multiple candidate SPARQL queries to pick the best one."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    
    def _run(self, input_data: RerankingInput) -> Dict[str, Any]:
        """
        Rerank candidate queries based on relevance to question and result quality.
        
        Parameters:
        -----------
        input_data : RerankingInput
            The original question and candidate queries with results
            
        Returns:
        --------
        Dict[str, Any]
            The best ranked query and ranking information
        """
        question = input_data.question
        candidates = input_data.queries
        
        if not candidates:
            return {
                "success": False,
                "error": "No candidate queries provided for reranking",
                "best_query": None
            }
        
        # If only one candidate, return it directly
        if len(candidates) == 1:
            return {
                "success": True,
                "best_query": candidates[0],
                "ranking": [{"index": 0, "score": 1.0}]
            }
        
        # Calculate scores for each candidate
        ranked_candidates = []
        for i, candidate in enumerate(candidates):
            # Extract relevant information
            query = candidate.get("sparql_query", "")
            results = candidate.get("results", [])
            
            # Calculate different score components
            query_relevance = self._calculate_query_relevance(question, query)
            result_quality = self._calculate_result_quality(results)
            
            # Combined score (weight can be adjusted)
            combined_score = 0.7 * query_relevance + 0.3 * result_quality
            
            ranked_candidates.append({
                "index": i,
                "score": combined_score,
                "query_relevance": query_relevance,
                "result_quality": result_quality
            })
        
        # Sort by combined score
        ranked_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Return the best candidate
        best_index = ranked_candidates[0]["index"]
        
        return {
            "success": True,
            "best_query": candidates[best_index],
            "ranking": ranked_candidates
        }
    
    def _calculate_query_relevance(self, question: str, query: str) -> float:
        """Calculate semantic similarity between question and query."""
        try:
            # Clean up the query for better comparison
            cleaned_query = ' '.join(line.strip() for line in query.split('\n'))
            
            # Calculate embeddings and similarity
            embeddings = self.model.encode([question, cleaned_query], convert_to_tensor=True)
            similarity = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
            
            return similarity
        except Exception as e:
            self.logger.error(f"Error calculating query relevance: {e}")
            return 0.5  # Default middle score
    
    def _calculate_result_quality(self, results: List[Dict[str, Any]]) -> float:
        """Calculate result quality based on number of results and completeness."""
        if not results:
            return 0.0
        
        # Simple quality metric based on number of results
        # More sophisticated metrics could consider result diversity, completeness, etc.
        num_results = len(results)
        
        # Normalize: 0 results = 0.0, 1-3 results = 0.6-0.8, 4+ results = 0.9-1.0
        if num_results == 0:
            return 0.0
        elif num_results <= 3:
            return 0.6 + (num_results - 1) * 0.1
        else:
            return min(0.9 + (num_results - 4) * 0.02, 1.0)