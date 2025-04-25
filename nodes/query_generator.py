from typing import Dict, Any
import google.generativeai as genai

class QueryGenerator:
    """Node for generating SPARQL queries from entities and properties."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
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
        
        # Prepare entity and property information for the prompt
        entity_info = []
        for entity in entities:
            entity_info.append(f"Entity: {entity.get('label')} (ID: {entity.get('id')}), Description: {entity.get('description')}")
        
        property_info = []
        for prop in properties:
            property_info.append(f"Property: {prop.get('label')} (ID: {prop.get('id')}), Description: {prop.get('description')}")
        
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
        
        Common SPARQL prefixes for Wikidata:
        PREFIX wd: <http://www.wikidata.org/entity/>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX p: <http://www.wikidata.org/prop/>
        PREFIX ps: <http://www.wikidata.org/prop/statement/>
        PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
        
        {"Previous feedback to address: " + feedback if feedback else ""}
        
        Only return the SPARQL query, with prefixes but without explanation or additional text.
        """
        
        response = self.model.generate_content(prompt)
        query = response.text.strip()
        
        # Extract just the SPARQL query if there are any additional explanations
        if "PREFIX" in query:
            query_start = query.find("PREFIX")
            query = query[query_start:]
        
        # Add necessary prefixes if they're missing
        prefixes = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
"""
        
        if not query.strip().startswith("PREFIX"):
            query = prefixes + query
        
        return {
            **state,
            "generated_query": query,
            "generation_complete": True
        }

    def __call__(self, state):
        """Make the class callable for langgraph."""
        return self.generate_query(state)