import os
from typing import Tuple
from dotenv import load_dotenv
from langchain_core.tools import BaseTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage

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
        system_message = """You are an AI assistant that generates SPARQL queries for Wikidata based on user questions and the given tools.
You have access to two tools:

1. search_entity_property: Use this to search for entities or properties in Wikidata.
2. execute_sparql: Use this to run SPARQL queries against Wikidata.

To generate a SPARQL query for a user's question, you MUST follow these steps:

1. Analyze the user's question and identify the key entities and properties that need to be looked up.
2. Use the search_entity_property tool to find the Wikidata IDs for these entities and properties.
3. Construct a SPARQL query using the identified entity and property IDs.
4. You can test your query using the execute_sparql tool to verify it works.
5. If the query results are insufficient or there's an error:
   - Revise your entities/properties or try a different SPARQL query
   - Search for additional entities or properties if needed
   - Execute the new SPARQL query
6. Once you have satisfactory results, return ONLY the final SPARQL query as the response, with appropriate prefixes.

Remember:
- Wikidata entities start with Q (like Q42 for Douglas Adams)
- Wikidata properties start with P (like P31 for "instance of")
- Use the search_entity_property tool to find entities/properties, do not infer the IDs by yourself.
- Make your SPARQL queries specific and focused
- Always include relevant entity/property IDs in your SPARQL queries

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
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
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

    def query(self, user_question: str) -> Tuple[str, dict]:
        """
        Process a user question and return a SPARQL query for Wikidata

        Args:
            user_question: The user's natural language question

        Returns:
            A tuple containing (SPARQL query, query results)
        """
        response = self.agent_executor.invoke({"input": user_question})
        output = response["output"]
        
        # Extract SPARQL query from the output
        # The model might wrap the query in code blocks or add explanations
        query = output
        
        # If query is wrapped in ```sparql ... ```, extract just the query
        if "```" in query:
            query_parts = query.split("```")
            for i, part in enumerate(query_parts):
                if i % 2 == 1:  # Odd-indexed parts are inside code blocks
                    # Remove "sparql" or other language indicators
                    query = part.strip()
                    if query.lower().startswith("sparql"):
                        query = query[6:].strip()
                    break
        
        # Execute the query to get results
        result = self.sparql_tool._run(query)
        
        return query, result