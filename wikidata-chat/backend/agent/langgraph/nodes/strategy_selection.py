
# backend/agent/langgraph/nodes/strategy_selection.py
import re
from datetime import datetime
from ..utils.state import WikidataGraphRAGState

def contains_multiple_entities(question):
    """Check if the question has multiple entities"""
    keywords = ["and", "or", "as well as", "both", "along with", "together with"]
    question = question.lower()
    return any(
        f" {keyword} " in question
        or question.startswith(f"{keyword} ")
        or question.endswith(f" {keyword}")
        for keyword in keywords
    )

class StrategySelectionNode:
    """Node for deciding between SPARQL and verbalization strategies"""
    def __init__(self, always_use_generate_sparql=False):
        self.always_use_generate_sparql = always_use_generate_sparql
        
    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Strategy Selection Node", 
                "start",
                {"question": state.translated_question, "entities": state.extracted_entities},
                start_time=start_time
            )
        
        # Determine if we should use SPARQL or verbalization
        contains_multiple = contains_multiple_entities(state.translated_question)
        state.use_sparql = self.always_use_generate_sparql or contains_multiple
        
        # Log decision factors
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Strategy Selection Node",
                "decision factors",
                {
                    "always_use_sparql": self.always_use_generate_sparql,
                    "contains_multiple_entities": contains_multiple,
                    "final_decision": "sparql" if state.use_sparql else "verbalization"
                }
            )
        
        # Route to appropriate next step
        if not state.use_sparql and state.extracted_entities:
            state.next = "verbalization"
            # Log routing decision
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Strategy Selection Node",
                    "routing decision",
                    {"next_node": "verbalization"}
                )
        else:
            state.next = "property_generation"  # FIXED: Route to property_generation instead
            # Log routing decision
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Strategy Selection Node",
                    "routing decision",
                    {"next_node": "property_generation"}  # FIXED: Log property_generation
                )
        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Strategy Selection Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
        
        return state
