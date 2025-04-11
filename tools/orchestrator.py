from langchain.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr
from typing import ClassVar, List, Dict, Any, Optional
from tools.base import WikidataBaseTool
from tools.entity_ontology_retrieval import EntityOntologyRetrievalTool, EntityOntologyRetrievalInput
from tools.property_retrieval import PropertyRetrievalTool, PropertyRetrievalInput
from tools.entity_linking import EntityLinkingTool, EntityLinkingInput
from tools.sparql_generation import SPARQLGenerationTool, SPARQLGenerationInput
from tools.sparql_execution import SPARQLExecutionTool, SPARQLExecutionInput
from tools.query_fixer import QueryFixerTool, QueryFixerInput
from tools.reranking import RerankingTool, RerankingInput
from tools.answer_generation import AnswerGenerationTool, AnswerGenerationInput
from config import MAX_QUERY_ATTEMPTS

class OrchestratorInput(BaseModel):
    question: str = Field(..., description="The user's question")
    language: str = Field("en", description="The language to generate the answer in")

class EnsembleOrchestratorTool(WikidataBaseTool):
    name: ClassVar[str] = "ensemble_orchestrator_tool"
    description: ClassVar[str] = "Orchestrate the flow of information through multiple approaches to answer the question."
    
    _entity_ontology_retrieval_tool = PrivateAttr()
    _property_retrieval_tool = PrivateAttr()
    _entity_linking_tool = PrivateAttr()
    _sparql_generation_tool = PrivateAttr()
    _sparql_execution_tool = PrivateAttr()
    _query_fixer_tool = PrivateAttr()
    _reranking_tool = PrivateAttr()
    _answer_generation_tool = PrivateAttr()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize all tools
        self._entity_ontology_retrieval_tool = EntityOntologyRetrievalTool()
        self._property_retrieval_tool = PropertyRetrievalTool()
        self._entity_linking_tool = EntityLinkingTool()
        self._sparql_generation_tool = SPARQLGenerationTool()
        self._sparql_execution_tool = SPARQLExecutionTool()
        self._query_fixer_tool = QueryFixerTool()
        self._reranking_tool = RerankingTool()
        self._answer_generation_tool = AnswerGenerationTool()
    
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
        
        self._logger.info(f"Processing question: {question}")
        
        # Step 1: Combined Entity and Ontology Retrieval
        entity_retrieval_input = EntityOntologyRetrievalInput(query=question)
        entity_retrieval_result = self._entity_ontology_retrieval_tool._run(entity_retrieval_input)
        
        if not entity_retrieval_result.get("entities"):
            self._logger.warning("No entities found in the question.")
            return {
                "answer": "I couldn't identify any specific entities in your question. Could you please rephrase it?",
                "success": False,
                "question": question
            }
        
        entities = entity_retrieval_result["entities"]
        self._logger.info(f"Retrieved entities: {[e['label'] for e in entities]}")
        
        # Step 2: Entity Linking with Graph Traversal
        entity_linking_input = EntityLinkingInput(question=question)
        entity_linking_result = self._entity_linking_tool._run(entity_linking_input)
        
        linked_entities = entity_linking_result.get("linked_entities", [])
        paths = entity_linking_result.get("paths", [])
        
        self._logger.info(f"Graph traversal found {len(paths)} relevant paths")
        
        # Step 3: Property Retrieval for the most relevant entity
        if entities:
            main_entity = entities[0]
            property_retrieval_input = PropertyRetrievalInput(
                question=question,
                entity_id=main_entity["entity_id"]
            )
            property_result = self._property_retrieval_tool._run(property_retrieval_input)
            properties = property_result.get("properties", [])
        else:
            properties = []
        
        # Step 4: Generate multiple SPARQL queries
        sparql_generation_input = SPARQLGenerationInput(
            question=question,
            entities=entities,
            paths=paths,
            properties=properties,
            num_queries=3
        )
        sparql_result = self._sparql_generation_tool._run(sparql_generation_input)
        
        if "error" in sparql_result:
            self._logger.error(f"Error in SPARQL generation: {sparql_result['error']}")
            return {
                "answer": "I had trouble generating queries to answer your question. Could you please rephrase it?",
                "success": False,
                "question": question
            }
        
        # Step 5: Execute multiple SPARQL queries with retry mechanism
        sparql_queries = sparql_result.get("sparql_queries", [])
        
        if not sparql_queries:
            self._logger.error("No SPARQL queries were generated")
            return {
                "answer": "I couldn't generate appropriate queries for your question. Could you please rephrase it?",
                "success": False,
                "question": question
            }
        
        query_results = []
        
        for query_obj in sparql_queries:
            query_id = query_obj.get("query_id", len(query_results) + 1)
            sparql_query = query_obj.get("sparql_query", "")
            explanation = query_obj.get("explanation", "No explanation provided")
            
            self._logger.info(f"Processing query {query_id}: {explanation}")
            
            # Try to execute with retries
            success = False
            data = []
            final_query = sparql_query
            
            for attempt in range(MAX_QUERY_ATTEMPTS):
                self._logger.info(f"Executing SPARQL query {query_id} (attempt {attempt+1}/{MAX_QUERY_ATTEMPTS})")
                
                sparql_execution_input = SPARQLExecutionInput(query=final_query)
                execution_result = self._sparql_execution_tool._run(sparql_execution_input)
                
                if execution_result.get("success", False):
                    success = True
                    data = execution_result.get("data", [])
                    column_names = execution_result.get("column_names", [])
                    row_count = execution_result.get("row_count", 0)
                    break
                
                # Query failed, try to fix it
                if attempt < MAX_QUERY_ATTEMPTS - 1:
                    self._logger.info(f"Query {query_id} failed, attempting to fix")
                    query_fixer_input = QueryFixerInput(
                        query=final_query,
                        error=execution_result.get("error", "Unknown error")
                    )
                    fixed_result = self._query_fixer_tool._run(query_fixer_input)
                    
                    if fixed_result.get("success", False):
                        final_query = fixed_result["fixed_query"]
                    else:
                        self._logger.error(f"Failed to fix query {query_id}")
                        break
            
            # Add to results
            query_results.append({
                "query_id": query_id,
                "sparql_query": final_query,
                "original_query": sparql_query,
                "explanation": explanation,
                "success": success,
                "data": data[:5] if len(data) > 5 else data,  # Limit to 5 rows for reranking
                "full_data": data,
                "row_count": len(data)
            })
        
        # Step 6: Rerank the results
        if any(qr.get("success", False) for qr in query_results):
            # Only rerank successful queries
            successful_queries = [qr for qr in query_results if qr.get("success", False)]
            
            if successful_queries:
                reranking_input = RerankingInput(
                    question=question,
                    query_results=successful_queries,
                    entities=entities
                )
                reranking_result = self._reranking_tool._run(reranking_input)
                
                best_result = reranking_result.get("best_result", successful_queries[0])
                
                # Step 7: Generate Answer
                answer_input = AnswerGenerationInput(
                    question=question,
                    query_results=best_result.get("full_data", best_result.get("data", [])),
                    sparql_query=best_result.get("sparql_query", ""),
                    entities=entities
                )
                answer_result = self._answer_generation_tool._run(answer_input)
                
                return {
                    "answer": answer_result["answer"],
                    "success": True,
                    "question": question,
                    "entities": [e["label"] for e in entities],
                    "paths": len(paths),
                    "query": best_result.get("sparql_query", ""),
                    "result_count": best_result.get("row_count", 0),
                    "query_explanation": best_result.get("explanation", "")
                }
        
        # No successful queries or empty results
        self._logger.warning("No successful queries with results")
        answer_input = AnswerGenerationInput(
            question=question,
            query_results=[],
            entities=entities
        )
        answer_result = self._answer_generation_tool._run(answer_input)
        
        return {
            "answer": answer_result["answer"],
            "success": False,
            "question": question,
            "entities": [e["label"] for e in entities],
            "paths": len(paths),
            "query": sparql_queries[0].get("sparql_query", "") if sparql_queries else None
        }