
# backend/agent/langgraph/nodes/entity_extraction.py
import re
import json
import logging
from datetime import datetime
from typing import Optional, Union
from ..utils.state import WikidataGraphRAGState
import google.generativeai as genai

logger = logging.getLogger(__name__)

class EntityExtractionNode:
    """Node for extracting entities and properties from questions"""
    def __init__(self, genai_model=None, llm_factory=None):
        """
        Initialize EntityExtractionNode
        
        Args:
            genai_model: Legacy Gemini model (for backward compatibility)
            llm_factory: LLM factory instance for multi-provider support
        """
        self.genai_model = genai_model
        self.llm_factory = llm_factory
        self.json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
        
        # Initialize the LLM provider
        self._llm_provider = None
        if self.llm_factory:
            try:
                self._llm_provider = self.llm_factory.get_model_for_entity_extraction()
                logger.info("Initialized EntityExtractionNode with LLM factory")
            except Exception as e:
                logger.error(f"Failed to get model from factory: {e}")
                logger.warning("Falling back to legacy Gemini model")
                self._llm_provider = None
        
        if not self._llm_provider and not self.genai_model:
            raise ValueError("Either llm_factory or genai_model must be provided")
        
    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Entity Extraction Node", 
                "start",
                {"question": state.translated_question},
                start_time=start_time
            )
        
        # Define system prompt from finetune-extract-entity-property.ipynb
        system_prompt = """You are an expert entity and property extractor for knowledge graph querying. Your task is to analyze a natural language question and identify the relevant entities and properties needed to create a SPARQL query for Wikidata.

Guidelines:
1. For each question, extract ALL entities mentioned in the question
2. For each question, extract ALL relevant properties needed to answer the question
3. Format your response as a structured JSON object with 'entities' and 'properties' keys
4. Each key should contain an array of strings with the entity or property names
5. Focus ONLY on extracting, not on generating SPARQL queries

Your output should look like:
```json
{
  "entities": ["entity1", "entity2", ...],
  "properties": ["property1", "property2", ...]
}
```
"""

        # Create user prompt from finetune-extract-entity-property.ipynb
        user_prompt = f"Question: {state.translated_question}\n\nExtract all entities and properties from this question that would be needed to generate a SPARQL query for Wikidata."
        
        # Log prompt preparation
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Entity Extraction Node",
                "prompt prepared",
                {"prompt_type": "system-user", "system_prompt": system_prompt[:100] + "..."}
            )
        
        # Extract entities and properties
        try:
            extraction_start_time = datetime.now()
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Entity Extraction Node",
                    "extraction start",
                    {"question": state.translated_question},
                    start_time=extraction_start_time
                )
                
            # Generate extraction using configured model
            if self._llm_provider:
                # Use LLM factory provider
                if self._llm_provider.is_chat_template_supported():
                    # Use chat template
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                    prompt = self._llm_provider.apply_chat_template(messages)
                else:
                    # Fallback to simple concatenation
                    prompt = f"{system_prompt}\n\n{user_prompt}"
                
                completion = self._llm_provider.generate_response(prompt)
            else:
                # Legacy Gemini model
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"
                response = self.genai_model.generate_content(combined_prompt)
                completion = response.text
            
            # Log raw completion
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Entity Extraction Node",
                    "llm completion",
                    {"completion": completion}
                )
            
            # Extract JSON content from completion
            match = re.search(self.json_pattern, completion)
            if match:
                json_str = match.group(1).strip()
                try:
                    extracted_data = json.loads(json_str)
                except json.JSONDecodeError:
                    extracted_data = {"entities": [], "properties": []}
            else:
                # Try direct parsing if no JSON code block found
                try:
                    extracted_data = json.loads(completion)
                except json.JSONDecodeError:
                    extracted_data = {"entities": [], "properties": []}
            
            # Update state with extracted entities and properties
            state.extracted_entities = extracted_data.get("entities", [])
            state.related_properties = extracted_data.get("properties", [])
            
            extraction_end_time = datetime.now()
            
            # Log extracted entities and properties
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Entity Extraction Node",
                    "entities and properties extracted",
                    {
                        "entities": state.extracted_entities,
                        "properties": state.related_properties
                    },
                    start_time=extraction_start_time,
                    end_time=extraction_end_time
                )
                
            if state.verbose > 0:
                print(f"Extracted Entities: {state.extracted_entities}")
                print(f"Extracted Properties: {state.related_properties}")
        except Exception as e:
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Entity Extraction Node",
                    "extraction error",
                    {"error": str(e)}
                )
                
            if state.verbose > 0:
                print(f"Error extracting entities and properties: {e}")
            state.extracted_entities = []
            state.related_properties = []
        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Entity Extraction Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state
