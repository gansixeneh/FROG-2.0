# tools/sparql_generation.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any, Optional
import google.generativeai as genai
from config import GEMINI_API_KEY
from tools.base import WikidataBaseTool


class SPARQLGenerationInput(BaseModel):
    question: str = Field(..., description="The user's question")
    entities: List[Dict[str, Any]] = Field(
        ..., description="The linked entities with their Wikidata IDs"
    )
    properties: Optional[List[Dict[str, Any]]] = Field(
        None, description="Optional properties for the entities"
    )
    ontology: Optional[Dict[str, Any]] = Field(
        None, description="Optional ontology information"
    )


class SPARQLGenerationTool(WikidataBaseTool):
    name: ClassVar[str] = "sparql_generation_tool"
    description: ClassVar[str] = "Generate SPARQL queries to answer the user question."
    
    _model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.0-pro")
    
    def _run(self, input_data: SPARQLGenerationInput) -> Dict[str, Any]:
        """
        Generate SPARQL queries to answer the user question.

        Parameters:
        -----------
        input_data : SPARQLGenerationInput
            The user's question, linked entities, and optional properties and ontology

        Returns:
        --------
        Dict[str, Any]
            The generated SPARQL queries
        """
        question = input_data.question
        entities = input_data.entities
        properties = input_data.properties or []
        ontology = input_data.ontology or {}

        # Build context for the prompt
        entity_context = "\n".join(
            [
                f"- Entity: {e['label']} (ID: {e['entity_id']})"
                + (f", Description: {e['description']}" if e.get("description") else "")
                for e in entities
            ]
        )

        property_context = ""
        if properties:
            property_context = "\nRelevant properties:\n" + "\n".join(
                [
                    f"- Property: {p['label']} (ID: {p['property_id']})"
                    + (
                        f", Description: {p['description']}"
                        if p.get("description")
                        else ""
                    )
                    + f", Direction: {p.get('direction', 'outgoing')}"
                    for p in properties
                ]
            )

        ontology_context = ""
        if ontology and ontology.get("types"):
            ontology_context = "\nEntity types:\n" + "\n".join(
                [
                    f"- Type: {t['label']} (ID: {t['type_id']})"
                    for t in ontology.get("types", [])
                ]
            )

        # Create the prompt
        prompt = f"""
        Generate a SPARQL query for Wikidata to answer the following question:
        
        Question: {question}
        
        Entities identified:
        {entity_context}
        {property_context}
        {ontology_context}
        
        Important guidelines:
        1. Use the PREFIX wd: <http://www.wikidata.org/entity/> for entities
        2. Use the PREFIX wdt: <http://www.wikidata.org/prop/direct/> for properties
        3. Include SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        4. Use proper variable names that reflect the entities/properties
        5. Return only the SPARQL query without any explanation or markdown
        
        Complete SPARQL query:
        """

        try:
            # Generate the SPARQL query
            response = self._model.generate_content(prompt)
            sparql_query = response.text.strip()

            # Remove any markdown code blocks if present
            if sparql_query.startswith("```sparql"):
                sparql_query = (
                    sparql_query.replace("```sparql", "").replace("```", "").strip()
                )
            elif sparql_query.startswith("```"):
                sparql_query = sparql_query.replace("```", "").strip()

            result = {
                "sparql_query": sparql_query,
                "original_question": question,
                "entities": entities,
            }

            self._log_input_output(input_data, result)
            return result

        except Exception as e:
            self._logger.error(f"Error generating SPARQL query: {e}")
            return {
                "error": str(e),
                "original_question": question,
                "entities": entities,
            }
