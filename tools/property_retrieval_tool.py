from langchain.tools import BaseTool
from pydantic import Field
from typing import Any
from entity_property_retrieval import EntityPropertyRetrieval
import pandas as pd

class PropertyRetrievalTool(BaseTool):
    name: str = "property_retrieval"
    description: str = "Gets properties of a Wikidata entity to help in SPARQL query construction."

    retriever: Any = Field(default_factory=EntityPropertyRetrieval)

    def _run(self, entity_id: str) -> str:
        props_tail = self.retriever.query_engine.run_query(f"""
            SELECT DISTINCT ?property ?propertyLabel
            WHERE {{
                wd:{entity_id} ?prop ?target .
                ?property wikibase:directClaim ?prop .
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
        """)

        props_head = self.retriever.query_engine.run_query(f"""
            SELECT DISTINCT ?property ?propertyLabel
            WHERE {{
                ?subject ?prop wd:{entity_id} .
                ?property wikibase:directClaim ?prop .
                SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
        """)

        combined = pd.concat([props_tail, props_head]).drop_duplicates()
        return combined.to_json(orient="records")

    async def _arun(self, entity_id: str) -> Any:
        raise NotImplementedError("Async not supported")
