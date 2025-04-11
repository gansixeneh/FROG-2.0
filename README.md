# Wikidata Question Answering System

This is a Langchain-based system for answering questions using Wikidata as a knowledge source. The system uses a modular, tool-based approach to link entities, generate SPARQL queries, and produce natural language answers.

## Features

- Entity linking to Wikidata entities
- Property and ontology retrieval
- SPARQL query generation and execution
- Error correction for failed queries
- Natural language answer generation

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/wikidata-qa.git
   cd wikidata-qa
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key
   HF_TOKEN=your_huggingface_token
   ```

## Usage

### Command Line

You can ask a single question:

```
python main.py --question "Who is the president of Indonesia in 2024?"
```

Or run in interactive mode:

```
python main.py --interactive
```

### As a Library

```python
from tools.orchestrator import EnsembleOrchestratorTool, OrchestratorInput

# Initialize the orchestrator
orchestrator = EnsembleOrchestratorTool()

# Ask a question
input_data = OrchestratorInput(question="Who is the CEO of Apple?")
result = orchestrator._run(input_data)

# Print the answer
print(result["answer"])
```

## Tool Pipeline

1. `EntityLinkingTool` - Identifies entities in the question
2. `PropertyRetrievalTool` - Retrieves properties for identified entities
3. `OntologyRetrievalTool` - Retrieves class/type information (optional)
4. `SPARQLGenerationTool` - Generates SPARQL queries
5. `SPARQLExecutionTool` - Executes SPARQL queries
6. `QueryFixerTool` - Fixes failed queries
7. `AnswerGenerationTool` - Generates natural language answers
8. `EnsembleOrchestratorTool` - Coordinates the entire pipeline

## License

[MIT License](LICENSE)