
# backend/agent/langgraph/nodes/translation.py
from datetime import datetime
from googletrans import Translator
from ..utils.state import FROGGraphRAGState

class TranslationNode:
    """Node for translating non-English questions"""
    def __init__(self):
        self.translator = Translator()
    
    def __call__(self, state: FROGGraphRAGState) -> FROGGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Translation Node", 
                "start",
                {"question": state.question},
                start_time=start_time
            )
            
        # Check if translation is enabled
        use_translation = getattr(state, 'use_translation', True)
        
        # Detect language
        detected = self.translator.detect(state.question)
        state.original_lang = detected.lang
        
        # Log detection
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Translation Node",
                "language detection",
                {"detected_language": detected.lang, "translation_enabled": use_translation}
            )
        
        # Translate if not English and translation is enabled
        if state.original_lang != "en" and use_translation:
            state.translated_question = self.translator.translate(state.question, dest="en").text
            
            # Log translation
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Translation Node",
                    "translation",
                    {"original": state.question, "translated": state.translated_question}
                )
                
            if state.verbose > 0:
                print(f"Translated Question: {state.translated_question}")
        else:
            state.translated_question = state.question
            
            # Log no translation needed/used
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Translation Node",
                    "no translation " + ("needed" if state.original_lang == "en" else "enabled"),
                    {"question": state.question}
                )
        
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Translation Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state
