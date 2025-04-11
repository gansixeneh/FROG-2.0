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
    paths: Optional[List[Dict[str, Any]]] = Field(
        None, description="Optional paths discovered in the graph"
    )
    properties: Optional[List[Dict[str, Any]]] = Field(
        None, description="Optional properties for the entities"
    )
    ontology: Optional[Dict[str, Any]] = Field(
        None, description="Optional ontology information"
    )
    num_queries: int = Field(3, description="Number of different queries to generate")


class SPARQLGenerationTool(WikidataBaseTool):
    name: ClassVar[str] = "sparql_generation_tool"
    description: ClassVar[str] = "Generate multiple SPARQL queries to answer the user question."

    _model = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize Gemini
        genai.configure(api_key=GEMINI_API_KEY)
        self._model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")

    def _run(self, input_data: SPARQLGenerationInput) -> Dict[str, Any]:
        """
        Generate multiple SPARQL queries to answer the user question.

        Parameters:
        -----------
        input_data : SPARQLGenerationInput
            The user's question, linked entities, paths, and optional properties and ontology

        Returns:
        --------
        Dict[str, Any]
            The generated SPARQL queries
        """
        question = input_data.question
        entities = input_data.entities
        paths = input_data.paths or []
        properties = input_data.properties or []
        ontology = input_data.ontology or {}
        num_queries = input_data.num_queries

        # Build context for the prompt
        entity_context = "\n".join(
            [
                f"- Entity: {e['label']} (ID: {e['entity_id']})"
                + (f", Description: {e['description']}" if e.get("description") else "")
                for e in entities
            ]
        )

        path_context = ""
        if paths:
            path_context = "\nDiscovered paths in the knowledge graph:\n"
            for i, path in enumerate(paths):
                distance = path.get("distance", 0)
                if distance == 1:
                    path_context += (f"- Path {i+1} (distance 1): {path.get('start_entity', '')} → "
                                    f"{path['path'][0]['property_label']} → {path['end_entity']['label']}\n")
                elif distance == 2:
                    intermediate = path["path"][1]["intermediate_entity"]
                    path_context += (f"- Path {i+1} (distance 2): {path.get('start_entity', '')} → "
                                    f"{path['path'][0]['property_label']} → {intermediate['label']} → "
                                    f"{path['path'][2]['property_label']} → {path['end_entity']['label']}\n")
                elif distance == 3:
                    inter1 = path["path"][1]["intermediate_entity"]
                    inter2 = path["path"][3]["intermediate_entity"]
                    path_context += (f"- Path {i+1} (distance 3): {path.get('start_entity', '')} → "
                                    f"{path['path'][0]['property_label']} → {inter1['label']} → "
                                    f"{path['path'][2]['property_label']} → {inter2['label']} → "
                                    f"{path['path'][4]['property_label']} → {path['end_entity']['label']}\n")

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
        Generate {num_queries} different SPARQL queries for Wikidata to answer the following question:
        
        Question: {question}
        
        Entities identified:
        {entity_context}
        {path_context}
        {property_context}
        {ontology_context}
        
        Important guidelines:
        1. Use the PREFIX wd: <http://www.wikidata.org/entity/> for entities
        2. Use the PREFIX wdt: <http://www.wikidata.org/prop/direct/> for properties
        3. Include SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        4. Use proper variable names that reflect the entities/properties
        5. Create {num_queries} different queries that approach the question in different ways
        6. Provide a brief explanation for each query to explain how it addresses the question
        7. Format your response as:
           QUERY 1:
           ```sparql
           [SPARQL query 1]
           ```
           Explanation: [short explanation of query 1 approach]

           QUERY 2:
           ```sparql
           [SPARQL query 2]
           ```
           Explanation: [short explanation of query 2 approach]
           
           ... and so on.
        8. Prioritize using the discovered paths if they are relevant to the question
        
        Please generate {num_queries} different SPARQL queries:
        """

        try:
            # Generate the SPARQL queries
            response = self._model.generate_content(prompt)
            query_text = response.text.strip()

            # Parse the generated queries
            queries = self._parse_queries(query_text, num_queries)

            result = {
                "sparql_queries": queries,
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
    
    def _parse_queries(self, query_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """
        Parse the generated text into a list of query objects.
        
        Parameters:
        -----------
        query_text : str
            The generated text containing the queries
        expected_count : int
            The expected number of queries
            
        Returns:
        --------
        List[Dict[str, Any]]
            List of parsed queries with explanations
        """
        queries = []
        
        try:
            # Split by QUERY n:
            sections = query_text.split("QUERY ")
            
            # Remove any empty sections
            sections = [s for s in sections if s.strip()]
            
            for section in sections:
                # Extract the query number, SPARQL code, and explanation
                query_obj = {"query_id": len(queries) + 1}
                
                # Extract the SPARQL query from the code block
                if "```sparql" in section:
                    sparql_parts = section.split("```sparql")
                    if len(sparql_parts) > 1:
                        query_code = sparql_parts[1].split("```")[0].strip()
                        query_obj["sparql_query"] = query_code
                elif "```" in section:
                    sparql_parts = section.split("```")
                    if len(sparql_parts) > 1:
                        query_code = sparql_parts[1].strip()
                        query_obj["sparql_query"] = query_code
                
                # Extract the explanation
                if "Explanation:" in section:
                    explanation = section.split("Explanation:")[1].strip()
                    # If there's another query after this, trim the explanation
                    if "QUERY" in explanation:
                        explanation = explanation.split("QUERY")[0].strip()
                    query_obj["explanation"] = explanation
                
                # Add to list if it has a query
                if "sparql_query" in query_obj:
                    queries.append(query_obj)
                    
                # Stop if we've reached the expected count
                if len(queries) >= expected_count:
                    break
        except Exception as e:
            self._logger.error(f"Error parsing queries: {e}")
        
        # If we parsed fewer queries than expected, log a warning
        if len(queries) < expected_count:
            self._logger.warning(f"Expected {expected_count} queries but only parsed {len(queries)}")
        
        # Ensure we have at least one query
        if not queries:
            # Try a simpler parsing approach as fallback
            try:
                # Just look for code blocks
                code_blocks = query_text.split("```")
                for i in range(1, len(code_blocks), 2):
                    code = code_blocks[i].strip()
                    if code.startswith("sparql"):
                        code = code[6:].strip()
                    
                    queries.append({
                        "query_id": len(queries) + 1,
                        "sparql_query": code,
                        "explanation": "Generated query"
                    })
                    
                    if len(queries) >= expected_count:
                        break
            except Exception as e:
                self._logger.error(f"Error in fallback query parsing: {e}")
                
        return queries