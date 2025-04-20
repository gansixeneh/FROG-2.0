# backend/agent/agent.py
import os
import asyncio
import queue
import threading
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

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
                print(f"Error in debug handler processing thread: {e}")
    
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
                    print(f"Error in async callback: {e}")
            else:
                # Run the callback in the loop
                loop.run_until_complete(self.callback_func(message))
        else:
            # Regular synchronous callback
            try:
                self.callback_func(message)
            except Exception as e:
                print(f"Error in sync callback: {e}")
    
    def _add_to_queue(self, message):
        """Add a message to the queue for processing."""
        if self.is_running and self.callback_func:
            self.message_queue.put(str(message))
    
    # ---- Callback methods overridden from BaseCallbackHandler ----
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        self._add_to_queue("🧠 Starting to think about the question...")
    
    def on_llm_new_token(self, token, **kwargs):
        # Only log token if needed for streaming (disabled for cleaner output)
        pass
    
    def on_llm_end(self, response, **kwargs):
        self._add_to_queue("✅ Finished thinking")
    
    def on_llm_error(self, error, **kwargs):
        self._add_to_queue(f"❌ Error during thinking: {error}")
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        chain_name = serialized.get('name', 'unknown')
        self._add_to_queue(f"📎 Starting reasoning chain: {chain_name}")
    
    def on_chain_end(self, outputs, **kwargs):
        self._add_to_queue("📎 Reasoning chain completed")
    
    def on_chain_error(self, error, **kwargs):
        self._add_to_queue(f"❌ Error in reasoning chain: {error}")
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        """Important: This captures the start of a tool call."""
        tool_name = serialized.get('name', 'unknown tool')
        formatted_input = input_str.replace('\n', ' ')
        if len(formatted_input) > 100:
            formatted_input = formatted_input[:100] + "..."
        
        # Format message based on tool type
        if tool_name == "search_entity_property":
            self._add_to_queue(f"🔍 Searching Wikidata for: {formatted_input}")
        elif tool_name == "execute_sparql":
            self._add_to_queue(f"🔧 Executing SPARQL query against Wikidata")
        elif tool_name == "google_search":
            self._add_to_queue(f"🌐 Searching the web for: {formatted_input}")
        else:
            self._add_to_queue(f"🔧 Using tool: {tool_name} with input: {formatted_input}")
    
    def on_tool_end(self, output, **kwargs):
        """Important: This captures the result of a tool call."""
        # Convert output to string and truncate if too long
        output_str = str(output)
        if len(output_str) > 200:
            output_str = output_str[:200] + "... [output truncated]"
        
        self._add_to_queue(f"✓ Tool returned result: {output_str}")
    
    def on_tool_error(self, error, **kwargs):
        self._add_to_queue(f"❌ Tool error: {error}")
    
    def on_text(self, text, **kwargs):
        """Captures text output from the agent."""
        self._add_to_queue(text)
    
    def on_agent_action(self, action, **kwargs):
        """Captures when the agent decides to take an action."""
        tool = getattr(action, 'tool', 'unknown')
        tool_input = getattr(action, 'tool_input', '')
        print(action)
        self._add_to_queue(f"🤖 Agent decided to use: {tool}")
    
    def on_agent_finish(self, finish, **kwargs):
        """Captures when the agent finishes its reasoning."""
        self._add_to_queue(f"✅ Agent finished reasoning process")
    
    def __del__(self):
        """Clean up resources when the handler is garbage collected."""
        self.is_running = False
        if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=1.0)


# Import tools from the correct location
from agent.tools.search_tool import SearchWikidataTool
from agent.tools.sparql_tool import ExecuteSPARQLTool
from agent.tools.google_search_tool import GoogleSearchTool

class WikidataAgent:
    def __init__(self, gemini_api_key: str = None, debug_callback=None):
        # Set API key
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
        elif "GEMINI_API_KEY" not in os.environ:
            raise ValueError(
                "Gemini API key must be provided or set as GEMINI_API_KEY environment variable"
            )
        
        # Setup debug handler - pass the callback directly
        self.debug_handler = DebugHandler(debug_callback)

        # Initialize tools
        self.search_tool = SearchWikidataTool()
        self.sparql_tool = ExecuteSPARQLTool()
        self.google_search_tool = GoogleSearchTool()
        self.tools = [self.search_tool, self.sparql_tool, self.google_search_tool]

        # Create the system message with detailed instructions
        system_message = """You are an AI assistant that answers questions primarily by querying Wikidata. 
You have access to three tools:

1. search_entity_property: Use this to search for entities or properties in Wikidata.
2. execute_sparql: Use this to run SPARQL queries against Wikidata.
3. google_search: Use this ONLY as a fallback when Wikidata doesn't have the information or for recent events.

To answer a user's question, follow these steps:

1. ALWAYS try to use Wikidata first:
   - Analyze the question and identify key entities and properties
   - Use search_entity_property to find Wikidata IDs
   - Construct and execute a SPARQL query using execute_sparql
   - If the results are satisfactory, formulate an answer based on Wikidata

2. ONLY if Wikidata doesn't have the information (empty results, outdated info, or insufficient data):
   - Use the google_search tool as a fallback
   - Clearly indicate in your answer that you're using web search results instead of Wikidata
   - Include citations for the web search results

IMPORTANT: You must provide traceability in your final answer. Always include the following information:

If using Wikidata:
------------------------------
## ANSWER
[The direct answer to the user's question in natural language]

## TRACEABILITY
### Entity Search
- Searched for: [entity name]
- Selected: [entity label] (Wikidata ID: [Q-id])
   
### Property Search
- Searched for: [property name]
- Selected: [property label] (Wikidata ID: [P-id])
   
### SPARQL Query
```sparql
[The enhanced SPARQL query that was executed, from the 'enhanced_query' field in the tool response]
```

### Results Interpretation
[Brief explanation of how the query results were interpreted to form the answer]

### References
- [Reference URL if available]
- Reference date: [Date in human-readable format if available]
- [Any other reference information available]
------------------------------

If using Google Search (as fallback):
------------------------------
## ANSWER
[The direct answer to the user's question in natural language]

## TRACEABILITY
### Search Method
Web Search (used as fallback because [reason Wikidata was insufficient])
- Initial Wikidata attempt: [Brief description of what was tried with Wikidata]
- Reason for fallback: [Why Wikidata was insufficient - empty results, outdated, etc.]

### Google Search Query
[The query sent to the Google Search tool]

### Results Summary
[Brief summary of the search results used for the answer]

### Sources
- [Source title] - [Complete URL]
- [Source title] - [Complete URL]
- [Additional sources with full URLs]
------------------------------

Remember:
- Wikidata is your primary source - try it FIRST for ALL questions
- Only use Google Search as a fallback when:
  - Wikidata returns no results
  - The information in Wikidata is likely outdated (for recent events)
  - The question cannot be answered by structured data in Wikidata
- Be transparent about which source you're using
- Always include full traceability
- Include citation information from Google Search results when used
"""

        # Create a prompt template with system message and human input
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_message),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])

        # Initialize the model and agent
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2, google_api_key=os.environ["GEMINI_API_KEY"])
        self.agent = create_tool_calling_agent(
            self.llm, self.tools, self.prompt
        )
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=20,
            callbacks=[self.debug_handler]
        )

    def query(self, user_question: str) -> str:
        """
        Process a user question and return an answer based on Wikidata or web search as fallback

        Args:
            user_question: The user's natural language question

        Returns:
            A natural language answer based on Wikidata information or web search
        """
        response = self.agent_executor.invoke({"input": user_question})
        return response["output"]