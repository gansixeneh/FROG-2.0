# Wikidata Agent Backend

This is the Django backend for the Wikidata Agent chat application with multi-provider LLM support.

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key (required)
- Optional: Kaggle API credentials (for Kaggle models)
- Optional: Unsloth installation (for local fine-tuned models)

### Setup

1. Create a virtual environment:

   ```
   python -m venv venv
   ```
2. Activate the virtual environment:

- On Windows:

  ```
  venv\Scripts\activate
  ```
- On macOS/Linux:

  ```
  source venv/bin/activate
  ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```
4. **Optional dependencies** (install based on which LLM providers you want to use):

   ```bash
   # For Unsloth provider (local fine-tuned models)
   pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

   # For Kaggle provider (already included in requirements.txt)
   pip install kaggle
   ```
5. Create a `.env` file in the project root with your API keys:

   ```
   GEMINI_API_KEY=your_gemini_api_key_here

   # Optional: For Kaggle provider
   KAGGLE_USERNAME=your_kaggle_username
   KAGGLE_KEY=your_kaggle_api_key
   ```

   **Configuration options:**

   - `GEMINI_API_KEY`: **Required**. Your Google Gemini API key.
   - `KAGGLE_USERNAME` & `KAGGLE_KEY`: Optional. Required only if using Kaggle models for SPARQL generation.
6. Run database migrations:

   ```
   python manage.py makemigrations chat
   python manage.py migrate
   ```
7. Start the development server:

   ```
   python manage.py runserver
   ```

The server should now be running at http://localhost:8000.

## LLM Configuration System

The backend now supports multiple LLM providers through a configuration-based system:

### Supported Providers

1. **Gemini** - Google's Gemini models via API
2. **Unsloth** - Local fine-tuned models using Unsloth's FastLanguageModel
3. **Kaggle** - Models downloaded from Kaggle and loaded with Unsloth

### Configuration

The LLM configuration is stored in `config/llm_config.json`. You can customize which models are used for different tasks:

- **EntityExtractionNode**: Currently configured to use Unsloth with Qwen2.5-3B-Instruct-bnb-4bit
- **VerbalizationNode**: Uses Gemini 2.0 Flash
- **SparqlGenerationNode**: Configured to use a fine-tuned Kaggle model
- **AnswerGenerationNode**: Uses Gemini 1.5 Pro

### Testing the Configuration

Test your LLM factory setup:

```bash
python test_llm_factory.py
```

See example usage:

```bash
python example_llm_factory_usage.py
```

### Provider-Specific Setup

#### Unsloth Provider

- Requires Unsloth installation (see optional dependencies above)
- Loads models locally using `FastLanguageModel.from_pretrained()`
- Supports chat templates automatically
- Uses GPU memory - ensure adequate VRAM

#### Kaggle Provider

- Requires Kaggle API credentials in environment variables
- Downloads datasets automatically to `./kaggle_models/` directory
- Caches downloaded models to avoid re-downloading
- Uses Unsloth for model loading after download

#### Gemini Provider

- Uses Google's generative AI API
- Requires only the `GEMINI_API_KEY` environment variable
- No local storage requirements

## API Endpoints

-`GET /api/chats/` - List all chats

-`POST /api/chats/` - Create a new chat

-`GET /api/chats/<uuid>/` - Get a chat with all messages

-`DELETE /api/chats/<uuid>/` - Delete a chat

## WebSocket Connection

To connect to a chat via WebSocket, use the following URL:

```

ws://localhost:8000/ws/chat/<chat_uuid>/

```

You can send messages to the WebSocket in the following format:

```json

{

"message": "Your question here"

}

```

The WebSocket will send back messages in the following formats:

- Regular messages:

```json

{

"message": "Message content",

"role": "user|assistant|system"

}

```

- Debug messages:

```json

{

"debug": "Debug output content",

"role": "system"

}

```



# Apache Jena Visualization Analysis

This backend now integrates with Apache Jena Fuseki to store visualization logs in RDF format. This enables powerful semantic querying of agent execution patterns.

## Configuration

Ensure the following environment variable is set in your `.env` file:

