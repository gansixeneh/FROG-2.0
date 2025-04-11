from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any, Optional, Tuple
from tools.base import WikidataBaseTool
from tools.entity_ontology_retrieval import EntityOntologyRetrievalTool, EntityOntologyRetrievalInput
import google.generativeai as genai
from sentence_transformers import SentenceTransformer, util
import random
from utils.sparql_utils import QueryEngine
from config import GEMINI_API_KEY, SENTENCE_TRANSFORMER_MODEL


class EntityLinkingInput(BaseModel):
    question: str = Field(..., description="The user's question")
    context: Optional[str] = Field(None, description="Optional additional context")


class EntityLinkingTool(WikidataBaseTool):
    name: ClassVar[str] = "entity_linking_tool"
    description: ClassVar[str] = (
        "Link mentions in the user's question to Wikidata entities and traverse the graph."
    )

    _entity_retrieval_tool = PrivateAttr()
    _model = PrivateAttr()
    _query_engine = PrivateAttr()
    _sentence_model = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize dependent tools
        self._entity_retrieval_tool = EntityOntologyRetrievalTool()
        self._query_engine = QueryEngine()

        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
        
        # Initialize sentence transformer for path ranking
        self._sentence_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

    def _run(self, input_data: EntityLinkingInput) -> Dict[str, Any]:
        """
        Link entities in the question to Wikidata entities and traverse the graph.

        Parameters:
        -----------
        input_data : EntityLinkingInput
            The user's question and optional context

        Returns:
        --------
        Dict[str, Any]
            The linked entities, paths, and structured representations
        """
        question = input_data.question

        # 1. Get top entities using the combined entity-ontology retrieval
        retrieval_input = EntityOntologyRetrievalInput(query=question, limit=5)
        entity_result = self._entity_retrieval_tool._run(retrieval_input)
        
        if not entity_result.get("entities"):
            return {
                "linked_entities": [],
                "paths": [],
                "original_question": question,
                "error": "No entities found in the question"
            }
        
        # 2. Extract the top 3 entities to use as starting points
        top_entities = entity_result["entities"][:3]
        
        # 3. Traverse the graph starting from these entities
        all_paths = []
        for entity in top_entities:
            # Get paths at different distances
            paths_dist_1 = self._find_paths(question, entity, distance=1)
            paths_dist_2 = self._find_paths(question, entity, distance=2)
            paths_dist_3 = self._find_paths(question, entity, distance=3)
            
            # Add all paths to the list
            all_paths.extend(paths_dist_1)
            all_paths.extend(paths_dist_2)
            all_paths.extend(paths_dist_3)
        
        # 4. Rank all paths by relevance to the question
        ranked_paths = self._rank_paths(question, all_paths)
        
        result = {
            "linked_entities": [
                {
                    "entity_id": e["entity_id"],
                    "label": e["label"],
                    "description": e.get("description", ""),
                    "score": e["score"],
                    "ontology": e.get("ontology", {})
                }
                for e in top_entities
            ],
            "paths": ranked_paths[:9],  # Top 9 paths (3 from each distance)
            "original_question": question
        }

        self._log_input_output(input_data, result)
        return result

    def _find_paths(self, question: str, entity: Dict[str, Any], distance: int) -> List[Dict[str, Any]]:
        """
        Find paths in the graph starting from the given entity.
        
        Parameters:
        -----------
        question : str
            The user's question
        entity : Dict[str, Any]
            The starting entity
        distance : int
            The path distance to explore
            
        Returns:
        --------
        List[Dict[str, Any]]
            Paths found in the graph
        """
        entity_id = entity["entity_id"]
        
        if distance == 1:
            # Direct properties (1-hop)
            return self._find_direct_paths(entity_id, question)
        elif distance == 2:
            # 2-hop paths
            return self._find_two_hop_paths(entity_id, question)
        elif distance == 3:
            # 3-hop paths
            return self._find_three_hop_paths(entity_id, question)
        else:
            return []
    
    def _find_direct_paths(self, entity_id: str, question: str) -> List[Dict[str, Any]]:
        """Find direct (1-hop) paths from the entity."""
        # Query for outgoing properties (entity as subject)
        outgoing_query = f"""
        SELECT ?prop ?propLabel ?object ?objectLabel ?objectDescription
        WHERE {{
          wd:{entity_id} ?p ?object .
          ?prop wikibase:directClaim ?p .
          OPTIONAL {{ ?object schema:description ?objectDescription . FILTER(LANG(?objectDescription) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 50
        """
        
        # Query for incoming properties (entity as object)
        incoming_query = f"""
        SELECT ?prop ?propLabel ?subject ?subjectLabel ?subjectDescription
        WHERE {{
          ?subject ?p wd:{entity_id} .
          ?prop wikibase:directClaim ?p .
          OPTIONAL {{ ?subject schema:description ?subjectDescription . FILTER(LANG(?subjectDescription) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 50
        """
        
        # Execute queries
        outgoing_results = self._query_engine.run_query(outgoing_query)
        incoming_results = self._query_engine.run_query(incoming_query)
        
        paths = []
        
        # Process outgoing paths
        if not isinstance(outgoing_results, dict) and not outgoing_results.empty:
            for _, row in outgoing_results.iterrows():
                prop_id = row.get("prop", "").split("/")[-1]
                object_id = row.get("object", "").split("/")[-1]
                
                # Only include paths to entities (Q-ids)
                if object_id.startswith("Q"):
                    paths.append({
                        "distance": 1,
                        "direction": "outgoing",
                        "start_entity": entity_id,
                        "path": [
                            {
                                "property_id": prop_id,
                                "property_label": row.get("propLabel", "")
                            }
                        ],
                        "end_entity": {
                            "entity_id": object_id,
                            "label": row.get("objectLabel", ""),
                            "description": row.get("objectDescription", "")
                        }
                    })
        
        # Process incoming paths
        if not isinstance(incoming_results, dict) and not incoming_results.empty:
            for _, row in incoming_results.iterrows():
                prop_id = row.get("prop", "").split("/")[-1]
                subject_id = row.get("subject", "").split("/")[-1]
                
                # Only include paths from entities (Q-ids)
                if subject_id.startswith("Q"):
                    paths.append({
                        "distance": 1,
                        "direction": "incoming",
                        "start_entity": entity_id,
                        "path": [
                            {
                                "property_id": prop_id,
                                "property_label": row.get("propLabel", "")
                            }
                        ],
                        "end_entity": {
                            "entity_id": subject_id,
                            "label": row.get("subjectLabel", ""),
                            "description": row.get("subjectDescription", "")
                        }
                    })
        
        # If we have too many paths, randomly sample before ranking
        if len(paths) > 20:
            paths = random.sample(paths, 20)
        
        # Rank paths by relevance to the question and return top 3
        return self._rank_paths(question, paths)[:3]
    
    def _find_two_hop_paths(self, entity_id: str, question: str) -> List[Dict[str, Any]]:
        """Find 2-hop paths from the entity."""
        # Query for 2-hop outgoing paths
        outgoing_query = f"""
        SELECT 
          ?prop1 ?prop1Label 
          ?mid ?midLabel ?midDescription
          ?prop2 ?prop2Label
          ?end ?endLabel ?endDescription
        WHERE {{
          wd:{entity_id} ?p1 ?mid .
          ?prop1 wikibase:directClaim ?p1 .
          ?mid ?p2 ?end .
          ?prop2 wikibase:directClaim ?p2 .
          FILTER(isIRI(?mid) && STRSTARTS(STR(?mid), "http://www.wikidata.org/entity/Q"))
          FILTER(isIRI(?end) && STRSTARTS(STR(?end), "http://www.wikidata.org/entity/Q"))
          OPTIONAL {{ ?mid schema:description ?midDescription . FILTER(LANG(?midDescription) = "en") }}
          OPTIONAL {{ ?end schema:description ?endDescription . FILTER(LANG(?endDescription) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 50
        """
        
        # Execute query
        results = self._query_engine.run_query(outgoing_query)
        
        paths = []
        
        # Process results
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                prop1_id = row.get("prop1", "").split("/")[-1]
                mid_id = row.get("mid", "").split("/")[-1]
                prop2_id = row.get("prop2", "").split("/")[-1]
                end_id = row.get("end", "").split("/")[-1]
                
                paths.append({
                    "distance": 2,
                    "start_entity": entity_id,
                    "path": [
                        {
                            "property_id": prop1_id,
                            "property_label": row.get("prop1Label", "")
                        },
                        {
                            "intermediate_entity": {
                                "entity_id": mid_id,
                                "label": row.get("midLabel", ""),
                                "description": row.get("midDescription", "")
                            }
                        },
                        {
                            "property_id": prop2_id,
                            "property_label": row.get("prop2Label", "")
                        }
                    ],
                    "end_entity": {
                        "entity_id": end_id,
                        "label": row.get("endLabel", ""),
                        "description": row.get("endDescription", "")
                    }
                })
        
        # If we have too many paths, randomly sample before ranking
        if len(paths) > 20:
            paths = random.sample(paths, 20)
        
        # Rank paths by relevance to the question and return top 3
        return self._rank_paths(question, paths)[:3]
    
    def _find_three_hop_paths(self, entity_id: str, question: str) -> List[Dict[str, Any]]:
        """Find 3-hop paths from the entity."""
        # For 3-hop paths, we'll use a simplified query to avoid complexity
        # This is a simplified version that may not find all possible 3-hop paths
        query = f"""
        SELECT 
          ?prop1 ?prop1Label 
          ?mid1 ?mid1Label ?mid1Description
          ?prop2 ?prop2Label
          ?mid2 ?mid2Label ?mid2Description
          ?prop3 ?prop3Label
          ?end ?endLabel ?endDescription
        WHERE {{
          wd:{entity_id} ?p1 ?mid1 .
          ?prop1 wikibase:directClaim ?p1 .
          ?mid1 ?p2 ?mid2 .
          ?prop2 wikibase:directClaim ?p2 .
          ?mid2 ?p3 ?end .
          ?prop3 wikibase:directClaim ?p3 .
          
          FILTER(isIRI(?mid1) && STRSTARTS(STR(?mid1), "http://www.wikidata.org/entity/Q"))
          FILTER(isIRI(?mid2) && STRSTARTS(STR(?mid2), "http://www.wikidata.org/entity/Q"))
          FILTER(isIRI(?end) && STRSTARTS(STR(?end), "http://www.wikidata.org/entity/Q"))
          OPTIONAL {{ ?mid1 schema:description ?mid1Description . FILTER(LANG(?mid1Description) = "en") }}
          OPTIONAL {{ ?mid2 schema:description ?mid2Description . FILTER(LANG(?mid2Description) = "en") }}
          OPTIONAL {{ ?end schema:description ?endDescription . FILTER(LANG(?endDescription) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }}
        LIMIT 25
        """
        
        # Execute query
        results = self._query_engine.run_query(query)
        
        paths = []
        
        # Process results
        if not isinstance(results, dict) and not results.empty:
            for _, row in results.iterrows():
                prop1_id = row.get("prop1", "").split("/")[-1]
                mid1_id = row.get("mid1", "").split("/")[-1]
                prop2_id = row.get("prop2", "").split("/")[-1]
                mid2_id = row.get("mid2", "").split("/")[-1]
                prop3_id = row.get("prop3", "").split("/")[-1]
                end_id = row.get("end", "").split("/")[-1]
                
                paths.append({
                    "distance": 3,
                    "start_entity": entity_id,
                    "path": [
                        {
                            "property_id": prop1_id,
                            "property_label": row.get("prop1Label", "")
                        },
                        {
                            "intermediate_entity": {
                                "entity_id": mid1_id,
                                "label": row.get("mid1Label", ""),
                                "description": row.get("mid1Description", "")
                            }
                        },
                        {
                            "property_id": prop2_id,
                            "property_label": row.get("prop2Label", "")
                        },
                        {
                            "intermediate_entity": {
                                "entity_id": mid2_id,
                                "label": row.get("mid2Label", ""),
                                "description": row.get("mid2Description", "")
                            }
                        },
                        {
                            "property_id": prop3_id,
                            "property_label": row.get("prop3Label", "")
                        }
                    ],
                    "end_entity": {
                        "entity_id": end_id,
                        "label": row.get("endLabel", ""),
                        "description": row.get("endDescription", "")
                    }
                })
        
        # If we have too many paths, randomly sample before ranking
        if len(paths) > 20:
            paths = random.sample(paths, 20)
        
        # Rank paths by relevance to the question and return top 3
        return self._rank_paths(question, paths)[:3]
    
    def _rank_paths(self, question: str, paths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank paths by their relevance to the question.
        
        Parameters:
        -----------
        question : str
            The user's question
        paths : List[Dict[str, Any]]
            List of paths to rank
            
        Returns:
        --------
        List[Dict[str, Any]]
            Ranked paths
        """
        if not paths:
            return []
        
        # Create path descriptions for comparison
        path_texts = []
        for path in paths:
            # Construct a text representation of the path
            if path["distance"] == 1:
                text = f"{path.get('start_entity', '')} → {path['path'][0]['property_label']} → {path['end_entity']['label']}"
                if path['end_entity'].get('description'):
                    text += f" ({path['end_entity']['description']})"
            elif path["distance"] == 2:
                intermediate = path["path"][1]["intermediate_entity"]
                text = (f"{path.get('start_entity', '')} → {path['path'][0]['property_label']} → "
                       f"{intermediate['label']} → {path['path'][2]['property_label']} → {path['end_entity']['label']}")
            elif path["distance"] == 3:
                inter1 = path["path"][1]["intermediate_entity"]
                inter2 = path["path"][3]["intermediate_entity"]
                text = (f"{path.get('start_entity', '')} → {path['path'][0]['property_label']} → "
                       f"{inter1['label']} → {path['path'][2]['property_label']} → "
                       f"{inter2['label']} → {path['path'][4]['property_label']} → {path['end_entity']['label']}")
            
            path_texts.append(text)
        
        # Calculate similarities
        question_embedding = self._sentence_model.encode(question, convert_to_tensor=True)
        path_embeddings = self._sentence_model.encode(path_texts, convert_to_tensor=True)
        similarities = util.cos_sim(question_embedding, path_embeddings)[0]
        
        # Add relevance scores to paths
        for i, path in enumerate(paths):
            path['relevance_score'] = float(similarities[i])
        
        # Sort by relevance score
        ranked_paths = sorted(paths, key=lambda x: x['relevance_score'], reverse=True)
        
        return ranked_paths