from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
from tools.base import WikidataBaseTool
from sentence_transformers import SentenceTransformer, util
from config import SENTENCE_TRANSFORMER_MODEL
import google.generativeai as genai
from config import GEMINI_API_KEY

class RerankingInput(BaseModel):
    question: str = Field(..., description="The original user question")
    query_results: List[Dict[str, Any]] = Field(..., description="List of query objects with their results")
    entities: List[Dict[str, Any]] = Field(..., description="The linked entities from the question")

class RerankingTool(WikidataBaseTool):
    name: ClassVar[str] = "reranking_tool"
    description: ClassVar[str] = "Score multiple SPARQL queries and their results to pick the best answer."
    
    _model = PrivateAttr()
    _sentence_model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize sentence transformer for semantic similarity
        self._sentence_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        
        # Initialize Gemini for LLM-based ranking
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
    
    def _run(self, input_data: RerankingInput) -> Dict[str, Any]:
        """
        Rerank queries based on their results and relevance to the question.
        
        Parameters:
        -----------
        input_data : RerankingInput
            The original question, query results, and linked entities
            
        Returns:
        --------
        Dict[str, Any]
            The best ranked query, results, and ranking information
        """
        question = input_data.question
        query_results = input_data.query_results
        entities = input_data.entities
        
        if not query_results:
            return {
                "success": False,
                "error": "No query results provided for reranking",
                "best_result": None
            }
        
        # If only one result, return it directly
        if len(query_results) == 1:
            return {
                "success": True,
                "best_result": query_results[0],
                "ranking": [{"index": 0, "score": 1.0}]
            }
        
        # Step 1: Calculate statistical scores
        ranked_results = []
        for i, result in enumerate(query_results):
            # Extract relevant information
            query = result.get("sparql_query", "")
            explanation = result.get("explanation", "")
            data = result.get("data", [])
            
            # Calculate different score components
            query_relevance = self._calculate_query_relevance(question, query)
            result_quality = self._calculate_result_quality(data)
            
            # Add to ranking list
            ranked_results.append({
                "index": i,
                "result": result,
                "query_relevance": query_relevance,
                "result_quality": result_quality,
                # Preliminary score, will be updated by LLM
                "score": 0.7 * query_relevance + 0.3 * result_quality
            })
        
        # Step 2: Use LLM to evaluate and re-rank the results
        llm_ranked_results = self._llm_ranking(question, query_results, ranked_results)
        
        # Sort by the final score
        llm_ranked_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Get the best result
        best_index = llm_ranked_results[0]["index"]
        best_result = query_results[best_index]
        
        return {
            "success": True,
            "best_result": best_result,
            "ranking": llm_ranked_results
        }
    
    def _calculate_query_relevance(self, question: str, query: str) -> float:
        """Calculate semantic similarity between question and query."""
        try:
            # Clean up the query for better comparison
            cleaned_query = ' '.join(line.strip() for line in query.split('\n'))
            
            # Calculate embeddings and similarity
            embeddings = self._sentence_model.encode([question, cleaned_query], convert_to_tensor=True)
            similarity = float(util.cos_sim(embeddings[0], embeddings[1])[0][0])
            
            return similarity
        except Exception as e:
            self._logger.error(f"Error calculating query relevance: {e}")
            return 0.5  # Default middle score
    
    def _calculate_result_quality(self, results: List[Dict[str, Any]]) -> float:
        """Calculate result quality based on number of results and completeness."""
        if not results:
            return 0.0
        
        # Simple quality metric based on number of results
        num_results = len(results)
        
        # Normalize: 0 results = 0.0, 1-3 results = 0.6-0.8, 4+ results = 0.9-1.0
        if num_results == 0:
            return 0.0
        elif num_results <= 3:
            return 0.6 + (num_results - 1) * 0.1
        else:
            return min(0.9 + (num_results - 4) * 0.02, 1.0)
    
    def _llm_ranking(self, question: str, query_results: List[Dict[str, Any]], 
                    preliminary_ranking: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use LLM to evaluate and rank the query results.
        
        Parameters:
        -----------
        question : str
            The original question
        query_results : List[Dict[str, Any]]
            List of query results to rank
        preliminary_ranking : List[Dict[str, Any]]
            Preliminary ranking based on statistical metrics
            
        Returns:
        --------
        List[Dict[str, Any]]
            Updated ranking with LLM scores
        """
        # Format query results for the prompt
        formatted_results = []
        
        for i, result in enumerate(query_results):
            query = result.get("sparql_query", "Unknown query")
            explanation = result.get("explanation", "No explanation provided")
            data = result.get("data", [])
            
            # Format the data (limit to 5 rows for readability)
            data_str = "No results found."
            if data:
                data_rows = []
                for j, row in enumerate(data[:5]):
                    row_str = f"Row {j+1}: " + ", ".join([f"{k}={v}" for k, v in row.items()])
                    data_rows.append(row_str)
                
                data_str = "\n".join(data_rows)
                if len(data) > 5:
                    data_str += f"\n(... and {len(data) - 5} more rows)"
            
            # Add to formatted results
            formatted_results.append(
                f"QUERY {i+1}:\n"
                f"Explanation: {explanation}\n"
                f"Results: {len(data)} rows found\n"
                f"Sample data:\n{data_str}\n"
                f"Statistical scores: Query relevance = {preliminary_ranking[i]['query_relevance']:.2f}, "
                f"Result quality = {preliminary_ranking[i]['result_quality']:.2f}\n"
            )
        
        formatted_results_str = "\n\n".join(formatted_results)
        
        # Create the prompt
        prompt = f"""
        I need to determine which of the following SPARQL query results best answers this question:
        
        Question: {question}
        
        Query Results:
        {formatted_results_str}
        
        Please analyze each query result and rate them on a scale of 0.0 to 1.0 based on:
        1. Relevance - How directly the result addresses the question
        2. Completeness - Whether the result contains all information needed
        3. Accuracy - Whether the result appears correct based on the data
        4. Overall quality - Your overall assessment of how well it answers the question
        
        For each query, provide a score in this format:
        QUERY 1: score=X.XX
        QUERY 2: score=X.XX
        ... and so on
        
        Then, provide a brief explanation of your ranking decision. Which query provides the best answer and why?
        """
        
        try:
            # Get LLM's evaluation
            response = self._model.generate_content(prompt)
            evaluation_text = response.text.strip()
            
            # Extract scores
            for i in range(len(query_results)):
                score_marker = f"QUERY {i+1}: score="
                if score_marker in evaluation_text:
                    score_text = evaluation_text.split(score_marker)[1].split("\n")[0].strip()
                    try:
                        llm_score = float(score_text)
                        # Update the score in our ranking
                        preliminary_ranking[i]["llm_score"] = llm_score
                        # Combine with statistical score (weighted)
                        preliminary_ranking[i]["score"] = 0.3 * preliminary_ranking[i]["score"] + 0.7 * llm_score
                    except ValueError:
                        self._logger.warning(f"Could not parse LLM score: {score_text}")
            
            # Add explanation to the result
            explanation_parts = evaluation_text.split("explanation", 1)
            if len(explanation_parts) > 1:
                explanation = explanation_parts[1].strip()
                for item in preliminary_ranking:
                    item["ranking_explanation"] = explanation
            
            return preliminary_ranking
            
        except Exception as e:
            self._logger.error(f"Error in LLM ranking: {e}")
            # Fall back to the preliminary ranking
            return preliminary_ranking