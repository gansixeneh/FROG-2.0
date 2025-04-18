# Wikidata Agent

A Python AI agent built with LangChain that answers questions by querying Wikidata. This agent uses Google's Gemini API to intelligently search for entities/properties and construct SPARQL queries.

## Features

- Search for entities and properties in Wikidata
- Execute SPARQL queries against Wikidata's SPARQL endpoint
- Intelligent query construction and refinement
- Natural language answers based on query results

## Requirements

- Python 3.8+
- Google Gemini API key

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/wikidata-agent.git
   cd wikidata-agent
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Google Gemini API key:
   - Option 1: Create a `.env` file in the project root with:
     ```
     GOOGLE_API_KEY=your_gemini_api_key_here
     ```
   - Option 2: Provide the API key when prompted during runtime

## Project Structure

```
wikidata_agent/
├── requirements.txt   # Required Python packages
├── tools/             # LangChain tools for querying Wikidata
│   ├── __init__.py
│   ├── search_tool.py # Tool for searching entities/properties
│   └── sparql_tool.py # Tool for executing SPARQL queries
├── agent.py           # Agent implementation
├── main.py            # CLI interface
└── README.md          # This file
```

## Usage

Run the application:
```
python main.py
```

The interactive prompt will allow you to:
- Enter a question about something you want to know from Wikidata
- Exit the application with "exit", "quit", or "q"

Example questions:
1. "Who is the current president of France?"
2. "What is the capital of Japan and what is its population?"
3. "List the spouses of Albert Einstein"
4. "Which mountains in the Himalayas are higher than 8000 meters?"
5. "What books did Isaac Asimov write?"

## How It Works

1. The agent analyzes your question to identify key entities and properties
2. It searches for these in Wikidata to get their unique identifiers (Q-ids for entities, P-ids for properties)
3. It constructs a SPARQL query using these identifiers
4. The agent executes the query against Wikidata's SPARQL endpoint
5. If the results aren't satisfactory, it refines its query
6. Finally, it presents the answer in natural language

## Limitations

- Complex questions with multiple entities or relationships may require multiple queries
- Some very specific or obscure entities may not be found in Wikidata
- SPARQL queries are subject to Wikidata's rate limits and service availability

## License

MIT License