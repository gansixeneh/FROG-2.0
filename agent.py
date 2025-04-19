import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage

from tools.search_tool import SearchWikidataTool
from tools.sparql_tool import ExecuteSPARQLTool
from tools.google_search_tool import GoogleSearchTool


class WikidataAgent:
    def __init__(self, gemini_api_key: str = None):
        # Set API key
        if gemini_api_key:
            os.environ["GEMINI_API_KEY"] = gemini_api_key
        elif "GEMINI_API_KEY" not in os.environ:
            raise ValueError(
                "Gemini API key must be provided or set as GEMINI_API_KEY environment variable"
            )

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
```
ANSWER: [The direct answer to the user's question in natural language]

TRACEABILITY:
1. Entity Search:
   - Searched for: [entity name]
   - Selected: [entity label] (Wikidata ID: [Q-id])
   
2. Property Search:
   - Searched for: [property name]
   - Selected: [property label] (Wikidata ID: [P-id])
   
3. SPARQL Query:
[The enhanced SPARQL query that was executed, from the 'enhanced_query' field in the tool response]

4. Results Interpretation:
[Brief explanation of how the query results were interpreted to form the answer]

5. References:
   - [Reference URL if available]
   - Reference date: [Date in human-readable format if available]
   - [Any other reference information available]
```

If using Google Search (as fallback):
```
ANSWER: [The direct answer to the user's question in natural language]

TRACEABILITY:
1. Search Method: Web Search (used as fallback because [reason Wikidata was insufficient])
   - Initial Wikidata attempt: [Brief description of what was tried with Wikidata]
   - Reason for fallback: [Why Wikidata was insufficient - empty results, outdated, etc.]

2. Google Search Query:
   [The query sent to the Google Search tool]

3. Results Summary:
   [Brief summary of the search results used for the answer]

4. Sources:
   - [List of sources/citations from the search results]
```

Remember:
- Wikidata is your primary source - try it FIRST for ALL questions
- Only use Google Search as a fallback when:
  - Wikidata returns no results
  - The information in Wikidata is likely outdated (for recent events)
  - The question cannot be answered by structured data in Wikidata
- Be transparent about which source you're using
- Always include full traceability
- Include citation information from Google Search results when used

Common SPARQL prefixes for Wikidata:
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX pq: <http://www.wikidata.org/prop/qualifier/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX bd: <http://www.bigdata.com/rdf#>

Example SPARQL query for "Who is the president of France?":
```
SELECT ?president ?presidentLabel WHERE {
  wd:Q142 wdt:P35 ?president.
  ?president rdfs:label ?presidentLabel.
  FILTER(LANG(?presidentLabel) = "en")
}
```
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
            max_iterations=20,  # Limit number of iterations to prevent infinite loops
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