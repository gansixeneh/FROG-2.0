from langchain.tools import BaseTool
from pydantic import Field
from typing import Any
import google.generativeai as genai
from config import GEMINI_API_KEY

class AnswerGenerationTool(BaseTool):
    name: str = "answer_generation"
    description: str = "Converts raw SPARQL results into a natural language answer."

    model: Any = Field(default_factory=lambda: genai.GenerativeModel("gemini-2.0-flash"))

    def _run(self, context: str) -> str:
        prompt = f"""
        Please generate a concise natural language answer based on the following Wikidata result:

        {context}

        Answer in fluent English. If the question is in Indonesian, answer in Indonesian.
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

    async def _arun(self, context: str) -> Any:
        raise NotImplementedError("Async not supported")
