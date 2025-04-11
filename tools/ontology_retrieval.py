# tools/ontology_retrieval.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any
from utils.sparql_utils import QueryEngine
from tools.base import WikidataBaseTool

class OntologyRetrievalInput(BaseModel):
    entity_id: str = Field(..., description="The Wikidata entity ID (Q number)")

class OntologyRetrievalTool(WikidataBaseTool):
    name: ClassVar[str] = "ontology_retrieval_tool"
    description: ClassVar[str] = "Retrieve class/type and hierarchy information about Wikidata entities."
    
    _query_engine = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._query_engine = QueryEngine()
    
    def _run(self, input_data: OntologyRetrievalInput) -> Dict[str, Any]:
        """
        Retrieve ontology information for a given entity.
        
        Parameters:
        -----------
        input_data : OntologyRetrievalInput
            The entity ID
            
        Returns:
        --------
        Dict[str, Any]
            The entity ontology information
        """
        entity_id = input_data.entity_id
        
        # Get entity types/classes
        types = self._get_entity_types(entity_id)
        
        # Get entity superclasses (if it's a class)
        superclasses = self._get_entity_superclasses(entity_id)
        
        # Get entity subclasses (if it's a class)
        subclasses = self._get_entity_subclasses(entity_id)
        
        result = {
            "entity_id": entity_id,
            "types": types,
            "superclasses": superclasses,
            "subclasses": subclasses,
            "is_class": len(subclasses) > 0  # Entity is likely a class if it has subclasses
        }
        
        self._log_input_output(input_data, result)
        return result
    
    def _get_entity_types(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the types/classes of the entity."""
        query = f"""
        SELECT ?type ?typeLabel ?typeDescription
        WHERE {{
          wd:{entity_id} wdt:P31 ?type .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        
        results = self._query_engine.run_query(query)
        types = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                type_id = row.get("type", "").split("/")[-1]
                types.append({
                    "type_id": type_id,
                    "label": row.get("typeLabel", ""),
                    "description": row.get("typeDescription", "")
                })
                
        return types
    
    def _get_entity_superclasses(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the superclasses of the entity (if it's a class)."""
        query = f"""
        SELECT ?superclass ?superclassLabel ?superclassDescription
        WHERE {{
          wd:{entity_id} wdt:P279 ?superclass .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        """
        
        results = self._query_engine.run_query(query)
        superclasses = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                superclass_id = row.get("superclass", "").split("/")[-1]
                superclasses.append({
                    "superclass_id": superclass_id,
                    "label": row.get("superclassLabel", ""),
                    "description": row.get("superclassDescription", "")
                })
                
        return superclasses
    
    def _get_entity_subclasses(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get the subclasses of the entity (if it's a class)."""
        query = f"""
        SELECT ?subclass ?subclassLabel ?subclassDescription
        WHERE {{
          ?subclass wdt:P279 wd:{entity_id} .
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 100
        """
        
        results = self._query_engine.run_query(query)
        subclasses = []
        
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                subclass_id = row.get("subclass", "").split("/")[-1]
                subclasses.append({
                    "subclass_id": subclass_id,
                    "label": row.get("subclassLabel", ""),
                    "description": row.get("subclassDescription", "")
                })
                
        return subclasses