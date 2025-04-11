from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
import requests
from utils.sparql_utils import QueryEngine
from tools.base import WikidataBaseTool
import google.generativeai as genai
from config import GEMINI_API_KEY, MAX_PROPERTY_CANDIDATES
from sentence_transformers import SentenceTransformer, util

class PropertyRetrievalInput(BaseModel):
    question: str = Field(..., description="The user's question")
    entity_id: str = Field(..., description="The Wikidata entity ID (Q number)")
    limit: int = Field(MAX_PROPERTY_CANDIDATES, description="Maximum number of properties to retrieve")

class PropertyRetrievalTool(WikidataBaseTool):
    name: ClassVar[str] = "property_retrieval_tool"
    description: ClassVar[str] = "Retrieve properties relevant to the user's question and a Wikidata entity."
    
    _query_engine = PrivateAttr()
    _wikidata_api_url = PrivateAttr()
    _model = PrivateAttr()
    _sentence_model = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._query_engine = QueryEngine()
        self._wikidata_api_url = "https://www.wikidata.org/w/api.php"
        
        # Initialize Gemini for contextual property selection
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
        
        # Initialize sentence transformer for semantic similarity ranking
        self._sentence_model = SentenceTransformer("multi-qa-mpnet-base-cos-v1")
    
    def _run(self, input_data: PropertyRetrievalInput) -> Dict[str, Any]:
        """
        Retrieve properties relevant to the question and entity.
        
        Parameters:
        -----------
        input_data : PropertyRetrievalInput
            The user's question, entity ID, and limit
            
        Returns:
        --------
        Dict[str, Any]
            The relevant properties
        """
        question = input_data.question
        entity_id = input_data.entity_id
        limit = input_data.limit
        
        # Get common properties for this entity
        outgoing_properties = self._get_outgoing_properties(entity_id)
        incoming_properties = self._get_incoming_properties(entity_id)
        
        # Combine all properties
        all_properties = outgoing_properties + incoming_properties
        
        if not all_properties:
            self._logger.warning(f"No properties found for entity {entity_id}")
            return {
                "entity_id": entity_id,
                "properties": [],
                "question": question
            }
        
        # Rank properties by relevance to the question
        ranked_properties = self._rank_properties_by_relevance(question, all_properties, limit)
        
        result = {
            "entity_id": entity_id,
            "properties": ranked_properties,
            "question": question,
            "total_properties_found": len(all_properties)
        }
        
        self._log_input_output(input_data, result)
        return result
    
    def _get_outgoing_properties(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get properties where the entity is the subject."""
        query = f"""
        SELECT ?property ?propertyLabel ?propertyDescription (COUNT(?object) as ?count)
        WHERE {{
          wd:{entity_id} ?pred ?object .
          ?property wikibase:directClaim ?pred .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        GROUP BY ?property ?propertyLabel ?propertyDescription
        ORDER BY DESC(?count)
        LIMIT 50
        """
        
        results = self._query_engine.run_query(query)
        properties = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                property_id = row.get("property", "").split("/")[-1]
                properties.append({
                    "property_id": property_id,
                    "label": row.get("propertyLabel", ""),
                    "description": row.get("propertyDescription", ""),
                    "count": int(row.get("count", 0)),
                    "direction": "outgoing"
                })
                
        return properties
    
    def _get_incoming_properties(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get properties where the entity is the object."""
        query = f"""
        SELECT ?property ?propertyLabel ?propertyDescription (COUNT(?subject) as ?count)
        WHERE {{
          ?subject ?pred wd:{entity_id} .
          ?property wikibase:directClaim ?pred .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        GROUP BY ?property ?propertyLabel ?propertyDescription
        ORDER BY DESC(?count)
        LIMIT 50
        """
        
        results = self._query_engine.run_query(query)
        properties = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                property_id = row.get("property", "").split("/")[-1]
                properties.append({
                    "property_id": property_id,
                    "label": row.get("propertyLabel", ""),
                    "description": row.get("propertyDescription", ""),
                    "count": int(row.get("count", 0)),
                    "direction": "incoming"
                })
                
        return properties
    
    def _rank_properties_by_relevance(self, question: str, properties: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
        """
        Rank properties by their relevance to the question using semantic similarity.
        
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
        
        # Create property descriptions for semantic comparison
        property_texts = []
        for prop in properties:
            text = f"{prop['label']}"
            if prop.get('description'):
                text += f": {prop['description']}"
            property_texts.append(text)
        
        # Calculate embeddings
        question_embedding = self._sentence_model.encode(question, convert_to_tensor=True)
        property_embeddings = self._sentence_model.encode(property_texts, convert_to_tensor=True)
        
        # Calculate similarities
        similarities = util.cos_sim(question_embedding, property_embeddings)[0]
        
        # Add similarity scores to properties
        for i, prop in enumerate(properties):
            prop['relevance_score'] = float(similarities[i])
        
        # Sort by relevance score
        ranked_properties = sorted(properties, key=lambda x: x['relevance_score'], reverse=True)
        
        # Return top properties
        return ranked_properties[:limit]