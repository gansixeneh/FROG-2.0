# tools/answer_generation.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY
from tools.base import WikidataBaseTool

class AnswerGenerationInput(BaseModel):
    question: str = Field(..., description="The user's question")
    query_results: List[Dict[str, Any]] = Field(..., description="The results from SPARQL query execution")
    sparql_query: Optional[str] = Field(None, description="The SPARQL query used (optional)")
    entities: Optional[List[Dict[str, Any]]] = Field(None, description="The linked entities (optional)")

class AnswerGenerationTool(WikidataBaseTool):
    name: ClassVar[str] = "answer_generation_tool"
    description: ClassVar[str] = "Convert the raw SPARQL query result into a natural language answer."
    
    _model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.0-pro")
    
    def _run(self, input_data: AnswerGenerationInput) -> Dict[str, Any]:
        """
        Generate a natural language answer from query results.
        
        Parameters:
        -----------
        input_data : AnswerGenerationInput
            The user's question, query results, and optional query and entities
            
        Returns:
        --------
        Dict[str, Any]
            The generated answer and related information
        """
        question = input_data.question
        query_results = input_data.query_results
        sparql_query = input_data.sparql_query
        entities = input_data.entities or []
        
        # Check if we have results
        if not query_results:
            return self._generate_no_results_answer(question, entities)
        
        # Format results for the prompt
        results_text = self._format_results(query_results)
        
        # Create the prompt
        prompt = f"""
        Based on the following data from Wikidata, please answer this question:
        
        Question: {question}
        
        Data from Wikidata:
        {results_text}
        
        Please provide a clear, concise answer in natural language. Focus on directly answering the question.
        If the data doesn't contain a clear answer, acknowledge this and explain what information is available.
        """
        
        try:
            # Generate the answer
            response = self._model.generate_content(prompt)
            answer = response.text.strip()
            
            result = {
                "answer": answer,
                "original_question": question,
                "has_results": True,
                "result_count": len(query_results)
            }
            
            self._log_input_output(input_data, result)
            return result
            
        except Exception as e:
            self._logger.error(f"Error generating answer: {e}")
            return {
                "answer": f"I encountered an error while generating your answer: {str(e)}",
                "original_question": question,
                "has_results": True,
                "result_count": len(query_results),
                "error": str(e)
            }
    
    def _format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format results as a string for the prompt."""
        if not results:
            return "No results found."
        
        # Get all columns from the first result
        columns = list(results[0].keys())
        
        # Build a table-like representation
        formatted_results = []
        for i, result in enumerate(results[:10]):  # Limit to 10 results for readability
            formatted_result = f"Result {i+1}:"
            for col in columns:
                value = result.get(col, "")
                formatted_result += f"\n  {col}: {value}"
            formatted_results.append(formatted_result)
        
        # Add a note if there are more results
        if len(results) > 10:
            formatted_results.append(f"\n(Showing 10 of {len(results)} results)")
        
        return "\n\n".join(formatted_results)
    
    def _generate_no_results_answer(self, question: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate an answer when no results are found."""
        entity_text = ", ".join([e.get("label", e.get("entity_id", "")) for e in entities])
        
        prompt = f"""
        I need to answer this question: "{question}"
        
        I searched for information about {entity_text if entities else "relevant entities"} in Wikidata,
        but couldn't find any results. Please generate a polite response explaining that no information
        was found in Wikidata to answer this question.
        """
        
        try:
            response = self._model.generate_content(prompt)
            answer = response.text.strip()
            
            return {
                "answer": answer,
                "original_question": question,
                "has_results": False,
                "entities": entities
            }
            
        except Exception as e:
            self._logger.error(f"Error generating no-results answer: {e}")
            return {
                "answer": "I couldn't find any information in Wikidata to answer your question.",
                "original_question": question,
                "has_results": False,
                "entities": entities
            }