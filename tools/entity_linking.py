# tools/entity_linking.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any, Optional
from tools.base import WikidataBaseTool
from tools.entity_retrieval import EntityRetrievalTool, EntityRetrievalInput
import google.generativeai as genai
from config import GEMINI_API_KEY, MAX_ENTITY_CANDIDATES


class EntityLinkingInput(BaseModel):
    question: str = Field(..., description="The user's question")
    context: Optional[str] = Field(None, description="Optional additional context")


class EntityLinkingTool(WikidataBaseTool):
    name: ClassVar[str] = "entity_linking_tool"
    description: ClassVar[str] = (
        "Link mentions in the user's question to Wikidata entities."
    )

    _entity_retrieval_tool = PrivateAttr()
    _model = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize dependent tools
        self._entity_retrieval_tool = EntityRetrievalTool()

        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")

    def _run(self, input_data: EntityLinkingInput) -> Dict[str, Any]:
        """
        Link entities in the question to Wikidata entities.

        Parameters:
        -----------
        input_data : EntityLinkingInput
            The user's question and optional context

        Returns:
        --------
        Dict[str, Any]
            The linked entities with their Wikidata IDs
        """
        question = input_data.question

        # 1. Extract potential entity mentions from the question
        entity_mentions = self._extract_entity_mentions(question)

        # 2. Link each mention to Wikidata entities
        linked_entities = []
        for mention in entity_mentions:
            # Use the entity retrieval tool
            retrieval_input = EntityRetrievalInput(
                query=mention, limit=MAX_ENTITY_CANDIDATES
            )
            candidates = self._entity_retrieval_tool._run(retrieval_input)

            if candidates:
                # Take the top candidate
                top_candidate = candidates[0]
                linked_entities.append(
                    {
                        "mention": mention,
                        "entity_id": top_candidate["entity_id"],
                        "label": top_candidate["label"],
                        "description": top_candidate.get("description", ""),
                        "score": top_candidate["score"],
                        "candidates": candidates[
                            :3
                        ],  # Keep top 3 candidates for reference
                    }
                )

        result = {"linked_entities": linked_entities, "original_question": question}

        self._log_input_output(input_data, result)
        return result

    def _extract_entity_mentions(self, question: str) -> List[str]:
        """
        Extract potential entity mentions from the question using Gemini.

        Parameters:
        -----------
        question : str
            The user's question

        Returns:
        --------
        List[str]
            List of potential entity mentions
        """
        prompt = f"""
        Extract the main entities from this question that I should search for in Wikidata:
        Question: {question}
        
        Return only the entity names as a comma-separated list, with no additional text.
        """

        try:
            response = self._model.generate_content(prompt)
            entity_text = response.text.strip()
            entities = [e.strip() for e in entity_text.split(",")]
            return entities
        except Exception as e:
            self._logger.error(f"Error extracting entity mentions: {e}")
            # Fallback: simple extraction based on capitalized words
            words = question.split()
            candidates = [w for w in words if w[0].isupper() and len(w) > 1]
            return candidates or [
                question
            ]  # Return the whole question if no candidates
