# Comprehensive Overview: Curriculum Dataset Generation for Fine-tuning

## Introduction

This codebase implements two sophisticated approaches for generating a curriculum dataset designed for fine-tuning language models on Natural Language to SPARQL (NL2SPARQL) translation tasks, specifically focused on university course data. The system creates question-SPARQL pairs with varying complexity levels and includes rich metadata for training.

---

## Template-Based Approach

### Architecture Overview

The template-based approach uses predefined question-query templates that are instantiated with real entities and properties from the knowledge graph through a discovery-first methodology.

### Core Components & Flow

#### 1. Schema Extraction (kg_schema_extractor.py)

Purpose: Extract structured schema information from the university TTL file.

Key Process:

# Extracts entities, properties, and their categorizations

def extract_from_file(self, file_path, format='turtle'):

    self.graph = Graph()

    self.graph.parse(file_path, format=format)

    self.parse_university_course_graph(self.graph)

What it extracts:

* Entity Types: Courses, research groups, evaluation methods, etc.
* Properties: Categorized as numeric, date, text, or boolean
* Entity Examples: Sample instances with labels
* Relationships: Domain/range information for properties

Schema Structure:

schema_info = {

    "properties": [{"value": "ns1:has_credits", "label": "has credits", "uri": "..."}],

    "types": [{"value": "ns1:course", "label": "course", "uri": "..."}],

    "numericProperties": [...],  # Credit values, etc.

    "dateProperties": [...],     # Date-related properties

    "textProperties": [...]      # String properties

}

#### 2. Property Retrieval System (property_retrieval.py)

Purpose: Weaviate-based semantic search for entities and properties.

Key Features:

* Embedding-based search: Uses sentence transformers for semantic similarity
* Hybrid search: Combines keyword and vector search
* N-gram generation: Creates search terms from questions
* Entity/Property matching: Finds relevant candidates for question context

Search Process:

def search_entities(self, q: str, k: int = 5):

    query_vector = self.model_embed.encode([q])[0]

    response = collection.query.hybrid(

    query=q,

    query_properties=["label"],

    vector=query_vector,

    limit=k

    )

#### 3. Template System (nl2sparql_generator.py)

Template Categories by Complexity:

##### Basic Templates (40% of dataset)

Simple one-hop relationships:

{

    "id": "course-credits",

    "questionTemplates": [

    "How many credits does the {entity} course have?",

    "What is the credit value for {entity}?",

    "Can you tell me the number of credits for the {entity} course?"

    ],

    "sparqlTemplate": """

    SELECT ?value WHERE {

    {entity} ns1:has_credits ?value .

    }

    """,

    "complexity": "basic"

}

##### Intermediate Templates (30% of dataset)

Two-hop relationships and aggregations:

{

    "id": "courses-by-research-group",

    "questionTemplates": [

    "Which courses are associated with the {entity} research group?",

    "What courses are developed by the {entity} research team?"

    ],

    "sparqlTemplate": """

    SELECT ?course WHERE {

    ?course a ns1:course .

    ?course ns1:has_research_group {entity} .

    }

    """,

    "complexity": "intermediate"

}

##### Advanced Templates (30% of dataset)

Complex multi-hop relationships with filters and nested patterns:

{

    "id": "courses-with-same-prerequisites",

    "questionTemplates": [

    "Which courses have the same prerequisites as {entity}?",

    "Find courses sharing the same prerequisite requirements as {entity}."

    ],

    "sparqlTemplate": """

    SELECT DISTINCT ?course WHERE {

    {entity} ns1:has_prerequisite_course ?prereq .

    ?course ns1:has_prerequisite_course ?prereq .

    FILTER(?course != {entity})

    }

    """,

    "complexity": "advanced"

}

#### 4. Discovery-First Template Instantiation

Key Innovation: Instead of randomly selecting entities, the system uses discovery queries to find valid combinations that guarantee results.

Process:

1. Extract Placeholders:

def extract_placeholders(self, template):

    pattern = r"{\s*([a-zA-Z0-9_]+)\s*}"

    # Finds: {entity}, {entity1}, {value}, etc.

2. Create Discovery Query:

def create_all_placeholders_discovery_query(self, template, placeholders):

    # Converts template: {entity} ns1:has_credits ?value

    # To discovery: SELECT ?entity ?value WHERE { ?entity ns1:has_credits ?value }

3. Execute and Select:

results = list(self.graph.query(discovery_query))

selected = random.choice(results)  # Guaranteed valid combination

4. Instantiate Template:

* Replace placeholders with actual values
* Convert prefixed URIs to full URIs
* Format SPARQL for readability

#### 5. Chain of Thoughts Generation

Purpose: Generate step-by-step reasoning for question-to-SPARQL translation.

Template Example:

"thoughtsTemplate": [

    "1. The question asks for the credit value of {entity}.",

    "2. The entity '{entity}' represents a course in the university domain.",

    "3. The property 'ns1:has_credits' links a course to its credit value.",

    "4. To solve this, retrieve the credit value linked to {entity} via the 'ns1:has_credits' property.",

    "5. Construct a SPARQL query to retrieve the credit value for {entity}."

]

Replacement Logic:

* Uses context-aware replacement (URI vs label based on sentence context)
* Maps placeholders to actual entities/properties from discovery results

#### 6. Entity/Property Matching

Purpose: Generate training data for entity linking and property matching.

Process:

1. Extract URIs from SPARQL query
2. Get labels from RDF graph using rdfs:label
3. Generate n-grams from question text
4. Search Weaviate for semantically similar entities/properties
5. Filter by relevance threshold (0.6)

Output Format:

{

    "entities": ["Advanced Database", "Machine Learning"],

    "properties": ["has credits", "has prerequisite course"],

    "entities_matches": [{"id": "ns1:advanced_database", "label": "Advanced Database"}],

    "properties_matches": [{"id": "ns1:has_credits", "label": "has credits"}]

}

---

## Random Walk (Pattern-Based) Approach

### Architecture Overview

The random walk approach is actually a pattern discovery system that uses graph traversal to find valid multi-hop patterns and generates SPARQL queries based on actual graph structure.

### Core Logic (rw/rw_curi.py)

#### 1. Pattern Categories

The system generates three types of patterns based on the number of properties involved:

##### 1-Property Patterns (50% - Basic)

Direct subject-predicate-object relationships:

# Subject Target: ?target prop fixed_entity

# Object Target: fixed_entity prop ?target

def generate_1_property_patterns(self, count=100):

    discovery_query = """

    SELECT DISTINCT ?prop ?entity WHERE {

    ?s ?prop ?entity .

    FILTER(STRSTARTS(STR(?prop), "http://example.org/"))

    FILTER(STRSTARTS(STR(?entity), "http://example.org/"))

    }

    """

Generated Patterns:

* ?target ns1:has_research_group ns1:machine_learning_and_computer_vision
* ns1:advanced_database ns1:has_credits ?target

##### 2-Property Patterns (30% - Intermediate)

Two-hop relationships with intermediate nodes:

Middle Target Pattern:

# entity1 prop1 ?target . ?target prop2 entity2

SELECT ?target WHERE {

    ns1:advanced_database ns1:has_prerequisite_course ?target .

    ?target ns1:has_credits 3 .

}

Branching Pattern:

# ?target prop1 ?hidden . ?hidden prop2 entity

SELECT ?target WHERE {

    ?target ns1:has_prerequisite_course ?hidden .

    ?hidden ns1:has_research_group ns1:reliable_software_engineering .

}

Discovery Process:

middle_discovery_query = """

    SELECT DISTINCT ?prop1 ?prop2 ?entity1 ?entity2 ?middle WHERE {

    ?entity1 ?prop1 ?middle .

    ?middle ?prop2 ?entity2 .

    FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))

    FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))

    FILTER(?prop1 != ?prop2)

    }

"""

##### 3-Property Patterns (20% - Advanced)

Complex three-hop relationships:

Linear End Pattern:

# entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target

SELECT ?target WHERE {

    ns1:machine_learning ns1:has_prerequisite_course ?h1 .

    ?h1 ns1:has_course_category ?h2 .

    ?h2 ns1:has_evaluation_method ?target .

}

Star Pattern:

# ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target

SELECT ?target WHERE {

    ?hidden ns1:has_research_group ns1:machine_learning_and_computer_vision .

    ?hidden ns1:has_course_category ns1:study_program_elective_course .

    ?hidden ns1:has_evaluation_method ?target .

}

#### 2. Pattern Variation Generation

Key Innovation: Each pattern type generates multiple variations using bit manipulation:

def _create_linear_end_pattern(self, data, pattern_index):

    variation = random.randint(0, 7)  # 8 variations (2^3)

    # Use bit pattern to determine triple direction

    if variation & 1:  # bit 0: reverse first triple

    pattern_parts.append(f"?hidden1 {props_str[0]} {entity_str}")

    else:

    pattern_parts.append(f"{entity_str} {props_str[0]} ?hidden1")

