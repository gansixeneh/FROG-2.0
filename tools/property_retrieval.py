from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
import requests
from utils.sparql_utils import QueryEngine
from tools.base import WikidataBaseTool
import google.generativeai as genai
from config import GEMINI_API_KEY, MAX_PROPERTY_CANDIDATES

class PropertyRetrievalInput(BaseModel):
    question: str = Field(..., description="The user's question")
    entity_id: str = Field(None, description="Optional Wikidata entity ID for context")
    limit: int = Field(MAX_PROPERTY_CANDIDATES, description="Maximum number of properties to retrieve")

class PropertyRetrievalTool(WikidataBaseTool):
    name: ClassVar[str] = "property_retrieval_tool"
    description: ClassVar[str] = "Retrieve properties relevant to the user's question."
    
    _query_engine = PrivateAttr()
    _wikidata_api_url = PrivateAttr()
    _model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._query_engine = QueryEngine()
        self._wikidata_api_url = "https://www.wikidata.org/w/api.php"
        
        # Initialize Gemini for property extraction and ranking
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
    
    def _run(self, input_data: PropertyRetrievalInput) -> Dict[str, Any]:
        """
        Retrieve properties relevant to the question.
        
        Parameters:
        -----------
        input_data : PropertyRetrievalInput
            The user's question, optional entity ID, and limit
            
        Returns:
        --------
        Dict[str, Any]
            The relevant properties
        """
        question = input_data.question
        entity_id = input_data.entity_id
        limit = input_data.limit
        
        # Step 1: Extract potential property concepts from the question
        property_concepts = self._extract_property_concepts(question, entity_id)
        self._logger.info(f"Extracted property concepts: {property_concepts}")
        
        if not property_concepts:
            return {
                "properties": [],
                "question": question,
                "entity_id": entity_id
            }
        
        # Step 2: Find matching Wikidata properties for each concept
        all_properties = []
        for concept in property_concepts:
            properties = self._search_wikidata_properties(concept)
            all_properties.extend(properties)
        
        # Step 3: Rank properties using LLM
        ranked_properties = self._rank_properties_with_llm(question, all_properties, limit)
        
        result = {
            "properties": ranked_properties,
            "question": question,
            "entity_id": entity_id,
            "total_properties_found": len(all_properties)
        }
        
        self._log_input_output(input_data, result)
        return result
    
    def _extract_property_concepts(self, question: str, entity_id: str = None) -> List[str]:
        """
        Extract potential property concepts from the question using LLM.
        
        Parameters:
        -----------
        question : str
            The user's question
        entity_id : str, optional
            Optional entity ID for context
            
        Returns:
        --------
        List[str]
            List of property concepts
        """
        # If entity_id is provided, get entity information for context
        entity_context = ""
        if entity_id:
            try:
                params = {
                    'action': 'wbgetentities',
                    'ids': entity_id,
                    'languages': 'en',
                    'format': 'json'
                }
                
                response = requests.get(self._wikidata_api_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    entity = data.get('entities', {}).get(entity_id, {})
                    
                    label = entity.get('labels', {}).get('en', {}).get('value', entity_id)
                    description = entity.get('descriptions', {}).get('en', {}).get('value', '')
                    
                    entity_context = f"Context entity: {label} ({entity_id})"
                    if description:
                        entity_context += f"\nDescription: {description}"
            except Exception as e:
                self._logger.error(f"Error getting entity context: {e}")
        
        # Create the prompt
        prompt = f"""
        Extract the properties, relationships, or attributes that would be relevant to answer this question using Wikidata:
        
        Question: {question}
        {entity_context}
        
        Return only the property concepts as a comma-separated list. Focus on general property concepts, not specific Wikidata property IDs.
        Example properties might be: date of birth, spouse, capital, population, etc.
        """
        
        try:
            # Generate property concepts
            response = self._model.generate_content(prompt)
            property_text = response.text.strip()
            
            # Parse the comma-separated list
            properties = [p.strip() for p in property_text.split(",")]
            return properties
        except Exception as e:
            self._logger.error(f"Error extracting property concepts: {e}")
            # Fallback: extract possible property terms
            words = question.lower().split()
            possible_properties = ["date", "time", "location", "place", "name", "creator", "author", 
                                  "birth", "death", "founded", "created", "located", "population", 
                                  "height", "width", "size", "capital", "country", "member"]
            
            return [word for word in words if word in possible_properties]
    
    def _search_wikidata_properties(self, property_concept: str) -> List[Dict[str, Any]]:
        """
        Search for Wikidata properties matching a concept.
        
        Parameters:
        -----------
        property_concept : str
            The property concept to search for
            
        Returns:
        --------
        List[Dict[str, Any]]
            List of matching properties
        """
        params = {
            'action': 'wbsearchentities',
            'search': property_concept,
            'language': 'en',
            'format': 'json',
            'type': 'property',
            'limit': 5  # Get top 5 for each concept
        }
        
        try:
            # Make API request
            response = requests.get(self._wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract property information
            properties = []
            for prop in data.get('search', []):
                properties.append({
                    'property_id': prop.get('id', ''),
                    'label': prop.get('label', ''),
                    'description': prop.get('description', ''),
                    'search_term': property_concept,
                    'direction': 'unknown'  # No direction since we're not traversing the graph
                })
            
            return properties
            
        except Exception as e:
            self._logger.error(f"Error in Wikidata property search: {e}")
            return []
    
    def _rank_properties_with_llm(self, question: str, properties: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Rank properties by their relevance to the question using LLM.
        
        Parameters:
        -----------
        question : str
            The user's question
        properties : List[Dict[str, Any]]
            List of properties to rank
        limit : int
            Maximum number of properties to return
            
        Returns:
        --------
        List[Dict[str, Any]]
            Ranked properties
        """
        if not properties:
            return []
        
        # Remove duplicates by property_id
        unique_properties = {}
        for prop in properties:
            prop_id = prop.get('property_id')
            if prop_id and prop_id not in unique_properties:
                unique_properties[prop_id] = prop
        
        properties = list(unique_properties.values())
        
        # If we have fewer properties than limit, return all
        if len(properties) <= limit:
            return properties
        
        # Format properties for LLM prompt
        property_descriptions = []
        for i, prop in enumerate(properties):
            description = (
                f"Property {i+1}: {prop['label']} (ID: {prop['property_id']})\n"
                f"Description: {prop.get('description', 'N/A')}\n"
                f"Search term: {prop.get('search_term', 'N/A')}\n"
            )
            property_descriptions.append(description)
        
        # Create the prompt
        prompt = f"""
        Rank these Wikidata properties based on their relevance to answering the following question:
        
        Question: {question}
        
        Property candidates:
        {''.join(property_descriptions)}
        
        Return a ranking as a comma-separated list of property numbers, from most relevant to least relevant.
        For example: "2, 5, 1, 3, 4" means Property 2 is most relevant, followed by Property 5, etc.
        Only include the properties that are actually relevant to answering the question.
        """
        
        try:
            # Generate ranking
            response = self._model.generate_content(prompt)
            ranking_text = response.text.strip()
            
            # Parse the ranking
            ranking = []
            for item in ranking_text.replace(" ", "").split(","):
                try:
                    index = int(item) - 1  # Convert to zero-based index
                    if 0 <= index < len(properties):
                        ranking.append(index)
                except ValueError:
                    continue
            
            # If ranking failed, return properties in original order
            if not ranking:
                return properties[:limit]
            
            # Reorder properties based on ranking
            ranked_properties = []
            for index in ranking:
                if index < len(properties):
                    ranked_properties.append(properties[index])
            
            # Add any remaining properties not in the ranking
            for i, prop in enumerate(properties):
                if i not in ranking and len(ranked_properties) < limit:
                    ranked_properties.append(prop)
            
            return ranked_properties[:limit]
            
        except Exception as e:
            self._logger.error(f"Error in LLM ranking: {e}")
            return properties[:limit]