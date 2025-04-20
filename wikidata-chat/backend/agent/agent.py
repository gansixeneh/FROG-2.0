# backend/agent/agent.py
import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain.callbacks.base import BaseCallbackHandler

class DebugHandler(BaseCallbackHandler):
    """Callback handler for capturing debug information."""
    
    def __init__(self, callback_func=None):
        self.callback_func = callback_func
        
    def on_llm_start(self, serialized, prompts, **kwargs):
        output = f"Starting LLM with prompts: {prompts}"
        if self.callback_func:
            self._call_callback(output)
    
    def on_chain_start(self, serialized, inputs, **kwargs):
        output = f"Entering new {serialized['name']} chain..."
        if self.callback_func:
            self._call_callback(output)
    
    def on_chain_end(self, outputs, **kwargs):
        output = f"> Finished chain."
        if self.callback_func:
            self._call_callback(output)
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        output = f"Invoking: `{serialized['name']}` with `{input_str}`"
        if self.callback_func:
            self._call_callback(output)
    
    def on_tool_end(self, output, **kwargs):
        if self.callback_func:
            self._call_callback(str(output))
    
    def on_text(self, text, **kwargs):
        if self.callback_func:
            self._call_callback(text)
    
    def _call_callback(self, output):
        """Helper method to call the callback function"""
        if not self.callback_func:
            return
            
        # Check if callback is a coroutine function
        if asyncio.iscoroutinefunction(self.callback_func):
            # We're in a sync context, so we can't directly await
            # Create a future and schedule it in the event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.callback_func(output))
            else:
                loop.run_until_complete(self.callback_func(output))
        else:
            # Regular function callback
            self.callback_func(output)


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
        
        # Setup debug handler
        self.debug_callback = debug_callback
        self.debug_handler = DebugHandler(self._handle_debug_output)

        # Initialize tools
        self.search_tool = SearchWikidataTool()
        self.sparql_tool = ExecuteSPARQLTool()
        self.google_search_tool = GoogleSearchTool()
        self.tools = [self.search_tool, self.sparql_tool, self.google_search_tool]

        # Create the system message with detailed instructions (same as in your original code)
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

    def _handle_debug_output(self, output):
        """Handle debug output from the agent."""
        if self.debug_callback:
            # If we're running in async context, we need to be careful
            # The Debug Handler runs in sync context, but we need to pass
            # the output to an async callback
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # We're in an async context, use create_task
                    asyncio.create_task(self.debug_callback(output))
                else:
                    # We're not in an async context, run the coroutine directly
                    loop.run_until_complete(self.debug_callback(output))
            except RuntimeError:
                # No event loop, so we're in a sync context - can't call the async callback
                # This shouldn't normally happen since the agent is meant to be used in async context
                pass

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