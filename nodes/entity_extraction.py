import re
import json
from typing import Dict, Any, List
import google.generativeai as genai
from tools.search_tool import WikidataSearchTool

class EntityExtractor:
    """Node for extracting entities and properties from a user query."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.search_tool = WikidataSearchTool()
        
    def extract_entities_properties(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract entities and properties from a user query
        
        Args:
            state: Current state with 'question' key
            
        Returns:
            Updated state with entities and properties
        """
        question = state.get("question", "")
        
        # Use Gemini to identify potential entities and properties
        prompt = f"""
        Analyze the following question and identify the key entities and properties needed to create a Wikidata SPARQL query.
        
        Question: {question}
        
        For each entity or property, provide:
        1. Term: The name of the entity or property
        2. Type: Whether it's an "entity" or "property"
        3. Importance: "required" or "optional"
        
        Format your response as a structured list of JSON objects:
        [
          {{"term": "entity name", "type": "entity", "importance": "required"}},
          {{"term": "property name", "type": "property", "importance": "required"}}
        ]
        
        Only respond with the JSON list, nothing else.
        """
        
        response = self.model.generate_content(prompt)
        response_text = response.text
        
        # Extract JSON from response
        try:
            # Try to parse the entire response as JSON first
            terms = json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON using regex
            json_pattern = r"\[\s*\{.*\}\s*\]"
            json_match = re.search(json_pattern, response_text, re.DOTALL)
            
            if json_match:
                json_text = json_match.group(0)
                try:
                    terms = json.loads(json_text)
                except:
                    # Fallback if JSON parsing fails
                    terms = self._parse_terms_fallback(response_text)
            else:
                terms = self._parse_terms_fallback(response_text)
        
        # Search Wikidata for each term
        entities = []
        properties = []
        
        for term in terms:
            term_name = term.get("term", "")
            term_type = term.get("type", "entity")
            importance = term.get("importance", "required")
            
            if not term_name:
                continue
                
            search_results = self.search_tool.search(term_name, term_type)
            
            if search_results:
                result = search_results[0]  # Take the top result
                result["original_term"] = term_name
                result["importance"] = importance
                
                if term_type == "entity":
                    entities.append(result)
                else:
                    properties.append(result)
        
        return {
            **state,
            "entities": entities,
            "properties": properties,
            "extraction_complete": True
        }
    
    def _parse_terms_fallback(self, text: str) -> List[Dict[str, Any]]:
        """Fallback method to parse terms if JSON parsing fails."""
        terms = []
        lines = text.split('\n')
        
        current_term = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "term:" in line.lower() or "entity:" in line.lower():
                if current_term and "term" in current_term:
                    terms.append(current_term)
                current_term = {}
                
                # Try to extract term
                match = re.search(r"[\"']([^\"']+)[\"']", line)
                if match:
                    current_term["term"] = match.group(1)
                else:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        current_term["term"] = parts[1].strip()
            
            if "type:" in line.lower():
                if "entity" in line.lower():
                    current_term["type"] = "entity"
                elif "property" in line.lower():
                    current_term["type"] = "property"
            
            if "importance:" in line.lower():
                if "required" in line.lower():
                    current_term["importance"] = "required"
                elif "optional" in line.lower():
                    current_term["importance"] = "optional"
        
        if current_term and "term" in current_term:
            terms.append(current_term)
            
        return terms

    def __call__(self, state):
        """Make the class callable for langgraph."""
        return self.extract_entities_properties(state)