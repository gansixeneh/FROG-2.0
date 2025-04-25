import logging
import re
from typing import Dict, Any
import google.generativeai as genai

# Setup logger
logger = logging.getLogger(__name__)

class QueryGenerator:
    """Node for generating SPARQL queries from entities and properties."""

    def __init__(self, api_key: str):
        logger.info("Initializing QueryGenerator")
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def generate_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a SPARQL query from entities and properties

        Args:
            state: Current state with 'entities' and 'properties' keys

        Returns:
            Updated state with generated SPARQL query
        """
        question = state.get("question", "")
        entities = state.get("entities", [])
        properties = state.get("properties", [])
        feedback = state.get("feedback", "")

        logger.info(f"QueryGenerator: Generating SPARQL query for question: '{question}'")
        logger.info(f"QueryGenerator: Using {len(entities)} entities and {len(properties)} properties")
        
        if feedback:
            logger.info(f"QueryGenerator: Incorporating feedback: '{feedback}'")

        # Prepare entity and property information for the prompt
        entity_info = []
        for entity in entities:
            entity_str = f"Entity: {entity.get('label')} (ID: {entity.get('id')}), Description: {entity.get('description')}"
            logger.debug(f"QueryGenerator: Entity info: {entity_str}")
            entity_info.append(entity_str)

        property_info = []
        for prop in properties:
            prop_str = f"Property: {prop.get('label')} (ID: {prop.get('id')}), Description: {prop.get('description')}"
            logger.debug(f"QueryGenerator: Property info: {prop_str}")
            property_info.append(prop_str)

        entity_info_str = "\n".join(entity_info)
        property_info_str = "\n".join(property_info)

        prompt = f"""
        Generate a SPARQL query for the Wikidata endpoint that answers the following question:
        
        Question: {question}
        
        Using these entities and properties:
        {entity_info_str}
        {property_info_str}
        
        IMPORTANT RULES:
        1. The query should ONLY return URIs, NOT labels.
        2. Do NOT use rdfs:label, wikibase:label, or SERVICE wikibase:label.
        3. Do NOT include variables with "Label" suffix in the SELECT clause.
        4. Use the appropriate Wikidata prefixes (wd, wdt, p, ps, etc.)
        5. Only use the entities and properties provided above.
        
        {"Previous feedback to address: " + feedback if feedback else ""}
        
        Format your response as:
        ```sparql
        [YOUR SPARQL QUERY HERE]
        ```
        """

        logger.info("QueryGenerator: Calling Gemini model to generate SPARQL query")
        response = self.model.generate_content(prompt)
        raw_response = response.text.strip()
        logger.debug(f"QueryGenerator: Raw model response: {raw_response[:500]}...")

        # Try to extract query from code block
        sparql_pattern = r"```(?:sparql)?\s*([\s\S]*?)```"
        match = re.search(sparql_pattern, raw_response)
        
        if match:
            logger.info("QueryGenerator: Extracted SPARQL query from code block")
            query = match.group(1).strip()
        else:
            # If no code block found, use the entire response
            logger.info("QueryGenerator: No code block found, using entire response as query")
            query = raw_response

        logger.info("QueryGenerator: SPARQL query generated successfully")
        logger.info(f"QueryGenerator: Generated query:\n{query}")

        return {**state, "generated_query": query, "generation_complete": True}

    def __call__(self, state):
        """Make the class callable for langgraph."""
        logger.info("QueryGenerator node called")
        result = self.generate_query(state)
        logger.info("QueryGenerator node completed")
        return result