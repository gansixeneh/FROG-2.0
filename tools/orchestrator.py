# tools/orchestrator.py
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from tools.base import WikidataBaseTool
from tools.entity_linking import EntityLinkingTool, EntityLinkingInput
from tools.property_retrieval import PropertyRetrievalTool, PropertyRetrievalInput
from tools.ontology_retrieval import OntologyRetrievalTool, OntologyRetrievalInput
from tools.sparql_generation import SPARQLGenerationTool, SPARQLGenerationInput
from tools.sparql_execution import SPARQLExecutionTool, SPARQLExecutionInput
from tools.query_fixer import QueryFixerTool, QueryFixerInput
from tools.answer_generation import AnswerGenerationTool, AnswerGenerationInput
from config import MAX_QUERY_ATTEMPTS

class OrchestratorInput(BaseModel):
    question: str = Field(..., description="The user's question")
    language: str = Field("en", description="The language to generate the answer in")

class EnsembleOrchestratorTool(WikidataBaseTool):
    name: str = "ensemble_orchestrator_tool"
    description: str = "Orchestrate multiple possible approaches to answering the question."
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize all tools
        self.entity_linking_tool = EntityLinkingTool()
        self.property_retrieval_tool = PropertyRetrievalTool()
        self.ontology_retrieval_tool = OntologyRetrievalTool()
        self.sparql_generation_tool = SPARQLGenerationTool()
        self.sparql_execution_tool = SPARQLExecutionTool()
        self.query_fixer_tool = QueryFixerTool()
        self.answer_generation_tool = AnswerGenerationTool()
    
    def _run(self, input_data: OrchestratorInput) -> Dict[str, Any]:
        """
        Orchestrate the entire question answering pipeline.
        
        Parameters:
        -----------
        input_data : OrchestratorInput
            The user's question and preferred language
            
        Returns:
        --------
        Dict[str, Any]
            The answer and related information
        """
        question = input_data.question
        language = input_data.language
        
        self.logger.info(f"Processing question: {question}")
        
        # Step 1: Entity Linking
        entity_linking_input = EntityLinkingInput(question=question)
        entity_linking_result = self.entity_linking_tool._run(entity_linking_input)
        
        if not entity_linking_result.get("linked_entities"):
            self.logger.warning("No entities found in the question.")
            return {
                "answer": "I couldn't identify any specific entities in your question. Could you please rephrase it?",
                "success": False,
                "question": question
            }
        
        linked_entities = entity_linking_result["linked_entities"]
        self.logger.info(f"Linked entities: {[e['label'] for e in linked_entities]}")
        
        # Step 2: Property Retrieval for the most relevant entity
        main_entity = linked_entities[0]
        property_retrieval_input = PropertyRetrievalInput(entity_id=main_entity["entity_id"])
        property_result = self.property_retrieval_tool._run(property_retrieval_input)
        
        # Step 3: Optional Ontology Retrieval
        ontology_retrieval_input = OntologyRetrievalInput(entity_id=main_entity["entity_id"])
        ontology_result = self.ontology_retrieval_tool._run(ontology_retrieval_input)
        
        # Step 4: SPARQL Generation
        sparql_generation_input = SPARQLGenerationInput(
            question=question,
            entities=linked_entities,
            properties=property_result.get("properties"),
            ontology=ontology_result
        )
        sparql_result = self.sparql_generation_tool._run(sparql_generation_input)
        
        if "error" in sparql_result:
            self.logger.error(f"Error in SPARQL generation: {sparql_result['error']}")
            return {
                "answer": "I had trouble generating a query to answer your question. Could you please rephrase it?",
                "success": False,
                "question": question
            }
        
        # Step 5: SPARQL Execution with retry mechanism
        sparql_query = sparql_result["sparql_query"]
        execution_results = None
        
        for attempt in range(MAX_QUERY_ATTEMPTS):
            self.logger.info(f"Executing SPARQL query (attempt {attempt+1}/{MAX_QUERY_ATTEMPTS})")
            
            sparql_execution_input = SPARQLExecutionInput(query=sparql_query)
            execution_result = self.sparql_execution_tool._run(sparql_execution_input)
            
            if execution_result.get("success", False):
                execution_results = execution_result.get("data", [])
                break
            
            # Query failed, try to fix it
            if attempt < MAX_QUERY_ATTEMPTS - 1:
                self.logger.info("Query failed, attempting to fix")
                query_fixer_input = QueryFixerInput(
                    query=sparql_query,
                    error=execution_result.get("error", "Unknown error")
                )
                fixed_result = self.query_fixer_tool._run(query_fixer_input)
                
                if fixed_result.get("success", False):
                    sparql_query = fixed_result["fixed_query"]
                else:
                    self.logger.error("Failed to fix query")
                    break
        
        # Step 6: Answer Generation
        if execution_results:
            answer_input = AnswerGenerationInput(
                question=question,
                query_results=execution_results,
                sparql_query=sparql_query,
                entities=linked_entities
            )
            answer_result = self.answer_generation_tool._run(answer_input)
            
            return {
                "answer": answer_result["answer"],
                "success": True,
                "question": question,
                "entities": [e["label"] for e in linked_entities],
                "query": sparql_query,
                "result_count": len(execution_results)
            }
        else:
            # No results found or query execution failed
            self.logger.warning("No results found or query execution failed")
            answer_input = AnswerGenerationInput(
                question=question,
                query_results=[],
                entities=linked_entities
            )
            answer_result = self.answer_generation_tool._run(answer_input)
            
            return {
                "answer": answer_result["answer"],
                "success": False,
                "question": question,
                "entities": [e["label"] for e in linked_entities],
                "query": sparql_query if 'sparql_query' in locals() else None
            }