import os
from typing import List
from dotenv import load_dotenv
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

from tools.search_tool import SearchWikidataTool
from tools.sparql_tool import ExecuteSPARQLTool


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
        self.tools = [self.search_tool, self.sparql_tool]

        # Create the system message with detailed instructions
        self.system_message = """You are an AI assistant that answers questions by querying Wikidata. 
You have access to two tools:

1. search_entity_property: Use this to search for entities or properties in Wikidata.
2. execute_sparql: Use this to run SPARQL queries against Wikidata.

To answer a user's question, follow these steps:

1. Analyze the user's question and identify the key entities and properties that need to be looked up.
2. Use the search_entity_property tool to find the Wikidata IDs for these entities and properties.
3. Construct a SPARQL query using the identified entities and properties.
4. Execute the SPARQL query using the execute_sparql tool.
5. If the query results are insufficient or there's an error:
   - Revise your entities/properties or try a different SPARQL query
   - Search for additional entities or properties if needed
   - Execute the new SPARQL query
6. Once you have satisfactory results, formulate a natural language response to the user's question.

Remember:
- Wikidata entities start with Q (like Q42 for Douglas Adams)
- Wikidata properties start with P (like P31 for "instance of")
- Make your SPARQL queries specific and focused
- Always include relevant entity/property IDs in your SPARQL queries
- Format your final answer in a clear, concise way for the user

Important SPARQL tips:
- Use PREFIX wdt: <http://www.wikidata.org/prop/direct/>
- Use PREFIX wd: <http://www.wikidata.org/entity/>
- Add LIMIT to your queries (default is 5)
- Use labels with ?entity rdfs:label ?label . FILTER(LANG(?label) = "en")

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

        # Initialize the model and agent
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
        self.agent = create_tool_calling_agent(
            self.llm, self.tools, self.system_message
        )
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,  # Limit number of iterations to prevent infinite loops
        )

    def query(self, user_question: str) -> str:
        """
        Process a user question and return an answer based on Wikidata

        Args:
            user_question: The user's natural language question

        Returns:
            A natural language answer based on Wikidata information
        """
        response = self.agent_executor.invoke({"input": user_question})
        return response["output"]
