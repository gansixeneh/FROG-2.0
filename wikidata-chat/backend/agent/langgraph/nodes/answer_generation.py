
# backend/agent/langgraph/nodes/answer_generation.py
from datetime import datetime
import logging
import googletrans
from ..utils.state import FROGGraphRAGState

logger = logging.getLogger(__name__)

class AnswerGenerationNode:
    """Node for generating the final natural language answer"""
    def __init__(self, llm_factory=None):
        """
        Initialize AnswerGenerationNode
        
        Args:
            llm_factory: LLM factory instance for multi-provider support
        """
        self.llm_factory = llm_factory
        self.translator = googletrans.Translator()
        
        if not self.llm_factory:
            raise ValueError("llm_factory must be provided")
        
        # Initialize the LLM provider
        try:
            self._llm_provider = self.llm_factory.get_model_for_answer_generation()
            logger.info("Initialized AnswerGenerationNode with LLM factory")
        except Exception as e:
            logger.error(f"Failed to get model from factory: {e}")
            raise ValueError(f"Failed to initialize LLM provider: {e}")
        
    def __call__(self, state: FROGGraphRAGState) -> FROGGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node", 
                "start",
                {"question": state.question},
                start_time=start_time
            )
            
        # Log input data
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node",
                "input data",
                {
                    "context": state.context_str,
                    "query_result": state.query_result[:10] if state.query_result and len(state.query_result) > 10 else state.query_result
                }
            )
            
        # Create prompt for answer generation
        lang_detected = state.original_lang if state.original_lang else "en"
        
        # Build prompt for answer generation
        prompt = f"""You are an assistant for question-answering tasks. Use the following retrieved context to answer the question.
Answer directly and concisely in three sentences or less. If you don't know the answer, say so.{f" Answer in {googletrans.LANGUAGES.get(lang_detected, 'the appropriate')} language." if lang_detected != 'en' else ''}

Question: {state.question} 
Context: {state.context_str} 

Answer:"""
        
        # Log prompt
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node",
                "prompt prepared",
                {
                    "language": googletrans.LANGUAGES.get(lang_detected, lang_detected),
                    "prompt_template": "Answer directly and concisely in three sentences or less..."
                }
            )
        
        # Generate the answer
        gen_start_time = datetime.now()
        
        # Log generation start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node",
                "answer generation start",
                None,
                start_time=gen_start_time
            )
            
        # Generate response using configured model
        if self._llm_provider.is_chat_template_supported():
            # Use chat template if supported
            messages = [
                {"role": "system", "content": "You are an assistant for question-answering tasks."},
                {"role": "user", "content": prompt}
            ]
            formatted_prompt = self._llm_provider.apply_chat_template(messages)
        else:
            # Use direct prompt
            formatted_prompt = prompt
        
        state.final_answer = self._llm_provider.generate_response(formatted_prompt)
        
        # End generation timing
        gen_end_time = datetime.now()
        
        # Log generated answer
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node",
                "generated answer",
                {"answer": state.final_answer},
                start_time=gen_start_time,
                end_time=gen_end_time
            )
            
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Answer Generation Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state
