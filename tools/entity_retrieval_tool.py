from langchain.tools import BaseTool
from pydantic import Field
from typing import Any
from entity_property_retrieval import EntityPropertyRetrieval

class EntityRetrievalTool(BaseTool):
    name: str = "entity_retrieval"
    description: str = "Retrieves candidate entities from Wikidata using text search."

    retriever: Any = Field(default_factory=EntityPropertyRetrieval)

    def _run(self, query: str) -> Any:
        results_df = self.retriever.search_entities(query)
        return results_df.to_json(orient="records")

    async def _arun(self, query: str) -> Any:
        raise NotImplementedError("Async not supported")
