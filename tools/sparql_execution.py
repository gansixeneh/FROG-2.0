from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, Dict, Any, Union
from utils.sparql_utils import QueryEngine
from tools.base import WikidataBaseTool

class SPARQLExecutionInput(BaseModel):
    query: str = Field(..., description="The SPARQL query to execute")

class SPARQLExecutionTool(WikidataBaseTool):
    name: ClassVar[str] = "sparql_execution_tool"
    description: ClassVar[str] = "Execute SPARQL queries against the Wikidata endpoint."
    
    _query_engine = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._query_engine = QueryEngine()
    
    def _run(self, input_data: SPARQLExecutionInput) -> Union[Dict[str, Any], Any]:
        """
        Execute a SPARQL query and return the results.
        
        Parameters:
        -----------
        input_data : SPARQLExecutionInput
            The SPARQL query to execute
            
        Returns:
        --------
        Union[Dict[str, Any], Any]
            Query results or error information
        """
        query = input_data.query
        
        self._logger.info(f"Executing SPARQL query: {query}")
        result = self._query_engine.run_query(query)
        
        # Check if there was an error
        if isinstance(result, dict) and "error" in result:
            self._logger.error(f"Query execution error: {result['error']}")
            return {
                "success": False,
                "error": result["error"],
                "original_query": query
            }
        
        # Return the successful result
        return {
            "success": True,
            "data": result.to_dict(orient='records') if not result.empty else [],
            "column_names": result.columns.tolist() if not result.empty else [],
            "row_count": len(result) if not result.empty else 0
        }