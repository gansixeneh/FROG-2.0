# University Property Retrieval System

This system provides Weaviate-based entity and property retrieval for university course data, using semantic search with embeddings and n-gram processing.

## Features

- **Weaviate Integration**: Connects to local Weaviate instance (port 8080)
- **Semantic Search**: Uses SentenceTransformers embeddings for semantic matching
- **N-gram Processing**: Generates unigrams, bigrams, and trigrams for comprehensive search
- **Automatic Population**: Populates Weaviate from TTL files using SPARQL queries
- **Score-based Filtering**: Uses actual Weaviate similarity scores for relevance filtering
- **Flattened Results**: Returns results as lists instead of nested dictionaries

## Installation

Make sure you have the required dependencies:

```bash
pip install pandas weaviate-client sentence-transformers rdflib
```

## Usage

### Basic Usage

```python
from property_retrieval import UniversityPropertyRetrieval

# Initialize the system
retrieval = UniversityPropertyRetrieval(
    turtle_file_path='final_result.ttl',
    get_entities_query=your_entities_query,
    get_properties_query=your_properties_query,
    embedding_model_name="jinaai/jina-embeddings-v3",
    is_local_client=True,
    weaviate_host="localhost",
    weaviate_port=8080,
)

# Search for entities
entity_results = retrieval.search_entities("machine learning", k=5)
print(entity_results)

# Search for properties
property_results = retrieval.search_properties("credits", k=5)
print(property_results)

# Get related candidates using n-grams
candidates = retrieval.get_related_candidates(
    "What courses have 3 credits?", 
    threshold=0.5, 
    k=5
)
```

### Integration with NL2SPARQL Generator

```python
from nl2sparql_generator import NL2SPARQLGenerator
from property_retrieval import UniversityPropertyRetrieval

# Initialize property retrieval
property_retrieval = UniversityPropertyRetrieval(
    turtle_file_path='final_result.ttl',
    get_entities_query=entities_query,
    get_properties_query=properties_query
)

# Initialize generator with property retrieval
generator = NL2SPARQLGenerator(
    config=schema,
    graph=rdf_graph,
    property_retrieval=property_retrieval
)

# Generate dataset - entities_matches and properties_matches will be flattened lists
dataset = generator.generate_dataset(size=100)
```

## SPARQL Queries

The system requires two SPARQL queries to populate Weaviate:

### Entities Query Example
```sparql
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label
    (REPLACE(STR(?entity), "http://example.org/", "ns1:") AS ?short)
WHERE {
  { 
    ?entity ?predicate ?object. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  UNION
  { 
    ?subject ?predicate ?entity. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  
  OPTIONAL {
    ?entity rdfs:label ?label.
  }
}
```

### Properties Query Example
```sparql
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label 
    (REPLACE(STR(?property), "http://example.org/", "ns1:") AS ?short) 
    (REPLACE(REPLACE(STR(?domain), "http://example.org/", "ns1:"), "http://www.w3.org/2000/01/rdf-schema#", "rdfs:") AS ?shortDomain)
    (REPLACE(REPLACE(STR(?range), "http://example.org/", "ns1:"), "http://www.w3.org/2001/XMLSchema#", "xsd:") AS ?shortRange)
WHERE {
  ?subject ?property ?object.
  FILTER(STRSTARTS(STR(?property), STR(ns1:)))
  
  OPTIONAL {
    ?property rdfs:label ?label.
    ?property rdfs:domain ?domain.
    ?property rdfs:range ?range.
  }
}
```

## Output Format

### Entity Results
```python
[
    {
        "id": "machine_learning",
        "label": "Machine Learning",
        "description": "Entity in the university course knowledge graph",
        "url": "//www.example.org/machine_learning",
        "score": 0.95
    }
]
```

### Property Results
```python
[
    {
        "id": "has_credits",
        "label": "has credits",
        "description": "Property linking course to integer",
        "url": "//www.example.org/Property:has_credits",
        "score": 0.89
    }
]
```

### Related Candidates
```python
{
    "entities": [
        "Machine Learning",
        "Computer Vision", 
        "Deep Learning"
    ],
    "properties": [
        "ns1:has_credits: {'domain': 'ns1:course', 'range': 'xsd:integer'}",
        "ns1:has_evaluation_method: {'domain': 'ns1:course', 'range': 'ns1:evaluation'}"
    ]
}
```

## Testing

Run the test script to verify everything works:

```bash
python test_property_retrieval.py
```

This will test entity search, property search, and related candidate generation.

## Files

- `property_retrieval/base.py` - Base class with Weaviate integration
- `property_retrieval/university.py` - University-specific implementation
- `property_retrieval/__init__.py` - Package initialization
- `test_property_retrieval.py` - Test script
- `example_usage.py` - Updated example with property retrieval integration
