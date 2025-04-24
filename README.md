
# Wikidata Agent

A Python AI agent built with LangChain that answers questions by querying Wikidata. This agent uses Google's Gemini API to intelligently search for entities/properties and construct SPARQL queries.

## Features

* Search for entities and properties in Wikidata
* Execute SPARQL queries against Wikidata's SPARQL endpoint
* Intelligent query construction and refinement
* Generate SPARQL queries from natural language questions
* Evaluate agent's performance against test datasets

## Requirements

* Python 3.8+
* Google Gemini API key

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
   * Option 1: Create a `.env` file in the project root with:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```
   * Option 2: Provide the API key when prompted during runtime

## Project Structure

```
wikidata-agent/
├── requirements.txt     # Required Python packages
├── tools/               # LangChain tools for querying Wikidata
│   ├── __init__.py
│   ├── search_tool.py   # Tool for searching entities/properties
│   └── sparql_tool.py   # Tool for executing SPARQL queries
├── agent.py             # Agent implementation
├── evaluate.py          # Evaluation script
├── main.py              # CLI interface
└── README.md            # This file
```

## Usage

### Interactive Mode

Run the application in interactive mode:

```
python main.py
```

The interactive prompt will allow you to:

* Enter a question about something you want to know from Wikidata
* Get the generated SPARQL query and its results
* Exit the application with "exit", "quit", or "q"

Example questions:

1. "Who is the current president of France?"
2. "What is the capital of Japan and what is its population?"
3. "List the spouses of Albert Einstein"
4. "Which mountains in the Himalayas are higher than 8000 meters?"
5. "What books did Isaac Asimov write?"

### Evaluation Mode

To evaluate the agent's performance against a test dataset:

```
python main.py --mode evaluate --test-data path/to/test/data.json --output results.json
```

Or alternatively:

```
python evaluate.py --test-data path/to/test/data.json --output results.json
```

This will:

1. Load questions from the test data file
2. Generate SPARQL queries using the agent for each question
3. Compare the results with the ground truth
4. Calculate performance metrics (precision, recall, F1 score, etc.)
5. Save detailed results to the specified output file

## Evaluation Metrics

The evaluation compares the results of executing the agent's generated SPARQL query with the results of executing the ground truth query, using the following metrics:

* **Precision** : The fraction of retrieved results that are relevant
* **Recall** : The fraction of relevant results that are retrieved
* **F1 Score** : Harmonic mean of precision and recall
* **Jaccard Similarity** : Intersection over union of the result sets
* **TP, FP, FN, TN** : True positives, false positives, false negatives, true negatives

## How It Works

1. The agent analyzes your question to identify key entities and properties
2. It searches for these in Wikidata to get their unique identifiers (Q-ids for entities, P-ids for properties)
3. It constructs a SPARQL query using these identifiers
4. The agent executes the query against Wikidata's SPARQL endpoint and returns the results

## Limitations

* Complex questions with multiple entities or relationships may require multiple queries
* Some very specific or obscure entities may not be found in Wikidata
* SPARQL queries are subject to Wikidata's rate limits and service availability

## License

MIT License