```
APACHE_JENA_URL=http://localhost:3030
```

## Recommended SPARQL Queries

Use these queries on the Fuseki SPARQL endpoint (http://localhost:3030/visualization-logs/sparql) to analyze agent execution patterns:

### 1. List All Runs with Timestamps

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?run ?startTime ?endTime ?duration ?totalEvents
WHERE {
  ?run rdf:type logex:ConversionMetadata ;
       logex:startTime ?startTime ;
       logex:endTime ?endTime ;
       logex:totalDuration ?duration ;
       logex:totalEvents ?totalEvents .
} 
ORDER BY DESC(?startTime)
```

### 2. Find Runs with Specific Entities

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT DISTINCT ?run ?entityLabel ?startTime
WHERE {
  ?event log:hasEntity ?entity .
  ?event logex:belongsToRun ?run .
  ?entity rdfs:label ?entityLabel .
  ?run logex:startTime ?startTime .
  
  # Filter for specific entity (remove or change this filter as needed)
  FILTER(CONTAINS(LCASE(?entityLabel), "ma huateng"))
}
ORDER BY DESC(?startTime)
```

### 3. Find SPARQL Queries Used in Runs

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?run ?queryText ?startTime
WHERE {
  ?event log:hasQuery ?query .
  ?event logex:belongsToRun ?run .
  ?query rdfs:label ?queryText .
  ?run logex:startTime ?startTime .
}
ORDER BY DESC(?startTime)
```

### 4. Analyze Approach Distribution

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?approach (COUNT(?event) as ?count)
WHERE {
  ?event log:approach ?approach .
}
GROUP BY ?approach
ORDER BY DESC(?count)
```

### 5. Calculate Average Duration by Component

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logid: <https://sepses.ifs.tuwien.ac.at/id/log#>

SELECT ?component (AVG(?duration) as ?avgDuration) (COUNT(?event) as ?count)
WHERE {
  ?event log:pname ?componentUri ;
         log:duration ?duration .
  BIND(STRAFTER(STR(?componentUri), "log#") as ?component)
}
GROUP BY ?component
ORDER BY DESC(?avgDuration)
```

### 6. Find Most Common Entities

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>

SELECT ?entityLabel (COUNT(?entity) as ?count)
WHERE {
  ?event log:hasEntity ?entity .
  ?entity rdfs:label ?entityLabel .
}
GROUP BY ?entityLabel
ORDER BY DESC(?count)
LIMIT 20
```

### 7. Find Most Common Wikidata Properties

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>

SELECT ?propertyId (COUNT(?property) as ?count)
WHERE {
  ?query log:referencesProperty ?property .
  ?property log:wikidataId ?propertyId .
}
GROUP BY ?propertyId
ORDER BY DESC(?count)
LIMIT 20
```

### 8. Track Failed vs Successful SPARQL Queries

```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>

SELECT ?status (COUNT(?run) as ?count)
WHERE {
  {
    ?run logex:hasEventType ?eventType .
    ?eventType rdfs:label "all attempts failed" .
    BIND("failed" as ?status)
  }
  UNION
  {
    ?run logex:hasEventType ?eventType .
    ?eventType rdfs:label "successful query execution" .
    BIND("successful" as ?status)
  }
}
GROUP BY ?status
```

### 9. Analyze Query Performance Over Time

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX log: <https://w3id.org/sepses/ns/log#>
PREFIX logex: <https://w3id.org/sepses/ns/logex#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?date (AVG(?duration) as ?avgDuration) (COUNT(?run) as ?runCount)
WHERE {
  ?run logex:totalDuration ?duration ;
       logex:startTime ?startTime .
  BIND(SUBSTR(STR(?startTime), 1, 10) as ?date)
}
GROUP BY ?date
ORDER BY ?date
```

## Exporting Visualization Data

The visualization data is automatically stored in Apache Jena when queries are executed. You can:

1. Use the Fuseki web interface to browse and download the data
2. Use the generated TTL files for archiving or sharing
3. Import the data into other RDF stores or visualization tools

For more information about Apache Jena Fuseki, see the [official documentation](https://jena.apache.org/documentation/fuseki2/).
