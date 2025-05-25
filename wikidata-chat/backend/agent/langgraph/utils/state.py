# backend/agent/langgraph/utils/state.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WikidataGraphRAGState(BaseModel):
    """State for the WikidataGraphRAG workflow"""
    question: str
    translated_question: Optional[str] = None
    original_lang: Optional[str] = None
    extracted_entities: Optional[List[str]] = Field(default_factory=list)
    use_sparql: Optional[bool] = None
    entity_uri: Optional[str] = None
    verbalization_result: Optional[List[Dict]] = Field(default_factory=list)
    verbalization_similarity: Optional[float] = None
    related_properties: Optional[List[str]] = Field(default_factory=list)
    sparql_query: Optional[str] = None
    query_result: Optional[List[Dict]] = Field(default_factory=list)
    context_str: Optional[str] = None
    final_answer: Optional[str] = None
    verbose: Optional[int] = 0
    use_cot: Optional[bool] = True
    output_uri: Optional[bool] = False
    try_threshold: Optional[int] = 10
    approach_used: Optional[str] = None
    next: Optional[str] = None
    visualizer: Optional[Any] = None
    boxology_verbose: Optional[int] = 0
    debug_callback: Optional[Any] = None
    include_references: Optional[bool] = True  # New field for reference enhancement
    google_search_result: Optional[Dict] = None  # New field for Google search results