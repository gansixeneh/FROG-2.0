# tools/entity_linking_tool.py
from langchain.tools import BaseTool
from pydantic import Field
from entity_property_retrieval import EntityPropertyRetrieval
import google.generativeai as genai
from config import GEMINI_API_KEY
from typing import List, Dict, Any

class EntityLinkingTool(BaseTool):
    name: str = "EntityLinkingTool"
    description: str = "Extracts and links entity mentions from a user question to Wikidata entities."
    retriever: Any = Field(default_factory=EntityPropertyRetrieval)
    gemini_model: Any = Field(default_factory=lambda: genai.GenerativeModel("gemini-2.0-flash"))

    def __init__(self):
        super().__init__()
        self.retriever = EntityPropertyRetrieval()
        genai.configure(api_key=GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    def _run(self, question: str) -> List[Dict[str, Any]]:
        # Step 1: Extract entity mentions using Gemini
        prompt = f"""
        Extract the main entities from this question that I should search for in a knowledge base:
        Question: {question}
        Return only the entity names as a comma-separated list, with no additional text.
        """
        response = self.gemini_model.generate_content(prompt)
        entities = [e.strip() for e in response.text.strip().split(",")]

        # Step 2: Link to Wikidata using search
        linked = []
        for entity in entities:
            candidates = self.retriever.search_entities(entity)
            top = candidates.iloc[0] if not candidates.empty else None
            if top is not None:
                linked.append({
                    "mention": entity,
                    "wikidata_id": top["entity_id"],
                    "label": top["label"],
                    "description": top["description"]
                })

        return linked

    async def _arun(self, question: str):
        raise NotImplementedError("Async not supported")