Result: Each 3-property pattern can generate 8 different structural variations, increasing dataset diversity.

#### 3. Validation System

Critical Feature: Every generated pattern is validated against the actual graph:

def _validate_pattern(self, sparql_query):

    try:

    results = list(self.graph.query(sparql_query))

    return len(results) > 0  # Must have at least one result

    except Exception as e:

    return False

This ensures all generated queries are executable and meaningful.

#### 4. Question Generation Gap

Problem: The random walk approach generates valid SPARQL patterns but lacks natural language questions and reasoning chains.

Solution: The hybrid approach described below.

---

## Hybrid Approach: Bridging Template and Random Walk

### The Missing Piece Problem

The random walk approach produces diverse, valid SPARQL queries but lacks:

1. Natural language questions
2. Chain of thoughts reasoning

### Solution: LLM-Assisted Enhancement

#### 1. Generation Process (rw/rw_merger.py)

def merge_json_files():

    # Read pattern-based SPARQL queries

    with open('curi_pattern_based.json', 'r') as file1:

    pattern_data = json.loads(file1.read())

    # Read LLM-generated questions/thoughts

    with open('curi_claude.json', 'r') as file2:

    llm_data = json.loads(file2.read())

    # Merge by ID

    for item in pattern_data:

    if item['id'] in llm_dict:

    item['question'] = llm_dict[item['id']]['question']

    item['thoughts'] = llm_dict[item['id']]['thoughts']

#### 2. LLM Prompting Strategy

Context Provided to LLM:

* SPARQL Query: The pattern-based query
* Entities: Extracted from query with labels
* Properties: Extracted from query with labels
* Template Examples: From template-based approach
* Domain Context: University course information

LLM Task:

1. Generate natural, diverse questions that would result in the given SPARQL query
2. Create step-by-step reasoning (chain of thoughts)
3. Ensure questions sound natural and varied

#### 3. Quality Control (rw/rw_simplifier.py)

Entity/Property Filtering:

def filter_matches(matches_list, used_identifiers):

    # Only include entities/properties actually used in SPARQL

    return [match for match in matches_list if match['id'] in used_identifiers]

This ensures training data consistency between questions and SPARQL queries.

---

## Post-Processing Pipeline

### SPARQL Formatting (post_processing.py)

Standardization Process:

