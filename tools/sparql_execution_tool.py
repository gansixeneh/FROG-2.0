from langchain.tools import BaseTool
from pydantic import Field
from typing import Any
from query_engine import QueryEngine

class SPARQLExecutionTool(BaseTool):
    name: str = "sparql_execution"
    description: str = "Executes a SPARQL query on Wikidata and returns results or error messages."

    engine: Any = Field(default_factory=QueryEngine)

    def _run(self, query: str) -> str:
        try:
            result = self.engine.run_query(query)
            if result.empty:
                return "No results found."
            return result.to_json(orient="records")
        except Exception as e:
            return f"SPARQL Error: {str(e)}"

    async def _arun(self, query: str) -> Any:
        raise NotImplementedError("Async not supported")
