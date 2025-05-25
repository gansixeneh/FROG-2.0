# backend/agent/agent.py
import os
import asyncio
import queue
import threading
import json
import tempfile
import logging
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

# Import LangGraph agent
from agent.langgraph import WikidataGraphAgent

# Configure logging
logger = logging.getLogger(__name__)

class DebugHandler(BaseCallbackHandler):
    """Callback handler for capturing debug information and sending it through WebSocket."""
    
    def __init__(self, callback_func=None):
        self.callback_func = callback_func
        # Create a thread-safe queue for passing messages between threads
        self.message_queue = queue.Queue()
        # Start a thread to process messages from the queue
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processing_thread.start()
        logger.info("Initialized DebugHandler with callback")
    
    def update_callback(self, new_callback_func):
        """Update the callback function without recreating the handler"""
        logger.info("Updating debug callback function")
        self.callback_func = new_callback_func
    
    def _process_queue(self):
        """Process messages from the queue and send them to the callback."""
        while self.is_running:
            try:
                # Get message from queue with timeout to allow thread to exit
                message = self.message_queue.get(timeout=0.1)
                # Send message to callback
                self._send_to_callback(message)
                # Mark task as done
                self.message_queue.task_done()
            except queue.Empty:
                # Queue is empty, continue waiting
                continue
            except Exception as e:
                logger.error(f"Error in debug handler processing thread: {e}")
    
    def _send_to_callback(self, message):
        """Send a message to the callback function, handling both sync and async callbacks."""
        if not self.callback_func:
            return
            
        # Handle async callback functions
        if asyncio.iscoroutinefunction(self.callback_func):
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop in this thread, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Schedule the callback in the event loop
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self.callback_func(message), loop)
                # Optional: Wait for result with timeout
                try:
                    future.result(timeout=1.0)
                except Exception as e:
                    logger.error(f"Error in async callback: {e}")
            else:
                # Run the callback in the loop
                loop.run_until_complete(self.callback_func(message))
        else:
            # Regular synchronous callback
            try:
                self.callback_func(message)
            except Exception as e:
                logger.error(f"Error in sync callback: {e}")
    
    def _add_to_queue(self, message):
        """Add a message to the queue for processing."""
        if self.is_running and self.callback_func:
            self.message_queue.put(str(message))
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        self._add_to_queue(f"📎 Starting reasoning chain")
    
    def on_chain_end(self, outputs, **kwargs):
        self._add_to_queue("📎 Reasoning chain completed")
    
    def on_agent_action(self, action, **kwargs):
        """Captures when the agent decides to take an action, including the tool and input."""
        tool = getattr(action, 'tool', 'unknown')
        tool_input = getattr(action, 'tool_input', '')
        
        # Format the tool input for readability
        input_str = str(tool_input)
        if len(input_str) > 100:
            input_str = input_str[:100] + "..."
            
        self._add_to_queue(f"🤖 Agent decided to use: {tool} with input: {input_str}")
    
    def on_agent_finish(self, finish, **kwargs):
        """Captures when the agent finishes its reasoning."""
        self._add_to_queue(f"✅ Agent finished reasoning process")
    
    def __del__(self):
        """Clean up resources when the handler is garbage collected."""
        self.is_running = False
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)

class WikidataAgent:
    def __init__(self, gemini_api_key: str = None, debug_callback=None):
        # Set API key
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
        elif "GEMINI_API_KEY" not in os.environ:
            raise ValueError(
                "Gemini API key must be provided or set as GEMINI_API_KEY environment variable"
            )
        
        # Setup debug handler for legacy support
        self.debug_handler = DebugHandler(debug_callback)
        
        # Initialize the LangGraph agent
        self.langgraph_agent = WikidataGraphAgent(
            gemini_api_key=gemini_api_key,
            always_use_generate_sparql=False,
            print_output=False,
            debug_callback=debug_callback
        )
        
        # Store visualization files
        self.visualization_files = {}
        
        logger.info("Initialized WikidataAgent")
    
    def update_debug_callback(self, debug_callback):
        """Update the debug callback function without recreating the agent"""
        logger.info("Updating debug callback in WikidataAgent")
        # Update the debug callback in the DebugHandler
        if hasattr(self, 'debug_handler'):
            self.debug_handler.update_callback(debug_callback)
        
        # Update the debug callback in the LangGraph agent
        if hasattr(self, 'langgraph_agent'):
            self.langgraph_agent.debug_callback = debug_callback
            
            # Also update in the visualizer if it exists
            if hasattr(self.langgraph_agent, 'visualizer') and self.langgraph_agent.visualizer:
                self.langgraph_agent.visualizer.debug_callback = debug_callback

    def query(self, user_question: str) -> tuple:
        """
        Process a user question and return an answer based on Wikidata or web search as fallback

        Args:
            user_question: The user's natural language question

        Returns:
            A tuple containing:
            - A natural language answer based on Wikidata information
            - Visualization files content dictionary
        """
        # Use the LangGraph agent for the actual querying
        answer, explanation, visualization_data = self.langgraph_agent.query(
            user_question, 
            verbose=0, 
            boxology_verbose=2  # Enable visualization
        )
        
        # Store visualization files for later download and read contents
        visualization_files_content = {}
        if visualization_data:
            # Store paths for backward compatibility
            self.visualization_files = {
                'json': visualization_data.get('json_path'),
                'mermaid': visualization_data.get('mermaid_path'),
                'ttl': visualization_data.get('ttl_path')
            }
            
        # Read file contents
            for file_type, file_path in self.visualization_files.items():
                if file_path and os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            visualization_files_content[file_type] = {
                                'content': f.read(),
                                'file_name': os.path.basename(file_path)
                            }
                        logger.info(f"Read visualization file: {file_type} ({os.path.basename(file_path)})")
                    except Exception as e:
                        logger.error(f"Error reading {file_type} visualization file: {e}")
        
        # Return the explanation as the response, and visualization files content
        return explanation, visualization_files_content