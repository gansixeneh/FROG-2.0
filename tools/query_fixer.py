# tools/query_fixer.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, Dict, Any
import google.generativeai as genai
from config import GEMINI_API_KEY
from tools.base import WikidataBaseTool

class QueryFixerInput(BaseModel):
    query: str = Field(..., description="The original SPARQL query that failed")
    error: str = Field(..., description="The error message from the SPARQL endpoint")

class QueryFixerTool(WikidataBaseTool):
    name: ClassVar[str] = "query_fixer_tool"
    description: ClassVar[str] = "Fix SPARQL query errors based on error messages from the SPARQL endpoint."
    
    _model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.0-pro")
    
    def _run(self, input_data: QueryFixerInput) -> Dict[str, Any]:
        """
        Fix a SPARQL query based on the error message.
        
        Parameters:
        -----------
        input_data : QueryFixerInput
            The original query and error message
            
        Returns:
        --------
        Dict[str, Any]
            The fixed query or error information
        """
        original_query = input_data.query
        error_message = input_data.error
        
        self._logger.info(f"Attempting to fix query with error: {error_message}")
        
        # Prompt for the model
        prompt = f"""
        You are a SPARQL query fixer. Fix the following SPARQL query for Wikidata that resulted in an error.
        
        Original Query:
        ```sparql
        {original_query}
        ```
        
        Error Message:
        ```
        {error_message}
        ```
        
        Please provide only the fixed SPARQL query without any explanations or additional text.
        Make sure the query follows Wikidata's SPARQL syntax and conventions.
        """
        
        try:
            # Generate the fixed query
            response = self._model.generate_content(prompt)
            fixed_query = response.text.strip()
            
            # Remove any markdown code blocks if present
            if fixed_query.startswith("```sparql"):
                fixed_query = fixed_query.replace("```sparql", "").replace("```", "").strip()
            elif fixed_query.startswith("```"):
                fixed_query = fixed_query.replace("```", "").strip()
            
            self._logger.info(f"Fixed query: {fixed_query}")
            
            return {
                "success": True,
                "original_query": original_query,
                "fixed_query": fixed_query,
                "error_message": error_message
            }
            
        except Exception as e:
            self._logger.error(f"Error in query fixing: {e}")
            return {
                "success": False,
                "original_query": original_query,
                "error": str(e),
                "error_message": error_message
            }