1. Keyword Capitalization: select → SELECT
2. URI Prefixing: [http://example.org/course](http://example.org/course) → ns1:course
3. Indentation: Proper WHERE clause formatting
4. Special Clause Handling: FILTER, UNION, GROUP BY formatting

def format_sparql_query(query):

    # Comprehensive formatting with proper indentation

    # Handles nested structures, special clauses

    return formatted_query

### Dataset Splitting

Final Output:

* Training Set: 100 examples
* Test Set: 50 examples
* Random Sampling: If dataset > 150 examples

---

## Validation System (validate_sparql.py)

### Comprehensive Testing

Validation Process:

1. Parse TTL File: Load university course graph
2. Execute Each Query: Against actual RDF data
3. Result Analysis: Count successful queries, empty results, errors
4. Statistics Generation: Complexity distribution, template usage

Output Metrics:

* Success rate by complexity level
* Average results per query
* Most common query patterns
* Error analysis

---

## Key Innovations & Design Decisions

### 1. Discovery-First Methodology

Instead of random entity selection, both approaches use graph exploration to find valid combinations, ensuring all generated queries are meaningful and executable.

### 2. Complexity Stratification

Three-tier complexity system (basic/intermediate/advanced) ensures balanced training data across difficulty levels.

### 3. Multi-Modal Training Data

Each example includes:

* Natural language question
* SPARQL query
* Chain of thoughts reasoning
* Entity/property matches
* Complexity metadata

### 4. Semantic Enhancement

Weaviate integration provides semantic search capabilities for entity linking training.

### 5. Pattern Variation

Systematic generation of query variations increases dataset diversity while maintaining correctness.

---

## Comparison: Template vs Random Walk

| Aspect             | Template-Based           | Random Walk             |
| ------------------ | ------------------------ | ----------------------- |
| Question Quality   | High (hand-crafted)      | Requires LLM assistance |
| SPARQL Diversity   | Limited by templates     | High (graph-driven)     |
| Pattern Coverage   | Predefined patterns      | Discovered patterns     |
| Scalability        | Manual template creation | Automatic discovery     |
| Complexity Control | Explicit                 | Emergent from graph     |
| Validation         | Template-guaranteed      | Discovery-guaranteed    |

---

## Usage Scenarios

### Template-Based: Best For

* Controlled generation with specific question types
* Educational datasets with clear learning objectives
* Domain-specific patterns that are well-understood

### Random Walk: Best For

* Large-scale generation with minimal manual effort
* Discovery of novel patterns in complex graphs
* Comprehensive coverage of graph relationships

### Hybrid: Best For

* Maximum diversity with natural questions
* Research applications requiring both coverage and quality
* Production systems needing robust training data

This comprehensive system represents a sophisticated approach to curriculum dataset generation, combining the reliability of template-based methods with the discovery power of graph-based exploration, enhanced by modern LLM capabilities for natural language generation.

# GESIS Dataset Generation: Comprehensive Technical Overview

This codebase implements two distinct approaches for generating high-quality Natural Language to SPARQL (NL2SPARQL) training datasets for the GESIS Knowledge Graph, a scholarly research domain. Let me provide a detailed breakdown of both approaches.

## Architecture Overview

The system operates on the GESIS Knowledge Graph, which contains scholarly publications, authors, organizations, and research data using Schema.org and custom GESIS vocabularies. The codebase supports two complementary generation strategies:

1. Template-Based Approach: Domain-specific, semantically meaningful queries
2. Random Walk Approach: Graph-structure-driven, pattern-based queries

---

## 1. Template-Based Approach

### Core Components and Flow

#### 1.1 Schema Extraction (kg_schema_extractor.py)

Purpose: Extracts comprehensive schema information from the GESIS Knowledge Graph

Dual Operation Modes:

* CSV Mode (Preferred): Uses pre-extracted CSV files for efficiency
* SPARQL Mode (Fallback): Direct queries against Fuseki endpoint

Extraction Process:

# Key extraction queries for GESIS domain

get_entities_query = """

PREFIX schema: [https://schema.org/](https://schema.org/)

SELECT DISTINCT ?entity ?name ?type WHERE {

  ?entity schema:name ?name .

  OPTIONAL { ?entity rdf:type ?type }

  FILTER(isIRI(?entity))

}

"""

Schema Information Extracted:

* Entity Types: CreativeWork, Person, Organization, Dataset
* Properties: author, publisher, datePublished, about, keywords
* Property Categories: Numeric (publication counts), Date (publication years), Text (titles, descriptions)
* Entity Examples: Sample entities for each type with labels

#### 1.2 Entity/Property Retrieval System (property_retrieval.py)

Weaviate Integration:

* Uses jinaai/jina-embeddings-v3 for semantic embeddings
* Creates separate collections for entities and properties
* Enables semantic matching between natural language and KG elements

Search Functionality:

def search_entities(self, q: str, k: int = 5) -> pd.DataFrame:

    query_vector = self.model_embed.encode([q])[0]

    response = collection.query.hybrid(

    query=q,

    query_properties=["label"],

    vector=query_vector,

    limit=k

    )

#### 1.3 Template Definition and Structure (nl2sparql_generator.py)

Template Architecture: Each template contains:

* Question Templates: Multiple natural language variations
* SPARQL Template: Parameterized query pattern
* Thoughts Template: Step-by-step reasoning explanation
* Complexity Level: Basic, Intermediate, Advanced
* Category: Domain classification (scholarly)

Example Template:

{

    "id": "publication-author",

    "category": "scholarly",

    "questionTemplates": [

    "Who is the author of '{entity}'?",

    "Who wrote '{entity}'?",

    "Who created '{entity}'?"

    ],

    "sparqlTemplate": """

    SELECT ?authorName WHERE {

    {entity} schema:author ?author .

    ?author schema:name ?authorName .

    }

    """,

    "complexity": "basic",

    "thoughtsTemplate": [

    "1. The question asks for the author of '{entity}'.",

    "2. In GESIS KG, authorship is via schema:author property.",

    "3. Find author entity using schema:author.",

    "4. Retrieve author name using schema:name.",

    "5. Return the author name(s)."

    ]

}

#### 1.4 Discovery-Based Template Instantiation

Discovery Query Generation: The system creates discovery queries to find valid entity-property combinations:

def create_discovery_query(self, template, placeholders):

    # Extract WHERE clause from template

    where_clause = extract_where_clause(template)

    # Replace placeholders with variables

    for placeholder in placeholders:

    where_clause = replace_placeholder(where_clause, placeholder)

    # Build discovery query

    discovery_query = f"""

    SELECT DISTINCT {placeholder_vars} WHERE {{

    {where_clause}

    OPTIONAL {{ ?entity rdfs:label ?entityLabel }}

    }} LIMIT 100

    """

Instantiation Process:

1. Execute discovery query to find valid combinations
2. Randomly select valid entity-property pairs
3. Replace template placeholders with actual values
4. Generate natural language question
5. Create chain-of-thought reasoning
6. Format final SPARQL query

#### 1.5 Complexity Levels and Pattern Types

Basic Templates (40% of dataset):

* Single property queries
* Direct subject-object relationships
* Examples: "Who authored X?", "When was X published?"

Intermediate Templates (30% of dataset):

* Aggregation queries (COUNT, MAX, MIN)
* Multi-step reasoning
* Examples: "How many publications has X authored?", "What is X's latest work?"

Advanced Templates (30% of dataset):

* Complex aggregations with grouping/ordering
* Multi-entity relationships
* Examples: "Who is the top expert on topic Y?", "Which publication has most authors?"

### Template-Based Output Format

Each generated item contains:

{

    "id": "q1",

    "question": "Who is the author of 'Social Media Analysis Study'?",

    "sparql": "SELECT ?authorName WHERE { <...> schema:author ?author . ?author schema:name ?authorName . }",

    "category": "scholarly",

    "complexity": "basic",

    "templateId": "publication-author",

    "thoughts": ["1. Question asks for author...", "2. Use schema:author property...", ...],

    "entities": ["Social Media Analysis Study"],

    "properties": ["author", "name"],

    "entities_matches": [{"id": "uri", "label": "name"}],

    "properties_matches": [{"id": "schema:author", "label": "author"}]

}

---

## 2. Random Walk Approach

### Core Philosophy

The Random Walk approach discovers structural patterns directly from the knowledge graph without predefined semantic templates. It generates queries based on graph topology and property relationships.

#### 2.1 Pattern Discovery Engine (rw/gen.py)

Three Pattern Complexity Levels:

##### 2.1.1 One-Property Patterns (50% weight)

Discovery Strategy:

discovery_query = f"""

SELECT DISTINCT ?prop ?entity WHERE {{

    ?s ?prop ?entity .

    FILTER(STRSTARTS(STR(?prop), "https://schema.org/") ||

    STRSTARTS(STR(?prop), "https://data.gesis.org/gesiskg/schema/"))

    FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))

    FILTER({exclusion_filters})

}} LIMIT 1000

"""

Pattern Variations:

* Subject Target: ?target prop fixed_entity
* Object Target: fixed_entity prop ?target

Example Generated Pattern:

SELECT ?target WHERE {

    ?target schema:author[https://data.gesis.org/gesiskg/resource/person-123](https://data.gesis.org/gesiskg/resource/person-123) .

}

##### 2.1.2 Two-Property Patterns (30% weight)

Pattern Types:

Literal Target Pattern:

SELECT ?target WHERE {

    <fixed_entity> schema:author ?hidden .

    ?hidden schema:name ?target .

}

Branching Pattern (4 variations using bit manipulation):

variations = [

    f"?target {prop1} ?hidden . ?hidden {prop2} {entity}",  # original

    f"?hidden {prop1} ?target . {entity} {prop2} ?hidden",  # both swapped

    f"?target {prop1} ?hidden . {entity} {prop2} ?hidden",  # second swapped

    f"?hidden {prop1} ?target . ?hidden {prop2} {entity}",  # first swapped

]

##### 2.1.3 Three-Property Patterns (20% weight)

Pattern Topologies:

Linear End Pattern:

SELECT ?target WHERE {

    fixed_entity prop1 ?h1 .

    ?h1 prop2 ?h2 .

    ?h2 prop3 ?target .

}

Linear Middle Pattern:

SELECT ?target WHERE {

    entity1 prop1 ?hidden .

    ?hidden prop2 ?target .

    ?target prop3 entity2 .

}

Star Pattern:

SELECT ?target WHERE {

    ?hidden prop1 entity1 .

    ?hidden prop2 entity2 .

    ?hidden prop3 ?target .

}

#### 2.2 Pattern Validation and Quality Control

Validation Process:

1. Execute each generated pattern against SPARQL endpoint
2. Verify pattern returns non-empty results
3. Filter out patterns with execution errors
4. Exclude low-quality properties (system properties, very common properties)

Property Exclusion Strategy:

excluded_properties = {

    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",

    "https://schema.org/hasPart",

    "https://data.gesis.org/gesiskg/schema/duplicate"

}

excluded_namespaces = {

    "http://www.w3.org/2000/01/rdf-schema#"  # Exclude all RDFS properties

}

#### 2.3 Entity and Property Extraction

For each generated SPARQL pattern, the system extracts:

Entity URIs: Full URIs enclosed in angle brackets Property Identifiers: Prefixed properties (schema:author, gesiskg:libraryLocation)

def extract_entities_and_properties(sparql_query):

    entity_pattern = r'<([^>]+)>'

    entity_uris = set(re.findall(entity_pattern, sparql_query))

    property_pattern = r'(\w+:\w+)'

    property_ids = set(re.findall(property_pattern, sparql_query))

    return entity_uris, property_ids

### Random Walk Output Format

{

    "id": "q1",

    "sparql": "SELECT ?target WHERE { ?target schema:author <entity_uri> . }",

    "pattern_type": "1_prop_subject_target",

    "complexity": "basic",

    "entities": ["Entity Name"],

    "properties": ["author"],

    "entities_matches": [{"id": "full_uri", "label": "Entity Name"}],

    "properties_matches": [{"id": "schema:author", "label": "author"}]

}

---

## 3. Question and Thought Generation for Random Walk

### 3.1 The Bridge: Template-to-Random Walk Context Transfer

Since Random Walk patterns are structurally generated without semantic context, the system uses a sophisticated approach to generate natural language questions and reasoning:

#### 3.2 Context Generation Process (rw/rw_merger.py)

Step 1: Pattern Analysis

* Analyze SPARQL structure to understand query intent
* Extract entities, properties, and relationships
* Determine query complexity and pattern type

Step 2: Template Contextualization

* Use template-based questions/thoughts as examples
* Create contextual prompts for LLM generation
* Maintain consistency with GESIS domain vocabulary

Step 3: LLM Prompting Strategy

# Example prompt context:

context = f"""

Based on these template examples:

Template: "Who is the author of '{{entity}}'?"

SPARQL: "SELECT ?authorName WHERE {{ {{entity}} schema:author ?author . ?author schema:name ?authorName . }}"

Thoughts: ["1. Question asks for author...", "2. Use schema:author property..."]

Generate question and thoughts for:

SPARQL: "{random_walk_sparql}"

Entities: {entities}

Properties: {properties}

"""

#### 3.3 Merging Process

File Flow:

1. gesis_rw.json - Raw Random Walk patterns
2. gesis_claude.json - LLM-generated questions/thoughts
3. gesis.json - Merged final dataset

def merge_json_files():

    # Read RW patterns and LLM generations

    rw_data = json.load('gesis_rw.json')

    llm_data = json.load('gesis_claude.json')

    # Create lookup dictionary

    llm_dict = {item['id']: item for item in llm_data}

    # Merge by ID

    for item in rw_data:

    if item['id'] in llm_dict:

    item['question'] = llm_dict[item['id']]['question']

    item['thoughts'] = llm_dict[item['id']]['thoughts']

---

## 4. Post-Processing and Quality Enhancement

### 4.1 SPARQL Query Formatting (post_processing.py)

Formatting Operations:

1. Keyword Capitalization: SELECT, WHERE, FILTER → uppercase
2. URI Prefix Replacement: Full URIs → prefixed forms
3. Query Structure Formatting: Proper indentation and spacing
4. Special Clause Handling: UNION, OPTIONAL, FILTER formatting

def format_sparql_query(query):

    # Handle WHERE clause structure

    before_where, after_where = query.split("WHERE", 1)

    # Format content with indentation

    indented_content = format_where_content(content)

    # Rebuild formatted query

    formatted_query = f"{before_where}\nWHERE {{\n{indented_content}\n}}"

### 4.2 Dataset Splitting and Sampling

Final Dataset Preparation:

* Random sampling if > 150 items
* 70-30 train-test split (100-50 items)
* Shuffle for random distribution
* Quality validation for each query

---

## 5. Technical Infrastructure

### 5.1 SPARQL Endpoint Integration

Fuseki Server Connection:

* Primary endpoint: http://localhost:3030/gesis/query
* SPARQLWrapper for query execution
* JSON result format processing
* Error handling and retry logic

### 5.2 Vector Database (Weaviate) Integration

Embedding Storage:

* Separate collections for entities and properties
* Jina embeddings v3 for semantic similarity
* Hybrid search (keyword + vector)
* Real-time similarity scoring

### 5.3 CSV Optimization Strategy

Performance Enhancement:

* Pre-extract entities/properties to CSV
* Fallback to SPARQL when CSV unavailable
* Faster template instantiation
* Reduced endpoint load

---

## 6. Quality Assurance and Validation

### 6.1 Query Validation (validate_gesis_sparql.py)

Validation Process:

* Execute each generated query against endpoint
* Measure execution time and result count
* Identify slow queries (>2 seconds)
* Generate execution statistics

### 6.2 Entity/Property Matching Quality

Matching Validation:

* Verify entities_matches contain actual query entities
* Ensure properties_matches reflect query properties
* Filter irrelevant matches using query analysis
* Maintain semantic consistency

---

## 7. Comparative Analysis: Template vs Random Walk

### Template-Based Advantages:

* Semantic Consistency: Domain-aware question generation
* Reasoning Quality: Expert-crafted chain-of-thought explanations
* Query Diversity: Multiple complexity levels with meaningful intent
* Domain Coverage: Comprehensive scholarly domain patterns

### Random Walk Advantages:

* Structural Diversity: Discovers unexpected graph patterns
* Scalability: Automatically finds valid entity-property combinations
* Pattern Coverage: Explores graph topology systematically
* Novelty: Generates patterns not captured by templates

### Hybrid Strategy Benefits:

* Comprehensive Coverage: Templates for semantics + RW for structure
* Quality Enhancement: LLM-generated questions with RW diversity
* Balanced Dataset: Both meaningful and structurally diverse queries
* Domain Adaptation: GESIS-specific vocabulary with general patterns

This comprehensive approach creates a high-quality, diverse NL2SPARQL dataset that combines semantic understanding with structural exploration, perfectly suited for fine-tuning language models on scholarly knowledge graph querying tasks.

# Comprehensive Overview of Legal Dataset Generation Approaches

## Introduction

The codebase implements two distinct approaches for generating a legal dataset intended for fine-tuning language models on natural language to SPARQL translation tasks in the legal domain:

1. Template-based approach: Uses predefined question templates and corresponding SPARQL query templates
2. Random walk approach: Generates SPARQL queries based on discovered graph patterns with increasing complexity

Both approaches leverage the same underlying knowledge graph containing Indonesian legal documents, accessed through a Fuseki SPARQL endpoint. Let me provide a detailed breakdown of each approach.

## Knowledge Graph Foundation

The underlying knowledge graph (modified-lex2kg) contains Indonesian legal documents with properties such as:

* Document metadata (title, enactment date, location)
* Document structure (chapters, articles, sections)
* Document relationships (references, amendments)
* Enactment information (who enacted, position of enactor)

## Template-Based Approach

### Overview Flow

1. Schema Extraction: Extract classes, properties, and sample entities from the knowledge graph
2. Template Definition: Define question-SPARQL templates for various legal query types
3. Template Instantiation: Fill templates with real entities and properties from the knowledge graph
4. Entity/Property Matching: Use vector embeddings to identify entities and properties mentioned in questions
5. Thought Chain Generation: Generate step-by-step reasoning explanations
6. Variation Generation: Create variations of questions for the same SPARQL query
7. Post-processing: Format SPARQL queries and export the dataset

### Detailed Process

#### 1. Knowledge Graph Schema Extraction (kg_schema_extractor.py)

This component extracts schema information from the Fuseki endpoint:

extractor = KGSchemaExtractor({"debug": True, "sparql_endpoint": endpoint_url})

schema = extractor.extract_schema()

The extraction process:

* Identifies all classes/types in the knowledge graph
* Extracts properties and their domains/ranges
* Categorizes properties (numeric, date, text, boolean)
* Collects sample entities for each class
* Generates human-readable labels for entities and properties

The legal_entity_label() and legal_property_label() functions transform URIs into readable labels specifically tailored for the Indonesian legal domain, handling special cases like dates, document numbers, and legal terminology.

#### 2. Property Retrieval System Initialization (property_retrieval.py)

This component creates a vector database using Weaviate to match natural language questions with relevant entities and properties:

property_retrieval = LegalPropertyRetrieval(

    endpoint_url=endpoint_url + "/query",

    embedding_model_name="jinaai/jina-embeddings-v3",

    is_local_client=True,

    weaviate_host="localhost",

    weaviate_port=8080

)

It:

* Creates embeddings for all entities and properties
* Provides search functionality based on semantic similarity
* Supports n-gram based search for multi-word terms
* Returns ranked lists of relevant entities and properties

#### 3. Template Definition and Dataset Generation (nl2sparql_generator.py)

The core of the template-based approach is the NL2SPARQLGenerator class:

generator = NL2SPARQLGenerator(

    schema,

    endpoint_url=endpoint_url + "/query",

    property_retrieval=property_retrieval

)

dataset = generator.generate_dataset(

    size=200,

    complexity_distribution={

    "basic": 0.4,

    "intermediate": 0.3,

    "advanced": 0.3,

    },

    include_variations=False,

    variations_per_question=2,

)

##### Template Structure

Each template defines:

* Question templates in Indonesian and English
* SPARQL query template with placeholders
* Step-by-step reasoning templates ("thoughts")
* Complexity level and category

Example template for law title queries:

{

    "id": "law-title",

    "category": "legal",

    "questionTemplates": [

    "Apa judul dari {entity}?",

    "Apa nama dari {entity}?",

    "Bagaimana judul dari {entity}?"

    ],

    "englishQuestionTemplates": [

    "What is the title of {entity}?",

    "What is the name of {entity}?",

    "How is the title of {entity}?"

    ],

    "sparqlTemplate": """

    SELECT ?title WHERE {

    {entity} lex2kg-o:tentang ?title .

    }

    """,

    "thoughtsTemplate": [

    "1. The question asks for the title of {entity}.",

    "2. The entity '{entity}' represents a legal document in the Indonesian legal system.",

    "3. The property 'lex2kg-o:tentang' links a legal document to its title or subject matter.",

    "4. To solve this, retrieve the title linked to {entity} via the 'lex2kg-o:tentang' property.",

    "5. Construct a SPARQL query to retrieve the title for {entity}."

    ],

    "complexity": "basic"

}

##### Template Instantiation Logic

The instantiate_template_with_discovery() method uses a discovery-first approach:

1. Create a "discovery query" based on the template's SPARQL pattern
2. Execute this query to find valid entity-property combinations
3. Randomly select one valid combination
4. Apply the selected values to all placeholders in the question and SPARQL templates

This ensures the generated SPARQL queries will always return results when executed against the knowledge graph.

##### Entity/Property Matching

For each question-SPARQL pair, the system identifies entities and properties:

1. Extract entity and property URIs from the SPARQL query
2. Generate human-readable labels for these entities and properties
3. Use the property_retrieval system to search for matching entities and properties from the question text
4. Record these matches in the dataset for training

##### Chain of Thoughts Generation

For each question-SPARQL pair, a detailed reasoning chain is generated:

1. Use the thoughtsTemplate from the selected template
2. Replace placeholders with actual entity and property information
3. Apply formatting and context-sensitive replacements to create natural-sounding reasoning steps

##### Variation Generation

The VariationGenerator creates alternative phrasings for questions:

1. Legal-specific variations (e.g., "Apa judul dari" → "Apa nama dari", "Bagaimana judul dari")
2. General variations (adding "please", "Could you tell me...", "I want to know...")

#### 4. Post-Processing (post_processing.py)

This component formats and prepares the final dataset:

1. Format SPARQL queries (uppercase keywords, proper indentation)
2. Replace full URIs with prefixed forms
3. Clean up spacing and formatting
4. Split into training and testing sets

## Random Walk Approach

### Overview Flow

1. Schema Extraction: Extract entities and properties from the knowledge graph
2. Pattern Discovery: Discover valid graph patterns with different complexities
3. Query Generation: Generate SPARQL queries based on discovered patterns
4. Validation: Ensure generated queries return results
5. Entity/Property Matching: Identify entities and properties in the queries
6. Merging: Combine with template-based questions and thoughts
7. Post-processing: Format and prepare the final dataset

### Detailed Process

#### 1. Pattern-Based SPARQL Generator Initialization (rw/gen.py)

generator = PatternBasedSPARQLGenerator(

    endpoint_url,

    custom_prefixes

)

This initializes:

* Connection to the SPARQL endpoint
* Extraction of entities and properties
* Pattern weights for different complexity levels
* Property retrieval system for entity/property matching

#### 2. Pattern Discovery and Generation

The generator discovers valid graph patterns of increasing complexity:

##### 1-Property Patterns (Basic)

These patterns involve a single triple pattern with one property and one fixed entity:

1. Subject Target: ?target property fixedEntity

   * Example: ?target lex2kg-o:tentang [https://example.org/lex2kg/uu/2020/9](https://example.org/lex2kg/uu/2020/9)
   * Question: "What has UU No. 9 Tahun 2020 as its subject?"
2. Object Target: fixedEntity property ?target

   * Example: [https://example.org/lex2kg/uu/2020/9](https://example.org/lex2kg/uu/2020/9) lex2kg-o:tentang ?target
   * Question: "What is the subject of UU No. 9 Tahun 2020?"

##### 2-Property Patterns (Intermediate)

These patterns involve two triple patterns connecting entities through properties:

1. Middle Target: entity1 prop1 ?target . ?target prop2 entity2

   * Example: [https://example.org/lex2kg/uu/2020/9](https://example.org/lex2kg/uu/2020/9) lex2kg-o:pasal ?target . ?target lex2kg-o:versi [https://example.org/lex2kg/uu/2020/9/pasal/0001/versi/20200901](https://example.org/lex2kg/uu/2020/9/pasal/0001/versi/20200901)
   * Question: "Which article in UU No. 9 Tahun 2020 has version 20200901?"
2. Branching: ?target prop1 ?hidden . ?hidden prop2 entity

   * Example: ?target lex2kg-o:pasal ?hidden . ?hidden lex2kg-o:disahkanPada [https://example.org/lex2kg/ontology/tanggal/20200901](https://example.org/lex2kg/ontology/tanggal/20200901)
   * Question: "Which law has articles enacted on September 1, 2020?"

##### 3-Property Patterns (Advanced)

These patterns involve three triple patterns with various configurations:

1. Linear End: entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target

   * Example: [https://example.org/lex2kg/uu/2020/9](https://example.org/lex2kg/uu/2020/9) lex2kg-o:bab ?h1 . ?h1 lex2kg-o:pasal ?h2 . ?h2 lex2kg-o:ayat ?target
   * Question: "What sections are in the articles of chapters in UU No. 9 Tahun 2020?"
2. Linear Middle: entity1 prop1 ?h . ?h prop2 ?target . ?target prop3 entity2

   * Example: [https://example.org/lex2kg/uu/2020/9](https://example.org/lex2kg/uu/2020/9) lex2kg-o:bab ?h . ?h lex2kg-o:pasal ?target . ?target lex2kg-o:ayat [https://example.org/lex2kg/uu/2020/9/pasal/0001/ayat/0001](https://example.org/lex2kg/uu/2020/9/pasal/0001/ayat/0001)
   * Question: "Which article in UU No. 9 Tahun 2020 contains section 0001?"
3. Star: ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target

   * Example: ?hidden lex2kg-o:disahkanOleh [https://example.org/lex2kg/pejabat/presiden](https://example.org/lex2kg/pejabat/presiden) . ?hidden lex2kg-o:tahun "2020" . ?hidden lex2kg-o:pasal ?target
   * Question: "What articles are in laws enacted by the president in 2020?"

#### 3. Pattern Variations

For each pattern type, multiple variations are generated by:

* Reversing the direction of individual triple patterns
* Combining different directions in multi-triple patterns
* Using bit manipulation to systematically generate all possible variations

For example, with 3 triple patterns, there are 2³ = 8 possible variations based on whether each triple is reversed or not.

#### 4. Query Validation

Each generated query is validated against the knowledge graph:

def _validate_pattern(self, sparql_query):

    """Check if pattern has results in the endpoint"""

    try:

    result = self.client.query(sparql_query)

    return (

    result

    and result["results"]["bindings"]

    and len(result["results"]["bindings"]) > 0

    )

    except Exception as e:

    print(f"Error validating query: {e}")

    return False

This ensures that only queries that return results are included in the dataset.

#### 5. Dataset Generation Process

The generate_dataset() method:

1. Calculates the number of patterns to generate for each complexity level
2. Generates patterns for each complexity level
3. Extracts entities and properties from each SPARQL query
4. Adds simple placeholder questions
5. Executes entity/property matching using the same method as the template-based approach

dataset = generator.generate_dataset(size=250)

#### 6. Merging with Template-Based Approach

The rw_merger.py script combines the random walk patterns with template-based questions and thoughts:

# Read the content from both files

with open('legal_rw.json', 'r') as file1:

    paste1_data = json.loads(file1.read())

with open('legal_claude.json', 'r') as file2:

    paste2_data = json.loads(file2.read())

# Create a dictionary from paste2 data for easy lookup by id

paste2_dict = {item['id']: item for item in paste2_data}

# Create a new list with updated items

merged_data = []

for item in paste1_data:

    # Check if this item exists in paste2

    if item['id'] in paste2_dict:

    # Update question and thoughts fields

    item['question'] = paste2_dict[item['id']]['question']

    item['thoughts'] = paste2_dict[item['id']]['thoughts']

    merged_data.append(item)

This merging indicates that the questions and thoughts for the random walk patterns were generated separately, likely using an LLM like Claude, and then merged with the pattern-generated SPARQL queries.

## Validation and Post-Processing

Both approaches include validation and post-processing steps:

1. SPARQL Query Validation: Running queries against the Fuseki endpoint to verify they return results
2. Query Formatting: Standardizing query format, capitalizing keywords, adding proper indentation
3. Entity/Property Mapping: Linking entities and properties to their mentions in questions
4. Dataset Splitting: Dividing the dataset into training and testing sets

## Comparison of Approaches

### Template-Based Approach Strengths:

* Directly generates well-formed questions with corresponding SPARQL queries
* Includes detailed reasoning steps (thoughts)
* Focuses on legal domain-specific question types
* Provides question variations to improve generalization

### Random Walk Approach Strengths:

* Discovers a wider variety of graph patterns
* More systematically explores the knowledge graph structure
* Potentially generates more diverse SPARQL queries
* Provides better coverage of complex relationship patterns

### Combined Approach:

The two approaches complement each other, with the template-based approach providing natural language questions and reasoning, and the random walk approach providing diverse SPARQL patterns.

## Conclusion

This codebase implements a sophisticated methodology for generating a high-quality legal dataset for training natural language to SPARQL translation models. The combination of template-based and random walk approaches ensures both diversity in SPARQL patterns and high-quality natural language questions with reasoning steps.

The generated dataset would be valuable for training models to handle legal document queries in both Indonesian and English, with a particular focus on Indonesian legal terminology and document structure.

# Comprehensive Analysis of FrOG (Framework of Open GraphRAG) Codebase

## 🏗️ Architecture Overview

Your codebase implements a sophisticated multi-agent GraphRAG system that combines knowledge graphs, large language models, and real-time visualization. Here's the detailed breakdown:

## 📋 Table of Contents

1. [High-Level Architecture](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#high-level-architecture)
2. [Backend Deep Dive](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#backend-deep-dive)
3. [Frontend Architecture](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#frontend-architecture)
4. [Agent Processing Flow](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#agent-processing-flow)
5. [Knowledge Graph Integration](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#knowledge-graph-integration)
6. [Real-time Communication](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#real-time-communication)
7. [Visualization &amp; Logging](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#visualization--logging)
8. [Configuration &amp; Settings](https://claude.ai/chat/cc373c7e-b862-48d6-9617-d53ac69532ab#configuration--settings)

---

## 🏛️ High-Level Architecture

### System Components

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐

│   React Frontend │◄──►│  Django Backend │◄──►│ Knowledge Graphs │

│   (TypeScript)   │    │   (Python)      │    │   (SPARQL)      │

└─────────────────┘    └─────────────────┘    └─────────────────┘

    │                       │                       │

    │              ┌─────────────────┐              │

    └──────────────►│   Agent System  │◄─────────────┘

    │   (LangGraph)   │

    └─────────────────┘

    │

    ┌─────────────────────────────┐

    │                             │

    ┌─────────▼──────┐          ┌─────────▼──────┐

    │ Apache Jena    │          │   Weaviate     │

    │ (RDF Storage)  │          │ (Vector Store) │

    └────────────────┘          └────────────────┘

### Technology Stack

* Backend: Django + Django Channels (WebSocket)
* Agent Framework: LangGraph (graph-based multi-agent processing)
* LLM Providers: Google Gemini, Ollama (local models)
* Knowledge Graphs: Wikidata, Curriculum KB, Legal KB, GESIS
* Vector Storage: Weaviate
* RDF Storage: Apache Jena Fuseki
* Frontend: React + TypeScript + Tailwind CSS
* Real-time: Pusher + WebSocket
* Visualization: Mermaid diagrams, RDF triples

---

## 🔧 Backend Deep Dive

### 1. Django Application Structure

#### Core Apps

* chat/: Handles chat sessions, WebSocket connections, and message routing
* agent/: Contains the main agent logic and LangGraph implementation
* wikidata_web/: Django project settings and configuration

#### Key Models (chat/models.py)

class Chat(models.Model):

    id = UUIDField(primary_key=True)  # Unique chat session

    title = CharField(max_length=255)  # Auto-generated from first message

    created_at = DateTimeField(auto_now_add=True)

    updated_at = DateTimeField(auto_now=True)

class Message(models.Model):

    chat = ForeignKey(Chat)

    role = CharField(choices=['user', 'assistant', 'system'])

    content = TextField()  # Message content

    created_at = DateTimeField(auto_now_add=True)

### 2. Agent System Architecture

#### Agent Singleton Pattern (agent/singletons.py)

class AgentSingleton:

    """Prevents creating multiple agent instances per API key"""

    _agents: Dict[str, FROGAgent] = {}

    @classmethod

    def get_agent(cls, api_key: str, debug_callback: Optional[Callable] = None):

    """Returns existing agent or creates new one"""

Purpose: Optimizes memory usage by reusing agent instances across WebSocket connections.

#### Main Agent Class (agent/agent.py)

class FROGAgent:

    def__init__(self, gemini_api_key: str, debug_callback=None):

    # Initialize LangGraph agent

    self.langgraph_agent = FROGGraphAgent(...)

    # Setup debug handler for real-time updates

    self.debug_handler = DebugHandler(debug_callback)

    def query(self, user_question: str, settings: dict = None) -> tuple:

    """Main entry point for question processing"""

    return self.langgraph_agent.query(user_question, settings=settings)

### 3. LangGraph Multi-Agent Implementation

#### Graph Structure (agent/langgraph/agent.py)

The agent uses a directed graph where each node represents a processing step:

def build_graph(self):

    workflow = StateGraph(FROGGraphRAGState)

    # Add processing nodes

    workflow.add_node("translation", TranslationNode())

    workflow.add_node("entity_extraction", EntityExtractionNode())

    workflow.add_node("strategy_selection", StrategySelectionNode())

    workflow.add_node("verbalization", VerbalizationNode())

    workflow.add_node("property_generation", PropertyGenerationNode())

    workflow.add_node("sparql_generation", SparqlGenerationNode())

    workflow.add_node("answer_generation", AnswerGenerationNode())

    workflow.add_node("google_search", GoogleSearchNode())

    # Define execution flow

    workflow.set_entry_point("translation")

    workflow.add_edge("translation", "entity_extraction")

    # ... complex conditional routing

#### Processing Nodes

1. TranslationNode (nodes/translation.py)

* Detects input language using Google Translate
* Translates non-English queries to English
* Preserves original language for response translation

2. EntityExtractionNode (nodes/entity_extraction.py)

* Uses LLM to extract entities and properties from questions
* Configurable LLM provider (Gemini/Ollama)
* Returns structured JSON with entities and properties

3. StrategySelectionNode (nodes/strategy_selection.py)

* Decides between verbalization vs SPARQL generation
* Logic: Single entity questions → verbalization, Complex questions → SPARQL

4. VerbalizationNode (nodes/verbalization.py)

* Retrieves entity information using semantic similarity
* Uses sentence transformers for embedding comparison
* Fallback to SPARQL if similarity score < 0.6

5. PropertyGenerationNode (nodes/property_generation.py)

* Enhances entity properties using vector search
* Combines N-gram analysis with semantic search
* Different retrieval strategies per knowledge source

6. SparqlGenerationNode (nodes/sparql_generation.py)

* Generates SPARQL queries using LLM
* Multi-attempt strategy (up to 5 tries)
* Query validation and error handling
* Automatic entity label resolution

7. AnswerGenerationNode (nodes/answer_generation.py)

* Synthesizes final natural language response
* Uses retrieved context and query results
* Supports multi-language responses

8. GoogleSearchNode (nodes/google_search.py)

* Fallback when knowledge graph methods fail
* Uses Google's Generative AI with search tools
* Extracts and resolves citation URLs

#### State Management (utils/state.py)

class FROGGraphRAGState(BaseModel):

    question: str

    translated_question: Optional[str] = None

    extracted_entities: List[str] = []

    sparql_query: Optional[str] = None

    query_result: List[Dict] = []

    final_answer: Optional[str] = None

    approach_used: Optional[str] = None  # "verbalization", "sparql", "google_search"

    # ... 20+ state variables tracking the entire process

### 4. Multi-LLM Factory Pattern

#### LLM Factory (llm_factory/factory.py)

class LLMFactory:

    def__init__(self, config_path: str = "config/llm_config.json"):

    self.config = load_llm_config(config_path)

    self._model_cache: Dict[str, BaseLLMProvider] = {}

    def get_model_for_entity_extraction(self) -> BaseLLMProvider:

    return self.get_model("EntityExtractionNode")

    def get_model_for_sparql_generation(self) -> BaseLLMProvider:

    return self.get_model("SparqlGenerationNode")

#### Provider Implementations

* GeminiProvider: Google's Gemini models via API
* OllamaProvider: Local models via Ollama server
* Extensible: Easy to add new providers (OpenAI, Anthropic, etc.)

#### Configuration (config/llm_config.json)

{

  "default": {

    "provider": "gemini",

    "model": "gemini-2.0-flash",

    "config": {"temperature": 0.2}

  },

  "nodes": {

    "EntityExtractionNode": {

    "provider": "ollama",

    "model": "qwen:3b-instruct",

    "config": {"temperature": 0.2}

    }

  }

}

---

## 🎨 Frontend Architecture

### 1. React Application Structure

#### Component Hierarchy

App.tsx

├── Header.tsx (Navigation, settings, new chat)

├── SideNav.tsx (Chat history, navigation)

├── ChatArea.tsx (Message display)

│   ├── ChatMessage.tsx (Individual messages)

│   ├── SystemMessageGroup.tsx (Agent reasoning trace)

│   └── VisualizationFiles.jsx (Download links)

└── MessageInput.tsx (User input, send messages)

#### Context Management (context/ChatContext.tsx)

interface ChatContextType {

  chats: Chat[]

  currentChat: ChatWithMessages | null

  isProcessing: boolean

  settings: AgentSettings

  sendMessage: (content: string) => void

  updateSettings: (settings: AgentSettings) => void

}

### 2. Real-time Communication

#### Pusher Integration (services/pusherService.ts)

export class PusherService {

  subscribeToChat(chatId: string, callbacks: {

    onMessage?: (data: PusherMessage) => void

    onDebugMessage?: (data: PusherMessage) => void

    onSystemMessage?: (data: PusherMessage) => void

  })

}

#### Message Types

* Chat Messages: User questions and agent responses
* Debug Messages: Real-time agent reasoning steps
* System Messages: Status updates and errors
* Visualization Messages: File download links

### 3. Advanced UI Features

#### Agent Reasoning Visualization

const SystemMessageGroup: React.FC = ({ messages }) => {

  // Collapsible debug trace with syntax highlighting

  // Auto-scroll to bottom for real-time updates

  // Frog-themed styling with terminal aesthetics

}

#### Settings Management

* Knowledge Source Selection: Wikidata, Curriculum, Legal, GESIS
* Processing Toggles: Translation, Verbalization, Google Search
* Persistent Storage: LocalStorage with defaults

#### Markdown Rendering

* SPARQL Syntax Highlighting: Automatic code formatting
* Link Processing: Auto-linkification of URLs
* Table Support: Responsive query result tables

---

## 🔄 Agent Processing Flow

### Detailed Execution Sequence

Input Processing

 User Question → Translation Node → Language Detection

├─ English: Pass through

└─ Non-English: Translate to English

Entity & Property Extraction

 Translated Question → LLM Analysis → JSON Output

{

  "entities": ["Albert Einstein", "spouses"],

  "properties": ["spouse", "married to", "partner"]

}

Strategy Selection

 Entities Count + Question Complexity → Decision

├─ Simple + Single Entity → Verbalization Path

└─ Complex + Multiple Entities → SPARQL Path

Verbalization Path (for simple questions)

 Entity → Knowledge Graph Lookup → Property Verbalization

→ Semantic Similarity Calculation → Answer (if score > 0.6)

→ Fallback to SPARQL (if score ≤ 0.6)

SPARQL Path (for complex questions)

 Properties → Vector Search Enhancement → SPARQL Generation

→ Query Execution → Result Processing → Answer Generation

Fallback Mechanisms

 SPARQL Fails → Google Search (if enabled)

→ Web Results → Citation Processing → Final Answer

### Error Handling & Retries

#### SPARQL Generation Retry Logic

attempts_left = state.try_threshold  # Default: 5

while attempts_left > 0:

    try:

    # Generate SPARQL query

    # Execute query

    if results:

    return success

    else:

    attempts_left -= 1

    # Modify question for retry

    except Exception:

    attempts_left -= 1

#### Graceful Degradation

* Verbalization Fails → SPARQL Generation
* SPARQL Fails → Google Search (if enabled)
* All Methods Fail → Informative error message

---

## 🌐 Knowledge Graph Integration

### 1. Multi-Source Architecture

#### Knowledge Source Metadata (config/knowledge_graph_metadata.json)

{

  "wikidata": {

    "name": "Wikidata",

    "endpoint": "https://query.wikidata.org/sparql",

    "prefixes": {"wd": "http://www.wikidata.org/entity/"},

    "supports_references": true

  },

  "curriculum": {

    "name": "Curriculum KB",

    "endpoint": "${APACHE_JENA_URL}/curi/query",

    "supports_references": false

  }

}

#### Dynamic Endpoint Configuration

* Environment Variable Substitution: ${APACHE_JENA_URL} → actual URL
* Source-Aware SPARQL Wrapper: Automatic endpoint switching
* Metadata-Driven Prefixes: Each source has its own namespace prefixes

### 2. Property Retrieval System

#### Factory Pattern (utils/property_retrieval_factory.py)

class PropertyRetrievalFactory:

    def get_property_retriever(self, knowledge_source: str):

    if knowledge_source == "wikidata":

    return WikidataPropertyRetrieval(df_properties)

    elif knowledge_source == "curriculum":

    return UniversityPropertyRetrieval()

    # ... other sources

#### Weaviate Integration

* Vector Storage: Property and entity embeddings
* Hybrid Search: Combines keyword and semantic search
* Per-Source Collections: Separate vector spaces for each knowledge graph

#### Search Strategies

def get_related_candidates(self, query: str, threshold: float = 0.6):

    # 1. N-gram generation from query

    # 2. Vector similarity search

    # 3. Threshold filtering

    # 4. Result ranking and deduplication

### 3. SPARQL Query Generation

#### Template-Based Generation

* Metadata-Driven Templates: Each source has custom SPARQL patterns
* Automatic Prefix Injection: Based on knowledge source
* Entity URI Formatting: Source-specific URI patterns

#### Query Enhancement Features

* Reference Integration: Automatic citation retrieval (Wikidata)
* Label Resolution: Entity URIs → Human-readable labels
* Query Optimization: DISTINCT, LIMIT, ORDER BY injection

---

## 📡 Real-time Communication

### 1. WebSocket Architecture

#### Django Channels Setup (chat/consumers.py)

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):

    # Join chat room

    # Initialize agent with debug callback

    self.agent = get_agent(api_key=gemini_api_key, debug_callback=self.debug_callback)

    async def debug_callback(self, output):

    # Real-time agent reasoning updates

    # Emoji decoration for different node types

    await self.send(text_data=json.dumps({

    'debug': decorated_output,

    'role': 'system'

    }))

#### Node-Specific Emoji Mapping

node_emojis = {

    "Translation Node": "🌍",

    "Entity Extraction Node": "🕵️",

    "Strategy Selection Node": "🔀",

    "Verbalization Node": "🗣️",

    "SPARQL Generation Node": "⚙️",

    "Answer Generation Node": "🎁",

    "Google Search Node": "🔍"

}

### 2. Pusher Fallback System

#### Dual Communication Channels

* Primary: Django Channels WebSocket
* Fallback: Pusher cloud service
* Automatic Switching: Based on connection availability

#### Message Deduplication

const processedMessageIds = new Set`<string>`()

const handlePusherMessage = (data: PusherMessage) => {

  if (processedMessageIds.has(data.message_id)) return

  processedMessageIds.add(data.message_id)

  // Process message

}

---

## 📊 Visualization & Logging

### 1. Apache Jena Integration

#### RDF Logging System (utils/visualization.py)

class LogToRDF:

    def__init__(self, run_id=None, approach_used=None):

    # RDF namespace definitions

    self.LOG = Namespace("https://w3id.org/sepses/ns/log#")

    self.LOGEX = Namespace("https://w3id.org/sepses/ns/logex#")

    def add_log_event(self, log_entry):

    # Convert execution logs to RDF triples

    # SLOGERT approach for semantic logging

#### Automatic Upload

class JenaUploader:

    def upload_ttl(self, ttl_content, graph_name=None):

    # Automatic dataset creation

    # TTL content upload to Fuseki

    # Named graph organization

### 2. Visualization Components

#### Mermaid Diagram Generation

def save_mermaid_diagram(self):

    # Component-based subgraphs

    # Event sequence visualization

    # Color-coded node types

    # Duration and timing information

#### Multi-Format Export

* JSON: Complete execution trace with metadata
* Mermaid: Visual process flow diagram
* TTL: RDF triples for semantic analysis

### 3. Analytics Queries

#### Pre-built SPARQL Queries (components/JenaLogsModal.tsx)

* Run Analysis: Duration, success rates, approach distribution
* Entity Tracking: Most common entities across runs
* Property Usage: Frequently used Wikidata properties
* Performance Metrics: Average processing time by component
* Error Analysis: Failed vs successful query patterns

---

## ⚙️ Configuration & Settings

### 1. Runtime Configuration

#### Agent Settings (types/index.ts)

interface AgentSettings {

  useVerbalization: boolean    // Enable verbalization strategy

  useGoogleSearch: boolean     // Allow web search fallback

  useTranslation: boolean      // Auto-translate non-English

  knowledgeSource: "wikidata" | "curriculum" | "legal" | "gesis"

}

#### Dynamic Setting Updates

* Real-time Application: Settings affect next query immediately
* Persistent Storage: Browser localStorage for user preferences
* Default Fallbacks: Graceful handling of missing settings

### 2. Environment Configuration

#### Backend Environment Variables

GEMINI_API_KEY=your_api_key

APACHE_JENA_URL=http://localhost:3030

WEAVIATE_URL=localhost

WEAVIATE_HTTP_PORT=8080

#### Frontend API Configuration

const API_HOST = process.env.REACT_APP_API_HOST || 'boss-amoeba-flying.ngrok-free.app'

const API_PROTOCOL = API_HOST.includes('localhost') ? 'http' : 'https'

### 3. Docker & Infrastructure

#### Weaviate Setup (backend/weaviate/docker-compose.yml)

services:

  weaviate:

    image: semitechnologies/weaviate:latest

    ports: ["8080:8080", "50052:50051"]

    environment:

    AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'

    PERSISTENCE_DATA_PATH: '/var/lib/weaviate'

#### Apache Jena Setup (fuseki-data/start_apache_jena.sh)

# Automatic dataset configuration

# Multi-source endpoint setup

# TTL data initialization

---

## 🚀 Key Innovation Points

### 1. Multi-Strategy Question Answering

* Dynamic routing between verbalization and SPARQL based on question complexity
* Semantic similarity scoring for strategy validation
* Graceful fallback mechanisms

### 2. Real-time Agent Reasoning Transparency

* Live WebSocket updates of agent processing steps
* Detailed execution tracing with emoji-coded node types
* User-friendly visualization of complex multi-step reasoning

### 3. Multi-Source Knowledge Graph Integration

* Metadata-driven configuration for different knowledge sources
* Automatic SPARQL template adaptation per source
* Unified interface for heterogeneous knowledge graphs

### 4. Comprehensive Execution Analytics

* RDF-based semantic logging following SLOGERT methodology
* Apache Jena integration for sophisticated SPARQL analytics
* Multi-format visualization export (JSON, Mermaid, TTL)

### 5. Flexible LLM Architecture

* Provider-agnostic factory pattern
* Per-node LLM configuration
* Easy integration of new model providers

### 6. Production-Ready Features

* Agent instance caching for performance
* Message deduplication across communication channels
* Graceful error handling and retry mechanisms
* Responsive UI with mobile support

This codebase represents a sophisticated implementation of GraphRAG that combines the power of knowledge graphs with modern LLM capabilities, providing transparent, real-time, and analytically rich question-answering experiences.

# FROG: Fine-Tuned GraphRAG Implementation - Detailed Technical Explanation

## Overview

Your codebase implements FROG (Fine-Tuned GraphRAG), a sophisticated framework for enhancing language models' ability to interact with knowledge graphs through natural language. The system fine-tunes specialized models to extract entities/properties from questions and generate SPARQL queries, while also incorporating a verbalization component for direct answers when possible.

## Core Architecture

FROG consists of four main components, implemented across the provided notebooks:

1. Entity & Property Extraction Model: Fine-tuned to identify relevant entities and properties from natural language questions
2. SPARQL Generation Model: Fine-tuned to convert identified entities/properties into executable SPARQL queries
3. Verbalization System: Provides direct answers for simple queries without needing SPARQL
4. Property Retrieval System: Uses vector search to find relevant properties in the knowledge graph

Your implementation supports two knowledge graph domains:

* Wikidata: A large-scale public knowledge graph (frog-wikidata-*.ipynb)
* CURI: A university course knowledge graph (frog-curi-*.ipynb)

## Technical Implementation Details

### Fine-tuning Architecture

Both fine-tuning notebooks (frog-wikidata-finetune.ipynb and frog-curi-finetune.ipynb) follow similar patterns:

def load_model(model_name: str):

    model, tokenizer = FastLanguageModel.from_pretrained(

    model_name=model_name,

    max_seq_length=max_seq_length,

    dtype=dtype,

    load_in_4bit=load_in_4bit,

    )

    # Chat template setup...

    return model, tokenizer

You're using Unsloth's FastLanguageModel with 4-bit quantization for memory efficiency.

For both entity extraction and SPARQL generation, you implement LoRA (Low-Rank Adaptation) with different configurations:

# Entity-Property Extraction (lighter configuration)

model = FastLanguageModel.get_peft_model(

    model,

    r=16,                     # Smaller rank for simpler task

    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",

    "gate_proj", "up_proj", "down_proj"],

    lora_alpha=16,

    lora_dropout=0,

    bias="none",

    # Additional parameters...

)

# SPARQL Generation (heavier configuration)

model = FastLanguageModel.get_peft_model(

    model,

    r=64,                     # Larger rank for complex syntax learning

    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",

    "gate_proj", "up_proj", "down_proj",],

    lora_alpha=64,            # Matching r

    lora_dropout=0.1,         # Higher dropout for better generalization

    bias="all",               # Bias adaptation for syntax patterns

    use_rslora=True,          # Rank-stabilized LoRA

    # Additional parameters...

)

This shows how you've carefully tuned the parameters - using a smaller rank for the simpler entity extraction task, and a larger rank with more regularization for the complex SPARQL generation task.

### Data Preparation & Formatting

Your data formatting is particularly sophisticated, with carefully crafted prompt templates:

# For entity-property extraction

system_prompt = """You are an expert entity and property extractor for knowledge graph querying. Your task is to analyze a natural language question and identify the relevant entities and properties needed to create a SPARQL query for Wikidata.

Guidelines:

1. For each question, extract ALL entities mentioned in the question
2. For each question, extract ALL relevant properties needed to answer the question
3. Format your response as a structured JSON object with 'entities' and 'properties' keys

...

"""

# For SPARQL generation

system_prompt = """You are a SPARQL generator expert for Wikidata knowledge graph. Your task is to convert the following natural language question to a SPARQL query for Wikidata using the provided entity and property resolutions.

Guidelines:

1. First identify which entities from the list match the question's intent
2. Identify which entities are relevant to the question and select EXACTLY ONE entity ID for each distinct concept

...

"""

This demonstrates how you've created specialized instructions for each model to perform its specific task.

### Pipeline Workflow

The evaluation notebooks (frog-wikidata-eval(37).ipynb and frog-curi-eval.ipynb) implement the full pipeline:

Entity & Property Extraction:

 def extract_entities_and_properties(questions, model_path):

    # Load model

    model, tokenizer = load_model(model_path)

    pipe = get_pipeline(model, tokenizer)

    # For each question, extract entities and properties

    # Format as JSON with {entities: [...], properties: [...]}

Entity URI Resolution:

 def get_entity_uris(extraction_df):

    # For each extracted entity, find the most appropriate URI

    # Uses LLM to disambiguate between candidates

Verbalization Attempt:

 def verbalize_entities(extraction_df):

    # For each entity URI, try to generate direct answers

    # Calculate similarity scores between question and candidate answers

SPARQL Generation (if verbalization score < 0.6):

 def generate_sparql(extraction_df, model_path, try_threshold=5):

    # Check verbalization score

    if verbalization_score >= 0.6:

    # Use verbalization results

    else:

    # Generate SPARQL query

    # Try up to try_threshold times if execution fails

### Vector Search Implementation

You implement sophisticated vector search for property retrieval using Weaviate:

class WikidataPropertyRetrieval:

    def__init__(

    self,

    df_properties: pd.DataFrame,

    embedding_model_name: str = "jinaai/jina-embeddings-v3",

    ):

    # Initialize embedding model and Weaviate collection

    def _search(self, q: str, k: int = 5):

    # Generate query vector

    query_vector = self.model_embed.encode([q])[0]

    # Perform hybrid search

    response = self.collection.query.hybrid(

    query=q,

    query_properties=["label"],

    vector=query_vector,

    return_metadata=wvc.query.MetadataQuery(score=True),

    limit=k,

    )

    def _preprocess_into_tokens(self, q: str):

    # Tokenize and remove stopwords

    def _generate_ngrams(self, tokens: list[str]):

    # Generate n-grams for more robust matching

    def get_related_candidates(self, q: str, property_candidates: list[str] = []):

    # Use n-grams and candidate properties to find matches

    # Filter by similarity threshold

This shows your implementation of a hybrid search approach that combines keyword matching with vector similarity, enhanced with n-gram generation for better matching.

### Verbalization Implementation

The verbalization component is particularly interesting:

class WikidataVerbalization:

    SENTENCE_TEMPLATE = "{s}'s {p} is {o}"

    def run(self, question: str, entity: str):

    # Get candidate sentences from knowledge graph

    list_of_candidates, po, sp = self.get_list_of_candidates(entity)

    # Encode question and candidates

    question_embed = self.model_embed.encode(question)

    passages_embed = self.model_embed.encode(cands)

    # Find most similar candidate

    similarities = self.model.similarity(question_embed, passages_embed)

    similar_index = np.argmax(similarities)

    similar_score = max(similarities)

    # Extract results based on the most similar property

    property_used = list(list_of_candidates.keys())[similar_index]

    # Return results and similarity score

This demonstrates how you're using semantic similarity between the question and knowledge graph triples to provide direct answers when possible.

### Evaluation Framework

Your evaluation framework is comprehensive:

def evaluate_batch_results(results_df, ground_truth_queries, questions, complexities):

    # Execute ground truth and generated queries

    # Compare results using precision, recall, F1, etc.

    # Group by complexity for more detailed analysis

def calculate_summary_statistics(evaluation_results):

    # Calculate overall metrics

    # Analyze by complexity

    # Track success rates, verbalization usage, etc.

### Optimizations

Your code includes several key optimizations:

Memory Management:

 def clear_memory():

    gc.collect()

    torch.cuda.empty_cache()

Quantization:

 load_in_4bit=True  # Use 4-bit quantization to reduce memory usage

Retry Logic:

 while attempts < try_threshold and not successful:

    # Try generating SPARQL

    # If failed, provide feedback and retry

Pipeline Fallbacks:

 if verbalization_score >= 0.6:

    # Use verbalization results

else:

    # Use SPARQL generation

## Domain Adaptations

Your implementation handles two different domains:

1. Wikidata (public knowledge graph):

   * Uses SPARQLWrapper to connect to Wikidata endpoint
   * Implements specialized entity and property retrieval functions
   * Handles Wikidata's specific PREFIX notation and query patterns
2. CURI (university course knowledge graph):

   * Uses local RDF files instead of endpoints

Implements domain-specific verbalization templates:
 SENTENCE_TEMPLATE = "{s}'s {p} is {o}"SENTENCE_TEMPLATE_BAGIAN_DARI = "{s} is part of {o}"SENTENCE_TEMPLATE_ME = "{s} {p}s {o}"SENTENCE_TEMPLATE_DI = "{s} is {p} {o}"

* 
* Adds complexity-based evaluation (basic, intermediate, advanced)

## Technical Contributions

Your FROG implementation makes several key technical contributions:

1. Dual-Model Fine-Tuning: Separate specialized models for entity extraction and SPARQL generation
2. Verbalization-First Approach: Using direct verbalization for simple queries, falling back to SPARQL generation for complex ones
3. Hybrid Search: Combining embedding similarity with n-gram matching for robust property retrieval
4. Complexity-Based Evaluation: Analyzing performance across different question complexity levels
5. Domain Adaptability: Demonstrated by implementations for both Wikidata and university course domains

## Summary

FROG is a sophisticated framework that enhances language models' ability to work with knowledge graphs by:

1. Fine-tuning specialized models for entity extraction and SPARQL generation
2. Implementing a verbalization component for direct answers when possible
3. Using vector search with n-gram matching for robust property retrieval
4. Providing a comprehensive evaluation framework

The implementation is well-structured, with carefully crafted prompts, optimized fine-tuning parameters, and robust fallback mechanisms. The domain adaptability demonstrated between Wikidata and CURI implementations shows the framework's flexibility for different knowledge graph applications.
