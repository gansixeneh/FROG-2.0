# tools/property_retrieval.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import requests
from utils.sparql_utils import QueryEngine
from tools.base import WikidataBaseTool

class PropertyRetrievalInput(BaseModel):
    entity_id: str = Field(..., description="The Wikidata entity ID (Q number)")
    limit: int = Field(10, description="Maximum number of properties to retrieve")

class PropertyRetrievalTool(WikidataBaseTool):
    name = "property_retrieval_tool"
    description = "Retrieve relevant properties of Wikidata entities."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.query_engine = QueryEngine()
        self.wikidata_api_url = "https://www.wikidata.org/w/api.php"
    
    def _run(self, input_data: PropertyRetrievalInput) -> Dict[str, Any]:
        """
        Retrieve properties for a given entity.
        
        Parameters:
        -----------
        input_data : PropertyRetrievalInput
            The entity ID and limit
            
        Returns:
        --------
        Dict[str, Any]
            The entity properties
        """
        entity_id = input_data.entity_id
        limit = input_data.limit
        
        # Get outgoing properties (entity as subject)
        outgoing_properties = self._get_outgoing_properties(entity_id)
        
        # Get incoming properties (entity as object)
        incoming_properties = self._get_incoming_properties(entity_id)
        
        # Combine and sort by usage count
        all_properties = outgoing_properties + incoming_properties
        all_properties.sort(key=lambda x: x.get("count", 0), reverse=True)
        
        # Limit the number of properties
        properties = all_properties[:limit]
        
        result = {
            "entity_id": entity_id,
            "properties": properties,
            "outgoing_count": len(outgoing_properties),
            "incoming_count": len(incoming_properties),
            "total_count": len(all_properties)
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
        """
        
        results = self.query_engine.run_query(query)
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
        """
        
        results = self.query_engine.run_query(query)
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