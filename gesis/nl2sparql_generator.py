"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator for GESIS Knowledge Graph

This version generates query templates based on the GESIS Knowledge Graph schema,
focusing on scholarly resources, publications, and research data.
Enhanced with entity/property matching similar to the legal approach.
"""

import json
import random
import re
import datetime
import csv
import io
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import Counter
from kg_schema_extractor import gesis_entity_label
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

class SparqlExecutor:
    """A class to execute SPARQL queries against the Fuseki server."""
    
    def __init__(self, endpoint_url="http://localhost:3030/gesis/query"):
        """Initialize the SPARQL executor with the Fuseki endpoint."""
        self.endpoint = SPARQLWrapper(endpoint_url)
        self.endpoint.setReturnFormat(JSON)
    
    def execute_query(self, query, return_format="dict"):
        """
        Execute a SPARQL query and return results.
        
        Args:
            query (str): SPARQL query to execute
            return_format (str): Format to return results in ("dict", "raw", "pandas")
            
        Returns:
            Results in the specified format
        """
        # add rdfs prefix before query
        query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/>\nPREFIX schema: <https://schema.org/>\n" + query
        self.endpoint.setQuery(query)
        results = self.endpoint.query().convert()
        
        if return_format == "raw":
            return results
        
        # Extract bindings from SPARQL JSON results
        result_list = []
        if 'results' in results and 'bindings' in results['results']:
            for binding in results['results']['bindings']:
                row_dict = {}
                for var, value in binding.items():
                    if value['type'] == 'uri':
                        row_dict[var] = value['value']
                    elif value['type'] == 'literal':
                        row_dict[var] = value['value']
                    else:
                        row_dict[var] = value['value']
                result_list.append(row_dict)
        
        if return_format == "pandas":
            import pandas as pd
            if result_list:
                return pd.DataFrame(result_list)
            return pd.DataFrame()
            
        # Default to dict format
        return result_list

class VariationGenerator:
    """Generates variations of natural language questions"""
    
    def generate_variations(self, question, english_question, category, count=3):
        """
        Generate variations of a question
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English (duplicate for compatibility)
            category (str): Question category
            count (int): Number of variations to generate
            
        Returns:
            list: Array of variation dictionaries with different phrasings
        """
        variations = []
        
        # Add scholarly resource specific variations
        if category == "scholarly":
            variations.extend(self.get_scholarly_variations(question, english_question))
        
        # Add general variations
        variations.extend(self.get_general_variations(question, english_question))
        
        # Ensure we don't have duplicate variations
        unique_variations = []
        seen_questions = set()
        
        for var in variations:
            if var["text"] not in seen_questions:
                seen_questions.add(var["text"])
                unique_variations.append(var)
        
        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[:min(count, len(unique_variations))]

    def get_scholarly_variations(self, question, english_question):
        """
        Get variations specific to scholarly resource questions
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # "Who is the author of" variations
        if question.startswith("Who is the author of"):
            variations.append({
                "text": question.replace("Who is the author of", "Who wrote"),
                "english": english_question.replace("Who is the author of", "Who wrote")
            })
            variations.append({
                "text": question.replace("Who is the author of", "Who created"),
                "english": english_question.replace("Who is the author of", "Who created")
            })
        
        # "When was * published" variations
        elif question.startswith("When was") and "published" in question:
            variations.append({
                "text": question.replace("When was", "In what year was"),
                "english": english_question.replace("When was", "In what year was")
            })
            variations.append({
                "text": question.replace("When was", "What is the publication date of"),
                "english": english_question.replace("When was", "What is the publication date of")
            })
        
        # "What is the title of" variations
        elif question.startswith("What is the title of"):
            variations.append({
                "text": question.replace("What is the title of", "What is the name of"),
                "english": english_question.replace("What is the title of", "What is the name of")
            })
        
        # "Which organization published" variations
        elif question.startswith("Which organization published"):
            variations.append({
                "text": question.replace("Which organization published", "Who published"),
                "english": english_question.replace("Which organization published", "Who published")
            })
            variations.append({
                "text": question.replace("Which organization published", "What is the publisher of"),
                "english": english_question.replace("Which organization published", "What is the publisher of")
            })
        
        # "What is the topic of" variations
        elif question.startswith("What is the topic of"):
            variations.append({
                "text": question.replace("What is the topic of", "What is the subject of"),
                "english": english_question.replace("What is the topic of", "What is the subject of")
            })
            variations.append({
                "text": question.replace("What is the topic of", "What is the main theme of"),
                "english": english_question.replace("What is the topic of", "What is the main theme of")
            })
        
        return variations

    def get_general_variations(self, question, english_question):
        """
        Get general variations that apply to any question
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # Could you tell me...
        variations.append({
            "text": f"Could you tell me {question.lower()}",
            "english": f"Could you tell me {english_question.lower()}"
        })
        
        # I want to know...
        variations.append({
            "text": f"I want to know {question.lower()}",
            "english": f"I want to know {english_question.lower()}"
        })
        
        # I'm looking for information about...
        variations.append({
            "text": f"I'm looking for information about {question.lower().replace('what is ', '').replace('who is ', '')}",
            "english": f"I'm looking for information about {english_question.lower().replace('what is ', '').replace('who is ', '')}"
        })
        
        return variations

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for GESIS Knowledge Graph."""
    
    def __init__(self, config, endpoint_url="http://localhost:3030/gesis/query", property_retrieval=None):
        """
        Initialize the generator with knowledge graph schema information
        
        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            endpoint_url (str): URL of the Fuseki SPARQL endpoint
            property_retrieval: Property retrieval system for Weaviate-based search
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()
        self.property_retrieval = property_retrieval
        
        # Initialize stopwords
        self.stopwords = set(stopwords.words('english'))
        
        # Create a SPARQL executor to connect to Fuseki
        self.sparql_exec = SparqlExecutor(endpoint_url)
        
        # Pre-extract keywords from the knowledge graph
        self.extracted_keywords = self.extract_keywords_from_kg()
        
        # Fallback keywords in case extraction fails
        self.fallback_keywords = [
            "SOCIAL SCIENCE", "RESEARCH", "SURVEY", "DATA", "PUBLICATION", 
            "METHODOLOGY", "ANALYSIS", "DATASET", "KNOWLEDGE GRAPH", "SCHOLARLY"
        ]
        
        print(f"Extracted {len(self.extracted_keywords)} keywords from the knowledge graph")
    
    def extract_keywords_from_kg(self):
        """
        Extract meaningful keywords from resource titles in the knowledge graph
        
        Returns:
            list: List of keywords that appear in resource titles
        """
        try:
            # Query to get resource titles
            query = """
            SELECT ?title
            WHERE {
                ?resource a <https://schema.org/ScholarlyArticle> .
                ?resource <https://schema.org/name> ?title .
            }
            LIMIT 1000
            """
            
            results = self.sparql_exec.execute_query(query)
            if not results:
                print("No titles found in the knowledge graph")
                return []
                
            # Process titles and extract meaningful words
            all_words = []
            for result in results:
                if "title" in result:
                    title = str(result["title"])
                    # Split by spaces and filter for meaningful words (4+ characters)
                    title_words = [w.strip('()').upper() for w in title.split() if len(w) >= 4]
                    all_words.extend(title_words)
            
            # Count frequency of each word
            word_counts = Counter(all_words)
            
            # Select words that appear at least twice (more meaningful)
            common_words = [word for word, count in word_counts.items() if count >= 5]
            
            # If we don't have enough common words, include all words
            if len(common_words) < 10:
                common_words = list(set(all_words))
            
            print(f"Found {len(common_words)} common words in resource titles")
            return common_words
            
        except Exception as e:
            print(f"Error extracting keywords from knowledge graph: {e}")
            return []

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """
        Preprocess question into tokens using NLTK RegexpTokenizer
        
        Args:
            q (str): Question string
            
        Returns:
            list[str]: List of tokens
        """
        tok_pattern = r"\w+"
        tokenizer = RegexpTokenizer(tok_pattern)
        tokenized = tokenizer.tokenize(q)
        result = []
        for tok in tokenized:
            tok = tok.lower()
            if tok not in self.stopwords:
                result.append(tok)
        return result

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """
        Generate n-grams from tokens using NLTK
        
        Args:
            tokens (list[str]): List of tokens
            max_n (int): Maximum n-gram size
            
        Returns:
            list[str]: List of n-grams
        """
        result = []
        
        # Generate unigrams, bigrams, and trigrams using NLTK
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        
        return result

    def _search_entities_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search entities using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of entity results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_entities(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching entities with Weaviate: {e}")
        
        # Return empty list if property_retrieval is None or if there was an error
        return []

    def _search_properties_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search properties using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of property results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_properties(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching properties with Weaviate: {e}")
        
        # Return empty list if property_retrieval is None or if there was an error
        return []

    def get_entities_and_properties(self, question, sparql):
        """
        Extract entities and properties from SPARQL query and get their labels using schema:name
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entities_list, properties_list, entity_matches, property_matches)
        """
        # Extract actual URIs from SPARQL query
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Get labels for entities and properties
        entities_list = []
        properties_list = []
        
        # Get entity labels using schema:name
        for uri in entity_uris:
            label = self._get_entity_name_from_kg(uri)
            if not label:
                # Fallback to gesis_entity_label function
                label = gesis_entity_label(uri)
            if label:
                entities_list.append(label)
        
        # Get property labels using schema:name
        for uri in property_uris:
            label = self._get_property_name_from_kg(uri)
            if not label:
                # Extract from URI if not found
                label = uri.split('/')[-1] if '/' in uri else uri.split(':')[-1]
            if label:
                properties_list.append(label)
        
        # Get entity and property candidates for entities_matches and properties_matches
        property_candidates = entities_list + properties_list
        related_candidates = self.get_related_candidates(
            question, 
            property_candidates=property_candidates,
        )
        
        # Format entity matches
        entity_matches = []
        if "entities" in related_candidates:
            for entity in related_candidates["entities"]:
                expanded_id = self.expand_uri(entity['short'])
                entity_matches.append({
                    "id": expanded_id,
                    "label": entity['label'],
                })
        
        # Format property matches
        property_matches = []
        if "properties" in related_candidates:
            for property in related_candidates["properties"]:
                property_matches.append({
                    "id": property['short'],
                    "label": property['label'],
                })
        
        return entities_list, properties_list, entity_matches, property_matches

    def _get_entity_name_from_kg(self, entity_uri):
        """Get the schema:name for an entity from the knowledge graph"""
        try:
            query = f"""
            PREFIX schema: <https://schema.org/>
            SELECT ?name WHERE {{
                <{entity_uri}> schema:name ?name .
            }}
            LIMIT 1
            """
            results = self.sparql_exec.execute_query(query)
            
            if results and len(results) > 0:
                return results[0].get("name")
            
            return None
        except Exception:
            return None

    def _get_property_name_from_kg(self, property_uri):
        """Get the schema:name or rdfs:label for a property from the knowledge graph"""
        try:
            query = f"""
            PREFIX schema: <https://schema.org/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?name WHERE {{
                {{
                    <{property_uri}> schema:name ?name .
                }} UNION {{
                    <{property_uri}> rdfs:label ?name .
                }}
            }}
            LIMIT 1
            """
            results = self.sparql_exec.execute_query(query)
            
            if results and len(results) > 0:
                return results[0].get("name")
            
            return None
        except Exception:
            return None
    
    def expand_uri(self, shortened_uri):
        """
        Expand a shortened URI back to its full form
        
        Args:
            shortened_uri (str): Shortened URI with prefix (e.g., schema:Publication)
            
        Returns:
            str: Full URI (e.g., https://schema.org/Publication)
        """
        # Check if the URI has a prefix
        if ":" in shortened_uri:
            prefix, path = shortened_uri.split(":", 1)
            
            # If the prefix is in our known prefixes, expand it
            if prefix in self.prefixes:
                return f"{self.prefixes[prefix]}{path}"
        
        # Return as is if it doesn't have a recognized prefix or is already a full URI
        return shortened_uri

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        entity_threshold: float = 0.7,
        property_threshold: float = 0.65,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """
        Get related entity and property candidates using n-grams and property candidates
        
        Args:
            q (str): Question string
            property_candidates (list[str]): List of property candidates (entities and properties)
            entity_threshold (float): Score threshold for entity relevance
            property_threshold (float): Score threshold for property relevance
            k (int): Number of results per search
            
        Returns:
            dict[str, list[str]]: Dictionary with 'entities' and 'properties' lists
        """
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type):
            """Search for entities or properties and format results"""

            # Search using the appropriate method
            if search_type == "entities":
                df_res = self._search_entities_weaviate(ngram, k=k)
                threshold = entity_threshold  # Use entity threshold
            else:
                df_res = self._search_properties_weaviate(ngram, k=k)
                threshold = property_threshold  # Use property threshold
            
            # Filter by threshold and format results
            filtered_results = []
            for result_item in df_res:
                if result_item['score'] >= threshold:
                    filtered_results.append(result_item)
            
            return search_type, filtered_results

        # Search using n-grams and property candidates
        search_terms = ngrams + property_candidates
        
        for term in search_terms:
            for search_type in result.keys():
                search_result_type, df_res = search(term, search_type)
                if df_res:
                    extracted_items = [{'short': item['short'], 'label': item['label']} for item in df_res]
                    result[search_result_type].extend(extracted_items)
                    
        # Remove duplicates at the end
        for key in result.keys():
            # Convert to list of tuples, use set for deduplication, then back to dicts
            seen = set()
            unique_items = []
            for item in result[key]:
                item_tuple = (item['short'], item['label'])
                if item_tuple not in seen:
                    seen.add(item_tuple)
                    unique_items.append(item)
            result[key] = unique_items
        return result

    def _extract_uris_from_sparql(self, sparql):
        """
        Extract entity and property URIs from SPARQL query
        
        Args:
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entity_uris, property_uris)
        """
        entity_uris = []
        property_uris = []
        
        # Extract URIs in angle brackets
        uri_pattern = r'<([^>]+)>'
        uris = re.findall(uri_pattern, sparql)
        
        # Extract prefixed names (schema:something)
        prefixed_pattern = r'schema:([a-zA-Z_][a-zA-Z0-9_]*)'
        prefixed_names = re.findall(prefixed_pattern, sparql)
        
        # Convert prefixed names to full URIs
        schema_prefix = self.prefixes.get('schema', 'https://schema.org/')
        for name in prefixed_names:
            full_uri = f"{schema_prefix}{name}"
            uris.append(full_uri)
        
        # Classify URIs as entities or properties
        for uri in uris:
            if self.is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)
        
        return entity_uris, property_uris

    def is_property_uri(self, uri):
        """
        Check if a URI is a property URI
        
        Args:
            uri (str): URI to check
            
        Returns:
            bool: True if it's a property URI
        """
        # For schema.org, properties typically have a pattern like "https://schema.org/propertyName"
        # Entities might have a pattern like "https://data.gesis.org/gesiskg/resource/..."
        
        # Check if it's from schema.org (properties)
        if "schema.org/" in uri and "resource/" not in uri:
            return True
        
        # Check if it's a specific property from GESIS ontology
        for prop in self.schema_info.get("properties", []):
            if prop.get("uri") == uri:
                return True
                
        return False
    
    def initialize_templates(self):
        """
        Initialize question-query template pairs for GESIS knowledge graph
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # GESIS Knowledge Graph specific templates
        scholarly_templates = [
            # Basic information about publications
            {
                "id": "publication-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the author of {entity}?",
                    "Who wrote {entity}?", 
                    "Who created {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Who is the author of {entity}?",
                    "Who wrote {entity}?",
                    "Who created {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    {entity} schema:author ?author .
                    ?author schema:name ?authorName .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks for the author of a specific scholarly resource {entity}.",
                    "2. In the GESIS knowledge graph, authorship is represented by the schema:author property.",
                    "3. First, I need to find the author entity related to {entity} using the schema:author property.",
                    "4. Then I retrieve the human-readable name of the author using the schema:name property.",
                    "5. The query returns the name(s) of the author(s) who created {entity}."
                ]
            },
            {
                "id": "publication-date",
                "category": "scholarly",
                "questionTemplates": [
                    "When was {entity} published?",
                    "What is the publication date of {entity}?",
                    "In what year was {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "When was {entity} published?",
                    "What is the publication date of {entity}?",
                    "In what year was {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?date WHERE {
                    {entity} schema:datePublished ?date .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks when a specific scholarly resource {entity} was published.",
                    "2. In the GESIS knowledge graph, publication dates are represented by the schema:datePublished property.",
                    "3. To answer this question, I need to query for the value of the schema:datePublished property of {entity}.",
                    "4. The query directly retrieves the publication date without needing additional joins or transformations.",
                    "5. The result provides the publication date of {entity} in the format stored in the knowledge graph."
                ]
            },
            {
                "id": "publication-publisher",
                "category": "scholarly",
                "questionTemplates": [
                    "Which organization published {entity}?",
                    "Who published {entity}?",
                    "What is the publisher of {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Which organization published {entity}?",
                    "Who published {entity}?",
                    "What is the publisher of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?publisherName WHERE {
                    {entity} schema:publisher ?publisher .
                    ?publisher schema:name ?publisherName .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks about the organization that published {entity}.",
                    "2. In the GESIS knowledge graph, publishers are linked to publications via the schema:publisher property.",
                    "3. I need to first find the publisher entity related to {entity} using schema:publisher.",
                    "4. Then I retrieve the name of the publisher organization using the schema:name property.",
                    "5. The query returns the name of the organization that published {entity}."
                ]
            },
            {
                "id": "publication-topic",
                "category": "scholarly",
                "questionTemplates": [
                    "What is the topic of {entity}?",
                    "What is the subject of {entity}?",
                    "What is the main theme of {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the topic of {entity}?",
                    "What is the subject of {entity}?",
                    "What is the main theme of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?topicName WHERE {
                    {entity} schema:about ?topic .
                    ?topic schema:name ?topicName .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks about the topic or subject of {entity}.",
                    "2. In the GESIS knowledge graph, topics are linked to publications via the schema:about property.",
                    "3. I first need to find the topic entity that {entity} is about using schema:about.",
                    "4. Then I retrieve the name of the topic using the schema:name property.",
                    "5. The query returns the name of the topic that {entity} is about."
                ]
            },
            {
                "id": "publication-language",
                "category": "scholarly",
                "questionTemplates": [
                    "What language is {entity} written in?",
                    "What is the language of {entity}?",
                    "In which language was {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "What language is {entity} written in?",
                    "What is the language of {entity}?",
                    "In which language was {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?language WHERE {
                    {entity} schema:inLanguage ?language .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks about the language in which {entity} was written or published.",
                    "2. In the GESIS knowledge graph, the language of a publication is represented by the schema:inLanguage property.",
                    "3. To answer this question, I need to query for the value of the schema:inLanguage property of {entity}.",
                    "4. The query directly retrieves the language without needing additional joins or transformations.",
                    "5. The result provides the language of {entity} as stored in the knowledge graph."
                ]
            },
            {
                "id": "resource-library-location",
                "category": "scholarly",
                "questionTemplates": [
                    "Where is {entity} located in the library?",
                    "What is the library location of {entity}?",
                    "In which section of the library can I find {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Where is {entity} located in the library?",
                    "What is the library location of {entity}?",
                    "In which section of the library can I find {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?locationName WHERE {
                    {entity} gesiskg:libraryLocation ?location .
                    ?location schema:name ?locationName .
                    }
                """,
                "complexity": "basic",
                "thoughtsTemplate": [
                    "1. The question asks about the library location of a specific resource {entity}.",
                    "2. In the GESIS knowledge graph, resources are linked to their physical locations via the gesiskg:libraryLocation property.",
                    "3. First, I need to find the location entity related to {entity} using the gesiskg:libraryLocation property.",
                    "4. Then I retrieve the human-readable name of the location using the schema:name property.",
                    "5. The query returns the name of the library location where {entity} can be found."
                ]
            },
            
            # Intermediate: Structure and relationships
            {
                "id": "person-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications has {entity} authored?",
                    "What is the publication count of {entity}?",
                    "How many works did {entity} create?"
                ],
                "englishQuestionTemplates": [
                    "How many publications has {entity} authored?",
                    "What is the publication count of {entity}?",
                    "How many works did {entity} create?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        ?publication schema:author {entity} .
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of publications authored by {entity}.",
                    "2. In the GESIS knowledge graph, publications are linked to their authors via the schema:author property.",
                    "3. To count the publications, I need to find all resources that have {entity} as their author.",
                    "4. I use COUNT(DISTINCT ?publication) to avoid counting the same publication multiple times.",
                    "5. The query uses a nested SELECT with aggregation to return the total count of publications authored by {entity}."
                ]
            },
            {
                "id": "person-latest-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "What is the latest publication by {entity}?",
                    "What was {entity}'s most recent work?",
                    "What did {entity} publish most recently?"
                ],
                "englishQuestionTemplates": [
                    "What is the latest publication by {entity}?",
                    "What was {entity}'s most recent work?",
                    "What did {entity} publish most recently?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:author {entity} .
                    ?publication schema:name ?title .
                    ?publication schema:datePublished ?date .
                    }
                    ORDER BY DESC(?date)
                    LIMIT 1
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the most recent publication by {entity}.",
                    "2. In the GESIS knowledge graph, publications are linked to authors via schema:author and have publication dates via schema:datePublished.",
                    "3. I need to find all publications that have {entity} as their author and retrieve their titles and dates.",
                    "4. I sort the results by publication date in descending order (most recent first) using ORDER BY DESC(?date).",
                    "5. The LIMIT 1 clause ensures only the most recent publication is returned."
                ]
            },
            {
                "id": "publication-collaborator-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many collaborators worked on {entity}?",
                    "What is the number of authors for {entity}?",
                    "How many researchers contributed to {entity}?"
                ],
                "englishQuestionTemplates": [
                    "How many collaborators worked on {entity}?",
                    "What is the number of authors for {entity}?",
                    "How many researchers contributed to {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?collaborator) AS ?count) WHERE {
                        {entity} schema:author ?collaborator .
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of authors or collaborators who worked on {entity}.",
                    "2. In the GESIS knowledge graph, publications are linked to their authors via the schema:author property.",
                    "3. To count the collaborators, I need to find all authors that are linked to {entity}.",
                    "4. I use COUNT(DISTINCT ?collaborator) to count each collaborator only once.",
                    "5. The query uses a nested SELECT with aggregation to return the total count of distinct authors of {entity}."
                ]
            },
            {
                "id": "organization-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications are associated with {entity}?",
                    "What is the publication count for {entity}?",
                    "How many works has {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "How many publications are associated with {entity}?",
                    "What is the publication count for {entity}?",
                    "How many works has {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        {
                            ?publication schema:publisher {entity} .
                        } UNION {
                            ?publication schema:contributor {entity} .
                        }
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of publications associated with {entity}, which appears to be an organization.",
                    "2. In the GESIS knowledge graph, organizations can be linked to publications in two ways: as publishers (schema:publisher) or as contributors (schema:contributor).",
                    "3. I need to find all publications where {entity} is either the publisher or a contributor using a UNION pattern.",
                    "4. I use COUNT(DISTINCT ?publication) to ensure each publication is counted only once, even if it relates to {entity} in multiple ways.",
                    "5. The query returns the total count of distinct publications associated with {entity}."
                ]
            },
            {
                "id": "year-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications were published in {value}?",
                    "What is the publication count for the year {value}?",
                    "How many works were released in {value}?"
                ],
                "englishQuestionTemplates": [
                    "How many publications were published in {value}?",
                    "What is the publication count for the year {value}?",
                    "How many works were released in {value}?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(?publication) AS ?count) WHERE {
                        ?publication schema:datePublished {value} .
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of publications published in a specific year ({value}).",
                    "2. In the GESIS knowledge graph, publication dates are represented by the schema:datePublished property.",
                    "3. I need to find all publications with a datePublished value matching {value}.",
                    "4. The COUNT(?publication) aggregation function gives us the total number of such publications.",
                    "5. The query returns the count of publications published in the year {value}."
                ]
            },
            {
                "id": "person-first-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "What was the first publication by {entity}?",
                    "What is {entity}'s earliest work?",
                    "What did {entity} publish first?"
                ],
                "englishQuestionTemplates": [
                    "What was the first publication by {entity}?",
                    "What is {entity}'s earliest work?",
                    "What did {entity} publish first?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:author {entity} .
                    ?publication schema:name ?title .
                    ?publication schema:datePublished ?date .
                    }
                    ORDER BY ASC(?date)
                    LIMIT 1
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the earliest publication by {entity}.",
                    "2. In the GESIS knowledge graph, publications are linked to authors via schema:author and have publication dates via schema:datePublished.",
                    "3. I need to find all publications that have {entity} as their author and retrieve their titles and dates.",
                    "4. I sort the results by publication date in ascending order (oldest first) using ORDER BY ASC(?date).",
                    "5. The LIMIT 1 clause ensures only the earliest publication is returned."
                ]
            },
            {
                "id": "topic-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications are about '{value}'?",
                    "What is the number of works on '{value}'?",
                    "How many research papers discuss '{value}'?"
                ],
                "englishQuestionTemplates": [
                    "How many publications are about '{value}'?",
                    "What is the number of works on '{value}'?",
                    "How many research papers discuss '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        {
                            ?publication schema:about ?topic .
                            ?topic schema:name ?topicName .
                            FILTER(CONTAINS(LCASE(?topicName), LCASE({value})))
                        } UNION {
                            ?publication schema:keywords ?keyword .
                            FILTER(CONTAINS(LCASE(?keyword), LCASE({value})))
                        }
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of publications about a specific topic ('{value}').",
                    "2. In the GESIS knowledge graph, a publication can be related to a topic in two ways: through schema:about pointing to a topic entity, or through schema:keywords containing the topic as a keyword.",
                    "3. I need to find publications where either the linked topic's name contains '{value}' or where a keyword contains '{value}'.",
                    "4. I use CONTAINS with LCASE to perform case-insensitive matching, ensuring we find all relevant publications regardless of capitalization.",
                    "5. COUNT(DISTINCT ?publication) ensures each publication is counted only once, even if it matches multiple times."
                ]
            },
            {
                "id": "location-resource-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many resources are located in {entity}?",
                    "What is the total number of resources at {entity}?",
                    "How many items can be found in the {entity} section?"
                ],
                "englishQuestionTemplates": [
                    "How many resources are located in {entity}?",
                    "What is the total number of resources at {entity}?",
                    "How many items can be found in the {entity} section?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(?resource) AS ?count) WHERE {
                        ?resource gesiskg:libraryLocation {entity} .
                        }
                    }
                    }
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for the number of resources located at a specific library location {entity}.",
                    "2. In the GESIS knowledge graph, resources are linked to their physical locations via the gesiskg:libraryLocation property.",
                    "3. To count the resources, I need to find all resources that have {entity} as their library location.",
                    "4. I use COUNT(?resource) to count the total number of such resources.",
                    "5. The query returns the count of resources located at {entity}."
                ]
            },
            {
                "id": "location-resources-list",
                "category": "scholarly",
                "questionTemplates": [
                    "Which resources are available at {entity}?",
                    "What items can be found at the {entity} location?",
                    "List the resources located in {entity}."
                ],
                "englishQuestionTemplates": [
                    "Which resources are available at {entity}?",
                    "What items can be found at the {entity} location?",
                    "List the resources located in {entity}."
                ],
                "sparqlTemplate": """
                    SELECT ?resourceName WHERE {
                    ?resource gesiskg:libraryLocation {entity} .
                    ?resource schema:name ?resourceName .
                    }
                    LIMIT 10
                """,
                "complexity": "intermediate",
                "thoughtsTemplate": [
                    "1. The question asks for a list of resources available at a specific library location {entity}.",
                    "2. In the GESIS knowledge graph, resources are linked to their physical locations via the gesiskg:libraryLocation property.",
                    "3. I need to find all resources that have {entity} as their library location.",
                    "4. For each resource, I retrieve its name using the schema:name property.",
                    "5. The query returns the names of up to 10 resources located at {entity}."
                ]
            },
            
            # Advanced: Complex relationships and analytics
            {
                "id": "keyword-topic-top-expert",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the top expert on '{value}'?",
                    "Which researcher is most prominent in '{value}'?",
                    "Who has published the most about '{value}'?"
                ],
                "englishQuestionTemplates": [
                    "Who is the top expert on '{value}'?",
                    "Which researcher is most prominent in '{value}'?",
                    "Who has published the most about '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    ?publication schema:author ?author .
                    {
                        ?publication schema:about ?topic .
                        ?topic schema:name ?topicName .
                        FILTER(CONTAINS(LCASE(?topicName), LCASE({value})))
                    } UNION {
                        ?publication schema:keywords ?keyword .
                        FILTER(CONTAINS(LCASE(?keyword), LCASE({value})))
                    } UNION {
                        ?publication schema:name ?title .
                        FILTER(CONTAINS(LCASE(?title), LCASE({value})))
                    }
                    ?author schema:name ?authorName .
                    }
                    GROUP BY ?author ?authorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks who is the top expert or most prolific researcher on the topic '{value}'.",
                    "2. To determine expertise, I need to count how many publications each author has on this topic.",
                    "3. A publication can relate to '{value}' in three ways: through a topic entity's name, through keywords, or through the publication's title.",
                    "4. I use UNION to combine these three patterns and CONTAINS with LCASE for case-insensitive matching.",
                    "5. I group the results by author and count their publications on this topic.",
                    "6. Ordering by the publication count in descending order and limiting to 1 result gives us the top expert."
                ]
            },
            {
                "id": "organization-top-contributor",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the top contributor to {entity}?",
                    "Which author publishes most with {entity}?",
                    "Who is the leading researcher at {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Who is the top contributor to {entity}?",
                    "Which author publishes most with {entity}?",
                    "Who is the leading researcher at {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?contributorName WHERE {
                    ?publication schema:publisher {entity} .
                    ?publication schema:author|schema:contributor ?contributor .
                    ?contributor schema:name ?contributorName .
                    }
                    GROUP BY ?contributor ?contributorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks who is the top contributor or most prolific author associated with {entity}, which appears to be an organization.",
                    "2. I need to find publications where {entity} is the publisher and then identify the most frequent author of these publications.",
                    "3. Authors can be linked to publications via either schema:author or schema:contributor, so I use the property path schema:author|schema:contributor to check both.",
                    "4. I group by contributor and count how many publications they have with {entity} as publisher.",
                    "5. Ordering by publication count in descending order and limiting to 1 result gives us the top contributor."
                ]
            },
            {
                "id": "publication-with-most-authors",
                "category": "scholarly",
                "questionTemplates": [
                    "Which publication has the most authors?",
                    "What paper has the largest research team?",
                    "Which work has the most collaborators?"
                ],
                "englishQuestionTemplates": [
                    "Which publication has the most authors?",
                    "What paper has the largest research team?",
                    "Which work has the most collaborators?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:name ?title .
                    ?publication schema:author ?author .
                    }
                    GROUP BY ?publication ?title
                    ORDER BY DESC(COUNT(?author))
                    LIMIT 1
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the publication with the highest number of authors or collaborators.",
                    "2. I need to count how many authors are associated with each publication.",
                    "3. In the GESIS knowledge graph, publications are linked to their authors via the schema:author property.",
                    "4. I group the results by publication and title, then count the number of authors for each.",
                    "5. Ordering by the author count in descending order and limiting to 1 result gives us the publication with the most authors."
                ]
            },
            {
                "id": "most-productive-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the most productive author?",
                    "Which researcher has published the most work?",
                    "Who has the highest publication count?"
                ],
                "englishQuestionTemplates": [
                    "Who is the most productive author?",
                    "Which researcher has published the most work?",
                    "Who has the highest publication count?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    ?publication schema:author ?author .
                    ?author schema:name ?authorName .
                    }
                    GROUP BY ?author ?authorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the most productive author, defined as the one with the most publications.",
                    "2. In the GESIS knowledge graph, publications are linked to their authors via the schema:author property.",
                    "3. I need to count how many publications are associated with each author.",
                    "4. I group the results by author and author name, then count the number of publications for each.",
                    "5. Ordering by publication count in descending order and limiting to 1 result gives us the most productive author."
                ]
            },
            {
                "id": "most-collaborative-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the most collaborative author?",
                    "Which researcher works with the most co-authors?",
                    "Who has the most research partners?"
                ],
                "englishQuestionTemplates": [
                    "Who is the most collaborative author?",
                    "Which researcher works with the most co-authors?",
                    "Who has the most research partners?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    {
                        SELECT ?author WHERE {
                        ?publication schema:author ?author .
                        ?publication schema:author ?coauthor .
                        FILTER(?author != ?coauthor)
                        }
                        GROUP BY ?author
                        ORDER BY DESC(COUNT(DISTINCT ?coauthor))
                        LIMIT 1
                    }
                    ?author schema:name ?authorName .
                    }
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the most collaborative author, defined as the one who works with the most co-authors.",
                    "2. To determine collaboration, I need to count unique co-authors for each author.",
                    "3. I find publications with the author, then find other authors (co-authors) of the same publications.",
                    "4. The FILTER(?author != ?coauthor) ensures we don't count the author as their own co-author.",
                    "5. I group by author and count distinct co-authors using COUNT(DISTINCT ?coauthor).",
                    "6. Ordering by co-author count in descending order and limiting to 1 result gives us the most collaborative author."
                ]
            },
            {
                "id": "publications-by-year-trend",
                "category": "scholarly",
                "questionTemplates": [
                    "Which year had the most publications?",
                    "What was the most productive year for research publications?",
                    "In which year were the most papers published?"
                ],
                "englishQuestionTemplates": [
                    "Which year had the most publications?",
                    "What was the most productive year for research publications?",
                    "In which year were the most papers published?"
                ],
                "sparqlTemplate": """
                    SELECT ?year WHERE {
                    ?publication schema:datePublished ?fullDate .
                    BIND(SUBSTR(STR(?fullDate), 0, 5) AS ?year)
                    }
                    GROUP BY ?year
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the year with the highest number of publications.",
                    "2. In the GESIS knowledge graph, publication dates are stored in the schema:datePublished property.",
                    "3. I extract just the year part from the full date using SUBSTR(STR(?fullDate), 0, 5) which gives the first 4 characters of the string representation.",
                    "4. I group the results by year and count the number of publications for each year.",
                    "5. Ordering by publication count in descending order and limiting to 1 result gives us the year with the most publications."
                ]
            },
            {
                "id": "most-diverse-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "Which publication covers the most diverse topics?",
                    "What paper addresses the widest range of subjects?",
                    "Which research work has the most varied themes?"
                ],
                "englishQuestionTemplates": [
                    "Which publication covers the most diverse topics?",
                    "What paper addresses the widest range of subjects?",
                    "Which research work has the most varied themes?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    {
                        SELECT ?publication WHERE {
                        ?publication schema:about ?topic .
                        }
                        GROUP BY ?publication
                        ORDER BY DESC(COUNT(DISTINCT ?topic))
                        LIMIT 1
                    }
                    ?publication schema:name ?title .
                    }
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the publication that covers the most diverse range of topics.",
                    "2. In the GESIS knowledge graph, publications are linked to their topics via the schema:about property.",
                    "3. I need to count how many distinct topics each publication covers.",
                    "4. I group the results by publication and title, then count the number of distinct topics for each using COUNT(DISTINCT ?topic).",
                    "5. Ordering by topic count in descending order and limiting to 1 result gives us the publication with the most diverse topics."
                ]
            },
            {
                "id": "most-populated-location",
                "category": "scholarly",
                "questionTemplates": [
                    "Which library location has the most resources?",
                    "What is the most populated section in the library?",
                    "Which library location contains the largest number of items?"
                ],
                "englishQuestionTemplates": [
                    "Which library location has the most resources?",
                    "What is the most populated section in the library?",
                    "Which library location contains the largest number of items?"
                ],
                "sparqlTemplate": """
                    SELECT ?locationName WHERE {
                    {
                        SELECT ?location (COUNT(?resource) AS ?count) WHERE {
                        ?resource gesiskg:libraryLocation ?location .
                        }
                        GROUP BY ?location
                        ORDER BY DESC(?count)
                        LIMIT 1
                    }
                    ?location schema:name ?locationName .
                    }
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the library location that contains the most resources.",
                    "2. In the GESIS knowledge graph, resources are linked to their physical locations via the gesiskg:libraryLocation property.",
                    "3. I need to count how many resources are associated with each location.",
                    "4. I group the results by location and count the number of resources for each using COUNT(?resource).",
                    "5. Ordering by the resource count in descending order and limiting to 1 result gives the location with the most resources.",
                    "6. Finally, I retrieve the human-readable name of this location using the schema:name property."
                ]
            },
            {
                "id": "author-multiple-locations",
                "category": "scholarly",
                "questionTemplates": [
                    "Which author has works in the most different library locations?",
                    "Who is the author with publications across the most library sections?",
                    "Which researcher has the widest distribution of works across library locations?"
                ],
                "englishQuestionTemplates": [
                    "Which author has works in the most different library locations?",
                    "Who is the author with publications across the most library sections?",
                    "Which researcher has the widest distribution of works across library locations?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    {
                        SELECT ?author (COUNT(DISTINCT ?location) AS ?locationCount) WHERE {
                        ?resource schema:author ?author .
                        ?resource gesiskg:libraryLocation ?location .
                        }
                        GROUP BY ?author
                        ORDER BY DESC(?locationCount)
                        LIMIT 1
                    }
                    ?author schema:name ?authorName .
                    }
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the author who has works distributed across the most different library locations.",
                    "2. I need to find authors, their works, and the library locations of those works.",
                    "3. For each author, I count the distinct library locations where their works can be found using COUNT(DISTINCT ?location).",
                    "4. The resources are linked to authors via schema:author and to locations via gesiskg:libraryLocation.",
                    "5. I group by author and order by the count of distinct locations in descending order.",
                    "6. The LIMIT 1 ensures I get only the author with works in the most locations.",
                    "7. Finally, I retrieve the author's name using the schema:name property."
                ]
            },
            {
                "id": "location-topic-distribution",
                "category": "scholarly",
                "questionTemplates": [
                    "What is the most common topic for resources in {entity}?",
                    "Which subject is most represented in the {entity} section?",
                    "What topic dominates the collection at {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the most common topic for resources in {entity}?",
                    "Which subject is most represented in the {entity} section?",
                    "What topic dominates the collection at {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?topicName WHERE {
                    {
                        SELECT ?topic (COUNT(?resource) AS ?count) WHERE {
                        ?resource gesiskg:libraryLocation {entity} .
                        ?resource schema:about ?topic .
                        }
                        GROUP BY ?topic
                        ORDER BY DESC(?count)
                        LIMIT 1
                    }
                    ?topic schema:name ?topicName .
                    }
                """,
                "complexity": "advanced",
                "thoughtsTemplate": [
                    "1. The question asks for the most common topic among resources located at {entity}.",
                    "2. In the GESIS knowledge graph, resources are linked to locations via gesiskg:libraryLocation and to topics via schema:about.",
                    "3. I need to find all resources at the specified location, then identify their topics.",
                    "4. I count how many resources are associated with each topic using COUNT(?resource).",
                    "5. Grouping by topic and ordering by count in descending order gives the most common topic.",
                    "6. Finally, I retrieve the human-readable name of this topic using the schema:name property."
                ]
            }
        ]
        
        # Use scholarly templates for GESIS KG
        return scholarly_templates

    def generate_chain_of_thoughts(self, question, sparql, template):
        """
        Generate a chain of thoughts explaining how to translate the question to SPARQL
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            template (dict): Template used to generate the question-query pair
            
        Returns:
            list: List of thought steps
        """
        if "thoughtsTemplate" not in template:
            # Fallback for templates without thoughtsTemplate
            return [
                "1. The question seeks specific information from the GESIS knowledge graph.",
                "2. The query involves entities and relationships defined in the scholarly domain.",
                "3. Properties in the knowledge graph connect scholarly resources to their various attributes and relationships.",
                "4. The SPARQL query is constructed to retrieve the requested information efficiently.",
                "5. The result provides valuable insights for scholarly research and analysis."
            ]
        
        # Get the thoughts template
        thoughts_template = template["thoughtsTemplate"]
        
        # Extract entity and property URIs from SPARQL
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Create mappings for replacement
        all_mappings = {}
        
        # Add entity mappings
        for i, uri in enumerate(entity_uris):
            key = "entity" if i == 0 else f"entity{i+1}"
            label = self.extract_label_from_uri(uri)
            all_mappings[key] = {
                'uri': uri,
                'label': label,
                'prefixed': self.shorten_uri(uri)
            }
        
        # Add value mappings from SPARQL
        numeric_pattern = r'\b(\d+)\b'
        numeric_values = re.findall(numeric_pattern, sparql)
        string_pattern = r'"([^"]+)"'
        string_values = re.findall(string_pattern, sparql)
        
        if numeric_values:
            all_mappings['value'] = {
                'value': numeric_values[0],
                'label': numeric_values[0]
            }
        elif string_values:
            all_mappings['value'] = {
                'value': string_values[0],
                'label': string_values[0]
            }
        
        # Replace placeholders in thoughts
        processed_thoughts = []
        for thought in thoughts_template:
            processed_thought = thought
            
            # Replace each placeholder with the appropriate value
            for placeholder, mapping in all_mappings.items():
                pattern = r'\{' + re.escape(placeholder) + r'\}'
                replacement_value = self.get_appropriate_replacement(thought, placeholder, mapping)
                processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            # Special handling for first entity: check if {entity} exists, if not try {entity1}
            if 'entity' in all_mappings:
                entity_mapping = all_mappings['entity']
                
                if '{entity}' not in processed_thought and '{entity1}' in processed_thought:
                    pattern = r'\{entity1\}'
                    replacement_value = self.get_appropriate_replacement(thought, 'entity1', entity_mapping)
                    processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            processed_thoughts.append(processed_thought)
        
        return processed_thoughts

    def get_appropriate_replacement(self, thought_text, placeholder, mapping):
        """
        Determine whether to use URI or label based on the context in the thought
        
        Args:
            thought_text (str): The thought text containing the placeholder
            placeholder (str): The placeholder being replaced
            mapping (dict): The mapping containing uri, label, and prefixed forms
            
        Returns:
            str: The appropriate replacement value
        """
        # Check context around the placeholder to determine appropriate replacement
        thought_lower = thought_text.lower()
        
        # Use URI/prefixed form in these contexts:
        if any(phrase in thought_lower for phrase in [
            "in the ontology",
            "represents the",
            "schema:",
            "property '",
            "entity '",
            "via the '",
            "using",
            "through"
        ]):
            # For entity placeholders (typically starting with "entity"), use full URI
            if placeholder.startswith('entity') and 'uri' in mapping and mapping['uri'].startswith('http'):
                return f"<{mapping['uri']}>"
            
            # For property placeholders or other placeholders, keep using prefixed form
            return mapping.get('prefixed', mapping.get('uri', mapping.get('label', placeholder)))
        
        # Use label form in these contexts:
        elif any(phrase in thought_lower for phrase in [
            "categorized as",
            "belonging to", 
            "classified as",
            "of the '",
            "as a '",
            "category '",
            "group '",
            "method '",
            "article '",
            "document '"
        ]):
            return mapping.get('label', mapping.get('value', placeholder))
        
        # Default to label for most contexts
        return mapping.get('label', mapping.get('value', placeholder))

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True,
                    variations_per_question=3, validate_queries=False, max_attempts_per_template=10,
                    use_english_question=False):
        """
        Generate dataset based on university course or GESIS knowledge graph
        
        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            variations_per_question (int): Number of variations per question
            validate_queries (bool): Whether to validate SPARQL queries
            max_attempts_per_template (int): Maximum number of attempts to instantiate a template
            use_english_question (bool): If True, use "englishQuestion" field instead of "question" (for GESIS data)
            
        Returns:
            list: Array of question-SPARQL pairs
        """
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.4,
                "intermediate": 0.3,
                "advanced": 0.3  # Increased proportion of advanced queries
            }
        
        dataset = []
        id_counter = 1
        
        # Calculate how many questions of each complexity to generate
        counts_by_complexity = {}
        for complexity, proportion in complexity_distribution.items():
            counts_by_complexity[complexity] = int(size * proportion)
        
        # Track problematic templates for reporting
        failed_templates = {}
        
        # Generate questions for each complexity level
        for complexity, count in counts_by_complexity.items():
            print(f"\nGenerating {count} questions for complexity level: {complexity}")
            successful_generations = 0
            eligible_templates = [t for t in self.templates if t["complexity"] == complexity]
            
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            while successful_generations < count and len(dataset) < size:
                print(f"  - Attempting to generate questions for complexity '{complexity}' (current count: {successful_generations}/{count})")
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)
                
                # Track attempts for this template
                template_id = template["id"]
                attempts = 0
                
                # Try to instantiate this template up to max_attempts
                while attempts < max_attempts_per_template:
                    attempts += 1
                    try:
                        # Use the discovery-based approach to instantiate the template
                        instance = self.instantiate_template_with_discovery(template)
                        
                        if instance:
                            # Generate chain of thoughts for the question-query pair
                            thoughts = self.generate_chain_of_thoughts(instance["question"], instance["sparql"], template)
                            
                            # Create the base dataset entry
                            entry = {
                                "id": f"q{id_counter}",
                                "category": template["category"],
                                "complexity": template["complexity"],
                                "templateId": template["id"],
                                "sparql": instance["sparql"],
                                "thoughts": thoughts
                            }
                            
                            # Set the question field name based on parameter
                            if use_english_question:
                                entry["englishQuestion"] = instance["question"]
                            else:
                                entry["question"] = instance["question"]
                            
                            # Add entity and property information if property_retrieval is available
                            if self.property_retrieval:
                                entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(
                                    instance["question"], instance["sparql"]
                                )
                                entry.update({
                                    "entities": entities_list,
                                    "properties": properties_list,
                                    "entities_matches": entity_matches,
                                    "properties_matches": property_matches
                                })
                            
                            dataset.append(entry)
                            id_counter += 1
                            successful_generations += 1
                            
                            # Break out of the attempts loop
                            break
                    except Exception as e:
                        print(f"Error instantiating template {template['id']}: {e}")
                
                # If we've tried max_attempts and still failed, record this template as problematic
                if attempts >= max_attempts_per_template and template_id not in failed_templates:
                    failed_templates[template_id] = 0
                
                if template_id in failed_templates:
                    failed_templates[template_id] += 1
        
        # Report problematic templates
        if failed_templates:
            print("\nWarning: Some templates consistently failed to instantiate:")
            for template_id, count in failed_templates.items():
                print(f"  - {template_id}: failed {count} times")
        
        # Report complexity distribution achieved
        complexity_counts = {}
        for item in dataset:
            complexity = item["complexity"]
            if complexity not in complexity_counts:
                complexity_counts[complexity] = 0
            complexity_counts[complexity] += 1
        
        print("\nActual complexity distribution in generated dataset:")
        for complexity, count in complexity_counts.items():
            target = counts_by_complexity.get(complexity, 0)
            percentage = (count / len(dataset)) * 100 if dataset else 0
            print(f"  - {complexity}: {count}/{len(dataset)} ({percentage:.1f}%) [Target: {target}]")
        
        # Validate queries if requested
        if validate_queries and hasattr(self.config, "query_validator"):
            validator = self.config["query_validator"]
            filtered_dataset = []
            
            for item in dataset:
                try:
                    if validator(item["sparql"]):
                        filtered_dataset.append(item)
                    else:
                        print(f"Invalid SPARQL query for id {item['id']}")
                except Exception as e:
                    print(f"Error validating query for id {item['id']}: {e}")
            
            return filtered_dataset
        
        return dataset

    def instantiate_template_with_discovery(self, template):
        """
        Instantiate a template using a discovery-based approach that guarantees valid placeholder values
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Extract placeholders from the template
        placeholders = self.extract_placeholders(template)
        
        # Special handling for templates without placeholders (like "most-collaborative-author")
        if not placeholders:
            print(f"Template {template['id']} has no placeholders, using direct instantiation")
            return self.instantiate_template_without_placeholders(template)
        
        # Special handling for keyword-based templates
        if ("keyword" in template["id"] or "topic" in template["id"]) and "value" in placeholders:
            # For this template, use the pre-extracted keywords directly
            # rather than trying to discover them via SPARQL
            return self.instantiate_keyword_template(template)
        
        # Create a discovery query that includes all placeholders in the SELECT clause
        discovery_query = self.create_discovery_query(template, placeholders)
        
        if not discovery_query:
            print(f"Could not create discovery query for template: {template['id']}")
            return self.instantiate_template(template)
        
        # Quick validation of the discovery query
        if "??" in discovery_query:
            print(f"Error: Discovery query contains double question marks!")
            print(f"Query: {discovery_query}")
            return self.instantiate_template(template)
        
        # Execute the discovery query
        try:
            print(f"Executing discovery query for template {template['id']}...")
            results = self.sparql_exec.execute_query(discovery_query)
            
            if not results:
                print(f"No valid combinations found for template: {template['id']}")
                print("Query: ", discovery_query)
                return self.instantiate_template(template)
                
            print(f"Found {len(results)} valid combinations for template: {template['id']}")
                
            # Randomly select one complete valid combination of values
            selected = random.choice(results)
            
            # Create a mapping of placeholders to their values from the selected combination
            replacements = {}
            
            # Extract values for each placeholder
            for placeholder in placeholders:
                # Skip if placeholder doesn't exist in result
                if placeholder not in selected:
                    print(f"Warning: Placeholder {placeholder} not found in query results")
                    continue
                
                value = selected[placeholder]
                
                # Skip if value is None
                if value is None:
                    print(f"Warning: Placeholder {placeholder} has None value")
                    continue
                    
                # Try to get the label for entity placeholders
                if placeholder.startswith('entity'):
                    entity_uri = str(value)
                    
                    # Look for a label variable for this entity
                    label_var = f"{placeholder}Label"
                    if label_var in selected and selected[label_var] is not None:
                        entity_label = str(selected[label_var])
                    else:
                        # Extract label from URI if not found in result
                        entity_label = self.extract_label_from_uri(entity_uri)
                        
                    replacement = {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri
                    }
                elif placeholder == "value" or placeholder.endswith("Value"):
                    # For value placeholders
                    value_str = str(value)
                    
                    # Handle different value types appropriately
                    if "year" in template["id"] or "year" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                    elif "keyword" in template["id"] or "keyword" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"'  # Include quotes for string literal
                        }
                    elif "topic" in template["id"] or "topic" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"'  # Include quotes for string literal
                        }
                    else:
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                else:
                    # For other placeholders, use as is
                    replacement = {
                        "value": str(value),
                        "label": str(value)
                    }
                    
                replacements[placeholder] = replacement
            
            # Check if all placeholders have valid replacements
            if set(replacements.keys()) != set(placeholders):
                missing = set(placeholders) - set(replacements.keys())
                print(f"Missing valid values for placeholders: {missing}")
                return self.instantiate_template(template)
                
            # Randomly select one of the question templates
            question_idx = random.randrange(len(template["questionTemplates"]))
            question_template = template["questionTemplates"][question_idx]
            english_question_template = template["englishQuestionTemplates"][question_idx]
            
            # Apply replacements to the question template
            question = question_template.strip()
            english_question = english_question_template.strip()
            sparql = template["sparqlTemplate"].strip()
            
            # Replace placeholders in question and query
            for placeholder, replacement in replacements.items():
                # Create a pattern that can handle whitespace around the placeholder
                pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
                
                # Replace in question
                replacement_text = replacement.get("label", replacement.get("value", ""))
                # Add quotes around entity placeholders, but not other placeholders like 'value'
                if placeholder.startswith('entity'):
                    quoted_replacement = f"'{replacement_text}'"
                    question = re.sub(pattern, quoted_replacement, question)
                    english_question = re.sub(pattern, quoted_replacement, english_question)
                else:
                    question = re.sub(pattern, replacement_text, question)
                    english_question = re.sub(pattern, replacement_text, english_question)
                
                # Replace in SPARQL
                if "uri" in replacement:
                    sparql_value = f"<{replacement['uri']}>"
                elif "sparqlValue" in replacement:
                    sparql_value = replacement["sparqlValue"]
                else:
                    sparql_value = replacement["value"]
                    
                sparql = re.sub(pattern, sparql_value, sparql)
            
            # Replace all prefixed URIs with full URIs
            for prefix, uri in self.prefixes.items():
                pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
                sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
            
            # Format the SPARQL query for readability
            sparql = self.format_sparql(sparql)
            
            return {"question": question, "englishQuestion": english_question, "sparql": sparql}
                
        except Exception as e:
            print("Query: ", discovery_query)
            print(f"Error executing discovery query for template {template['id']}: {e}")
            # Fall back to the old method
            return self.instantiate_template(template)

    def instantiate_template_without_placeholders(self, template):
        """
        Special handler for templates without placeholders (like aggregation queries)
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query
        """
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Use the templates as is (no placeholders to replace)
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}
    
    def instantiate_keyword_template(self, template):
        """
        Special handler for keyword-based templates using pre-extracted keywords
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Get a keyword from our pre-extracted list
        keyword = self.select_keyword_value()
        
        # Apply the keyword to the template
        replacements = {"value": keyword}
        
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace the placeholder in question and query
        pattern = r"{[\s]*value[\s]*}"
        
        # Replace in question
        replacement_text = keyword.get("label", keyword.get("value", ""))
        # For keyword templates, the quotes are already included in the template
        # so we don't need to add them here
        question = re.sub(pattern, replacement_text, question)
        english_question = re.sub(pattern, replacement_text, english_question)
        
        # Replace in SPARQL
        sparql_value = keyword.get("sparqlValue", f'"{keyword["value"]}"')
        
        sparql = re.sub(pattern, sparql_value, sparql)
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}

    def create_discovery_query(self, template, placeholders):
        """
        Create a discovery query that finds valid values for all placeholders
        
        Args:
            template (dict): The template to convert
            placeholders (set): Set of placeholders in the template
            
        Returns:
            str: The discovery query
        """
        sparql_template = template["sparqlTemplate"].strip()
        
        # Special handling for keyword-based templates
        if "keyword" in template["id"] and "value" in placeholders:
            # For these templates, we'll use our pre-extracted keywords
            # rather than trying to discover them from the SPARQL endpoint
            return None
        
        # Check if this is a complex query with aggregation, grouping, or ordering
        complexity_indicators = ['COUNT(', 'MAX(', 'MIN(', 'AVG(', 'SUM(', 'GROUP BY', 'ORDER BY', 'HAVING']
        is_complex_query = any(indicator in sparql_template.upper() for indicator in complexity_indicators)
        
        if is_complex_query:
            return self.create_simplified_discovery_query(template, placeholders)
        
        # Extract the WHERE clause more carefully
        # First normalize the template by removing extra whitespace
        normalized_template = re.sub(r'\s+', ' ', sparql_template)
        
        # Find the WHERE clause - look for WHERE { ... } but be careful about nested braces
        where_start = normalized_template.find('WHERE {')
        if where_start == -1:
            print(f"Error: Could not find WHERE clause in template: {template['id']}")
            return None
        
        # Find the matching closing brace
        brace_count = 0
        where_content_start = where_start + len('WHERE {')
        where_end = where_content_start
        
        for i, char in enumerate(normalized_template[where_content_start:], where_content_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    where_end = i
                    break
                brace_count -= 1
        
        if where_end == where_content_start:
            print(f"Error: Could not find end of WHERE clause in template: {template['id']}")
            return None
            
        where_clause = normalized_template[where_content_start:where_end].strip()
        
        # Replace placeholders with variables in the WHERE clause
        modified_where = where_clause
        for placeholder in placeholders:
            # Handle quoted placeholders first
            quoted_pattern = r'"{\s*' + re.escape(placeholder) + r'\s*}"'
            modified_where = re.sub(quoted_pattern, f"?{placeholder}", modified_where)
            
            # Then handle regular placeholders
            regular_pattern = r'{\s*' + re.escape(placeholder) + r'\s*}'
            modified_where = re.sub(regular_pattern, f"?{placeholder}", modified_where)
        
        # Build SELECT clause with only the placeholder variables we need
        select_vars = []
        
        # Add all placeholder variables to SELECT clause
        for placeholder in placeholders:
            select_vars.append(f"?{placeholder}")
            # For entity placeholders, also select label if available
            if placeholder.startswith('entity'):
                select_vars.append(f"?{placeholder}Label")
        
        # Construct the discovery query step by step
        select_clause = "SELECT DISTINCT " + " ".join(select_vars)
        where_clause_with_optionals = f"WHERE {{ {modified_where}"
        
        # Add OPTIONAL label patterns for entity placeholders
        optional_clauses = []
        for placeholder in placeholders:
            if placeholder.startswith('entity'):
                optional_clauses.append(f"OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label }}")
                optional_clauses.append(f"OPTIONAL {{ ?{placeholder} <https://schema.org/name> ?{placeholder}Label }}")
        
        # Combine all parts
        if optional_clauses:
            discovery_query = f"{select_clause} {where_clause_with_optionals} {' '.join(optional_clauses)} }} LIMIT 100"
        else:
            discovery_query = f"{select_clause} {where_clause_with_optionals} }} LIMIT 100"
        
        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            discovery_query = re.sub(pattern, r'<' + uri + r'\1>', discovery_query)
        
        # Final cleanup - remove any double spaces and ensure proper formatting
        discovery_query = re.sub(r'\s+', ' ', discovery_query).strip()
        
        return discovery_query
    
    def create_simplified_discovery_query(self, template, placeholders):
        """
        Create a simplified discovery query for complex templates with aggregation/grouping
        
        Args:
            template (dict): The template to convert
            placeholders (set): Set of placeholders in the template
            
        Returns:
            str: The simplified discovery query
        """
        template_id = template["id"]
        
        # Create specific discovery queries based on template patterns
        if "publication-count" in template_id:
            if "person" in template_id:
                # For person publication count queries
                return """
                    SELECT DISTINCT ?entity ?entityLabel WHERE {
                        ?publication <https://schema.org/author> ?entity .
                        OPTIONAL { ?entity rdfs:label ?entityLabel }
                        OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                    } LIMIT 50
                """
            elif "organization" in template_id:
                # For organization publication count queries
                return """
                    SELECT DISTINCT ?entity ?entityLabel WHERE {
                        { ?publication <https://schema.org/publisher> ?entity } UNION
                        { ?publication <https://schema.org/contributor> ?entity }
                        OPTIONAL { ?entity rdfs:label ?entityLabel }
                        OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                    } LIMIT 50
                """
            elif "topic" in template_id:
                # For topic-based publication count queries, use keywords
                return None  # Will fall back to keyword selection
            elif "year" in template_id:
                # For year-based publication count queries
                return """
                    SELECT DISTINCT ?value WHERE {
                        ?publication <https://schema.org/datePublished> ?date .
                        BIND(SUBSTR(STR(?date), 0, 5) AS ?value)
                    } LIMIT 20
                """
        elif "latest-publication" in template_id or "first-publication" in template_id:
            # For latest/first publication queries
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?publication <https://schema.org/author> ?entity .
                    ?publication <https://schema.org/datePublished> ?date .
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                } LIMIT 50
            """
        elif "collaborator-count" in template_id:
            # For collaborator count queries
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?entity a <https://schema.org/ScholarlyArticle> .
                    ?entity <https://schema.org/author> ?author1 .
                    ?entity <https://schema.org/author> ?author2 .
                    FILTER(?author1 != ?author2)
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                } LIMIT 50
            """
        elif "top-expert" in template_id:
            # For top expert queries, use keywords
            return None  # Will fall back to keyword selection
        elif "top-contributor" in template_id:
            # For top contributor queries - only select organizations that have publications WITH authors/contributors
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?publication <https://schema.org/publisher> ?entity .
                    ?publication <https://schema.org/author>|<https://schema.org/contributor> ?contributor .
                    ?contributor <https://schema.org/name> ?contributorName .
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                } LIMIT 50
            """
        elif "most-authors" in template_id or "most-productive" in template_id or "most-collaborative" in template_id:
            # For "most" queries, no placeholders needed
            return None
        elif "most-diverse" in template_id:
            # For most diverse publication queries
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?entity <https://schema.org/about> ?topic1 .
                    ?entity <https://schema.org/about> ?topic2 .
                    FILTER(?topic1 != ?topic2)
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                } LIMIT 50
            """
        elif "publications-by-year" in template_id:
            # For year trend queries, no placeholders needed
            return None
        elif "location-topic-distribution" in template_id:
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?resource gesiskg:libraryLocation ?entity .
                    ?resource schema:about ?topic .
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity schema:name ?entityLabel }
                } 
                GROUP BY ?entity ?entityLabel
                HAVING (COUNT(?resource) > 3)
                LIMIT 50
            """
        
        elif "location-resource-count" in template_id:
            # For counting resources at a specific library location
            return """
                SELECT DISTINCT ?entity ?entityLabel WHERE {
                    ?resource <https://data.gesis.org/gesiskg/schema/libraryLocation> ?entity .
                    OPTIONAL { ?entity rdfs:label ?entityLabel }
                    OPTIONAL { ?entity <https://schema.org/name> ?entityLabel }
                }
                GROUP BY ?entity ?entityLabel
                HAVING (COUNT(?resource) > 0)
                LIMIT 50
            """
        
        # Default fallback for unknown complex patterns
        print(f"Warning: No specific discovery pattern for complex template: {template_id}")
        return None
    
    def instantiate_template(self, template):
        """
        Original method to instantiate a template with specific entities and properties
        Kept as a fallback method
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Select entities and properties appropriate for this template
        placeholders = self.extract_placeholders(template)
        replacements = self.select_replacements(placeholders, template)
        
        if not replacements:
            return None
        
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Add prefixes to SPARQL query
        prefix_string = ""
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        sparql = prefix_string + sparql
        
        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
            
            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            # Add quotes around entity placeholders, but not other placeholders like 'value'
            if placeholder.startswith('entity'):
                quoted_replacement = f"'{replacement_text}'"
                question = re.sub(pattern, quoted_replacement, question)
                english_question = re.sub(pattern, quoted_replacement, english_question)
            else:
                question = re.sub(pattern, replacement_text, question)
                english_question = re.sub(pattern, replacement_text, english_question)
            
            # Replace in SPARQL
            if "uri" in replacement:
                sparql_value = f"<{replacement['uri']}>"
            elif "sparqlValue" in replacement:
                sparql_value = replacement["sparqlValue"]
            else:
                sparql_value = replacement["value"]
                
            sparql = re.sub(pattern, sparql_value, sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}

    def extract_placeholders(self, template):
        """
        Extract all placeholders from template
        
        Args:
            template (dict): Template with question and SPARQL
            
        Returns:
            set: Set of placeholder names
        """
        placeholders = set()
        
        # For Python triple-quoted strings, we need to handle whitespace
        # First, normalize the templates by removing extra whitespace
        # Check first question template - all should have the same placeholders
        question_template = template["questionTemplates"][0].strip()
        english_question = template["englishQuestionTemplates"][0].strip()
        sparql_template = template["sparqlTemplate"].strip()
        
        # Use a pattern that matches content between curly braces
        # This pattern is more restrictive to avoid matching SPARQL syntax
        pattern = r'{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*}'
        
        # Search in question template
        for match in re.finditer(pattern, question_template):
            placeholders.add(match.group(1).strip())
            
        # Search in English question template (for consistency)
        for match in re.finditer(pattern, english_question):
            placeholders.add(match.group(1).strip())
        
        # Search in SPARQL template
        for match in re.finditer(pattern, sparql_template):
            placeholders.add(match.group(1).strip())
        
        return placeholders

    def select_replacements(self, placeholders, template):
        """
        Select appropriate replacements for template placeholders
        
        Args:
            placeholders (set): Set of placeholder names
            template (dict): The template being instantiated
            
        Returns:
            dict: Map of placeholder to replacement value or None if failed
        """
        replacements = {}
        
        # Try to select appropriate values for each placeholder
        for placeholder in placeholders:
            replacement = None
            
            # Handle entity placeholders
            if placeholder.startswith('entity'):
                replacement = self.select_entity_from_endpoint(template)
                
                if not replacement:
                    # Select entity based on template type
                    if "publication" in template["id"]:
                        # For publication templates, select a CreativeWork entity
                        replacement = self.select_entity_by_type("schema:CreativeWork")
                    elif "person" in template["id"]:
                        # For person templates, select a Person entity
                        replacement = self.select_entity_by_type("schema:Person")
                    elif "organization" in template["id"]:
                        # For organization templates, select an Organization entity
                        replacement = self.select_entity_by_type("schema:Organization")
                    else:
                        # Default to any entity
                        replacement = self.select_random_entity()
                
                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()
            
            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                replacement = self.select_value_from_endpoint(template, placeholder)
                
                # If we didn't get a replacement, use predefined values
                if not replacement:
                    if "year" in template["id"]:
                        # For year, use a year
                        replacement = self.select_year_value()
                    elif "keyword" in template["id"] or "topic" in template["id"]:
                        # For keywords or topics, use a keyword
                        replacement = self.select_keyword_value()
                    else:
                        replacement = self.select_random_value(template)
            
            # Handle property placeholders
            elif placeholder.startswith('property'):
                replacement = self.select_scholarly_property(template, placeholder)
            
            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None
            
            replacements[placeholder] = replacement
        
        return replacements

    def select_entity_from_endpoint(self, template):
        """
        Select an entity from the SPARQL endpoint that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            
        Returns:
            dict: Selected entity info or None if not found
        """
        sparql_template = template["sparqlTemplate"]
        
        # Extract the predicate pattern for the entity
        # Look for patterns like: {entity} predicate ?object
        predicate_match = re.search(r'{\s*entity\s*}\s+([^\s.{}<>]+)\s+', sparql_template)
        
        if not predicate_match:
            # Try the inverse pattern: ?subject predicate {entity}
            predicate_match = re.search(r'([^\s.{}<>]+)\s+{\s*entity\s*}', sparql_template)
            if predicate_match:
                # This is an inverse relationship
                predicate = predicate_match.group(1)
                
                # Handle RDF/SPARQL prefixes
                if ':' in predicate:
                    prefix, local_name = predicate.split(':', 1)
                    if prefix in self.prefixes:
                        predicate_uri = f"{self.prefixes[prefix]}{local_name}"
                    else:
                        # Unknown prefix, can't construct URI
                        return None
                else:
                    # Not a prefixed name, use as is
                    predicate_uri = predicate
                    
                # Create the query to find valid objects for this predicate
                query = f"""
                    SELECT DISTINCT ?entity ?label
                    WHERE {{
                        ?subj <{predicate_uri}> ?entity .
                        OPTIONAL {{ ?entity rdfs:label ?label }}
                        OPTIONAL {{ ?entity <https://schema.org/name> ?label }}
                    }}
                    LIMIT 50
                """
                
                try:
                    # Execute query against the endpoint
                    results = self.sparql_exec.execute_query(query)
                    
                    if not results:
                        return None
                        
                    # Randomly select one entity from the results
                    selected = random.choice(results)
                    entity_uri = selected["entity"]
                    
                    # Use label if available, otherwise extract from URI
                    if "label" in selected and selected["label"]:
                        entity_label = selected["label"]
                    else:
                        entity_label = self.extract_label_from_uri(entity_uri)
                        
                    return {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri
                    }
                    
                except Exception as e:
                    print(f"Error selecting entity from endpoint: {e}")
                    return None
        
        if not predicate_match:
            return None
            
        predicate = predicate_match.group(1)
        
        # Handle RDF/SPARQL prefixes
        if ':' in predicate:
            prefix, local_name = predicate.split(':', 1)
            if prefix in self.prefixes:
                predicate_uri = f"{self.prefixes[prefix]}{local_name}"
            else:
                # Unknown prefix, can't construct URI
                return None
        else:
            # Not a prefixed name, use as is
            predicate_uri = predicate
            
        # Create the query to find valid subjects for this predicate
        query = f"""
            SELECT DISTINCT ?entity ?label
            WHERE {{
                ?entity <{predicate_uri}> ?obj .
                OPTIONAL {{ ?entity rdfs:label ?label }}
                OPTIONAL {{ ?entity <https://schema.org/name> ?label }}
            }}
            LIMIT 50
        """
        
        try:
            # Execute query against the endpoint
            results = self.sparql_exec.execute_query(query)
            
            if not results:
                return None
                
            # Randomly select one entity from the results
            selected = random.choice(results)
            entity_uri = selected["entity"]
            
            # Use label if available, otherwise extract from URI
            if "label" in selected and selected["label"]:
                entity_label = selected["label"]
            else:
                entity_label = self.extract_label_from_uri(entity_uri)
                
            return {
                "value": self.shorten_uri(entity_uri),
                "label": entity_label,
                "uri": entity_uri
            }
            
        except Exception as e:
            print(f"Error selecting entity from endpoint: {e}")
            return None

    def select_value_from_endpoint(self, template, placeholder):
        """
        Select a value from the SPARQL endpoint that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            placeholder (str): The name of the placeholder
            
        Returns:
            dict: Selected value info or None if not found
        """
        # For year values in publications
        if "publications-by-year" in template["id"]:
            # Extract a list of years from the endpoint
            query = """
                SELECT DISTINCT ?year
                WHERE {
                    ?publication <https://schema.org/datePublished> ?date .
                    BIND(SUBSTR(STR(?date), 0, 5) AS ?year)
                }
                ORDER BY ?year
            """
            
            try:
                results = self.sparql_exec.execute_query(query)
                if results:
                    # Pick a random year from results
                    year_value = str(random.choice(results)["year"])
                    return {
                        "value": year_value,
                        "label": year_value,
                        "sparqlValue": f'"{year_value}"'
                    }
            except Exception as e:
                print(f"Error querying for years: {e}")
        
        # For keyword values in keyword-based queries
        elif "keyword" in template["id"] or "topic" in template["id"]:
            # Use our pre-extracted keywords
            return self.select_keyword_value()
            
        return None

    def select_entity_by_type(self, type_value):
        """
        Select a random entity of a specific type
        
        Args:
            type_value (str): Type value (e.g. schema:CreativeWork)
            
        Returns:
            dict: Selected entity or None
        """
        # Filter entities by type
        matching_entities = [e for e in self.entity_examples if e.get("type") == type_value]
        
        if matching_entities:
            return random.choice(matching_entities)
        
        return None

    def select_random_entity(self):
        """
        Select a random entity from available examples
        
        Returns:
            dict: Selected entity
        """
        # If we have entity examples from the schema extractor, use them
        if self.entity_examples:
            return random.choice(self.entity_examples)
        
        # Fallback to predefined scholarly entities
        # This ensures we always have something workable for the GESIS KG
        scholarly_entities = [
            {"value": "schema:Dataset1", "label": "Dataset on Social Science Research", 
             "uri": "https://data.gesis.org/gesiskg/resource/dataset-001", "type": "schema:Dataset"},
            {"value": "schema:Publication1", "label": "Analysis of Social Media Usage", 
             "uri": "https://data.gesis.org/gesiskg/resource/publication-001", "type": "schema:CreativeWork"},
            {"value": "schema:Author1", "label": "Dr. Jane Smith", 
             "uri": "https://data.gesis.org/gesiskg/resource/person-001", "type": "schema:Person"},
            {"value": "schema:Organization1", "label": "GESIS - Leibniz Institute for the Social Sciences", 
             "uri": "https://data.gesis.org/gesiskg/resource/organization-001", "type": "schema:Organization"},
            {"value": "schema:Journal1", "label": "Journal of Social Science Research", 
             "uri": "https://data.gesis.org/gesiskg/resource/journal-001", "type": "schema:Periodical"}
        ]
        
        print("Warning: Using fallback scholarly entities")
        return random.choice(scholarly_entities)

    def select_scholarly_property(self, template, placeholder):
        """
        Select a property appropriate for scholarly templates
        
        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name
            
        Returns:
            dict: Selected property
        """
        # Define common scholarly properties
        scholarly_properties = {
            "author": {"value": "schema:author", "label": "author", 
                      "uri": "https://schema.org/author"},
            "title": {"value": "schema:name", "label": "name", 
                     "uri": "https://schema.org/name"},
            "date": {"value": "schema:datePublished", "label": "date published", 
                    "uri": "https://schema.org/datePublished"},
            "publisher": {"value": "schema:publisher", "label": "publisher", 
                         "uri": "https://schema.org/publisher"},
            "topic": {"value": "schema:about", "label": "about", 
                     "uri": "https://schema.org/about"},
            "citation": {"value": "schema:citation", "label": "citation", 
                        "uri": "https://schema.org/citation"},
            "contributor": {"value": "schema:contributor", "label": "contributor", 
                           "uri": "https://schema.org/contributor"},
            "keywords": {"value": "schema:keywords", "label": "keywords", 
                        "uri": "https://schema.org/keywords"}
        }
        
        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "author" in template["id"] or "author" in placeholder:
                prop = self.find_property_by_name("author")
                if prop:
                    return prop
                
            elif "title" in template["id"] or "title" in placeholder:
                prop = self.find_property_by_name("name")
                if prop:
                    return prop
                
            elif "date" in template["id"] or "date" in placeholder:
                prop = self.find_property_by_name("datePublished")
                if prop:
                    return prop
                
            elif "publisher" in template["id"] or "publisher" in placeholder:
                prop = self.find_property_by_name("publisher")
                if prop:
                    return prop
                
            elif "topic" in template["id"] or "topic" in placeholder:
                prop = self.find_property_by_name("about")
                if prop:
                    return prop
                
            elif "citation" in template["id"] or "citation" in placeholder:
                prop = self.find_property_by_name("citation")
                if prop:
                    return prop
        
        # If we don't have the property in schema info, use our predefined ones
        if "author" in template["id"] or "author" in placeholder:
            return scholarly_properties["author"]
            
        elif "title" in template["id"] or "title" in placeholder:
            return scholarly_properties["title"]
            
        elif "date" in template["id"] or "date" in placeholder:
            return scholarly_properties["date"]
            
        elif "publisher" in template["id"] or "publisher" in placeholder:
            return scholarly_properties["publisher"]
            
        elif "topic" in template["id"] or "topic" in placeholder:
            return scholarly_properties["topic"]
            
        elif "citation" in template["id"] or "citation" in placeholder:
            return scholarly_properties["citation"]
            
        # Fallback to any property if we can't find a specific match
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return random.choice(self.schema_info["properties"])
            
        # Last resort - return title as default
        return scholarly_properties["title"]

    def select_year_value(self):
        """
        Select a realistic year value for scholarly publications
        
        Returns:
            dict: Year value object
        """
        years = list(range(1990, 2025))
        value = random.choice(years)
        return {"value": str(value), "label": str(value), "sparqlValue": f'"{value}"'}

    def select_keyword_value(self):
        """
        Select a keyword value for searching scholarly publications
        
        Returns:
            dict: Keyword value object
        """
        # Use the pre-extracted keywords if available
        if self.extracted_keywords:
            value = random.choice(self.extracted_keywords)
        else:
            # Fallback to predefined keywords
            print("Using fallback keywords")
            value = random.choice(self.fallback_keywords)
            
        return {"value": value, "label": value, "sparqlValue": f'"{value}"'}

    def select_random_value(self, template):
        """
        Select a random appropriate value
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Special handling for scholarly data
        if template.get("category") == "scholarly":
            if "year" in template["id"]:
                return self.select_year_value()
            elif "keyword" in template["id"] or "topic" in template["id"]:
                return self.select_keyword_value()
            
        # Default to a generic value
        dummy_value = random.randint(1, 10)
        return {"value": str(dummy_value), "label": str(dummy_value)}

    def find_property_by_name(self, name):
        """
        Find a property by name in schema info
        
        Args:
            name (str): Property name to find
            
        Returns:
            dict: Found property or None
        """
        if "properties" not in self.schema_info:
            return None
        
        for prop in self.schema_info["properties"]:
            if (name in prop["value"] or 
                name in prop["label"] or 
                (prop.get("uri", "").split("/")[-1] == name)):
                return prop
        
        return None

    def extract_label_from_uri(self, uri):
        """
        Extract a human-readable label from a URI
        
        Args:
            uri (str): URI to extract label from
            
        Returns:
            str: Human-readable label
        """
        return gesis_entity_label(uri)

    def shorten_uri(self, uri):
        """
        Shorten a URI using known prefixes
        
        Args:
            uri (str): URI to shorten
            
        Returns:
            str: Shortened URI
        """
        for prefix, namespace in self.prefixes.items():
            if uri.startswith(namespace):
                return f"{prefix}:{uri[len(namespace):]}"
        
        return uri

    def format_sparql(self, sparql):
        """
        Format SPARQL query for readability with properly formatted URIs
        
        Args:
            sparql (str): Raw SPARQL query
            
        Returns:
            str: Formatted SPARQL query
        """
        # First, clean URIs by removing spaces within angle brackets
        def clean_uri(match):
            uri = match.group(0)
            # Remove all spaces from URIs
            return uri.replace(" ", "")
        
        # Fix all URIs first by removing spaces
        sparql = re.sub(r'<[^>]+>', clean_uri, sparql)
        
        # Now proceed with other formatting
        sparql = re.sub(r'PREFIX\s+\w+:\s+<[^>]+>\s*', '', sparql)
        sparql = re.sub(r'\s+', ' ', sparql)
        
        # Format spaces around keywords properly
        sparql = re.sub(r'(?i)\bSELECT\b', 'SELECT', sparql)
        sparql = re.sub(r'(?i)\bWHERE\b', ' WHERE ', sparql)
        sparql = re.sub(r'(?i)\bFILTER\b', ' FILTER ', sparql)
        sparql = re.sub(r'(?i)\bORDER BY\b', ' ORDER BY ', sparql)
        sparql = re.sub(r'(?i)\bLIMIT\b', ' LIMIT ', sparql)
        sparql = re.sub(r'(?i)\bGROUP BY\b', ' GROUP BY ', sparql)
        sparql = re.sub(r'(?i)\bHAVING\b', ' HAVING ', sparql)
        sparql = re.sub(r'(?i)\bCOUNT\b', 'COUNT', sparql)
        sparql = re.sub(r'(?i)\bAS\b', ' AS ', sparql)
        sparql = re.sub(r'(?i)\bDISTINCT\b', 'DISTINCT ', sparql)
        sparql = re.sub(r'(?i)\bUNION\b', ' UNION ', sparql)
        sparql = re.sub(r'(?i)\bOPTIONAL\b', ' OPTIONAL ', sparql)
        
        # Format braces
        sparql = re.sub(r'\s*{\s*', ' { ', sparql)
        sparql = re.sub(r'\s*}\s*', ' } ', sparql)
        
        # Final cleanup of any double spaces
        sparql = re.sub(r'\s+', ' ', sparql).strip()
        
        return sparql

    def export_json(self, dataset):
        """
        Export dataset to JSON format
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: JSON string
        """
        # Create a copy of the dataset to avoid modifying the original
        export_dataset = []
        
        for item in dataset:
            export_item = item.copy()
            
            # Ensure we have consistent field names
            if "englishQuestion" in export_item and "question" not in export_item:
                export_item["question"] = export_item["englishQuestion"]
            
            export_dataset.append(export_item)
        
        return json.dumps(export_dataset, indent=2)

    def export_csv(self, dataset):
        """
        Export dataset to CSV format
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Determine which fields are present in the dataset
        sample_item = dataset[0] if dataset else {}
        
        # Check if we're dealing with university data or GESIS data
        is_gesis_format = "englishQuestion" in sample_item
        
        # Set the header based on dataset type
        if is_gesis_format:
            # GESIS data format
            header = ['id', 'englishQuestion', 'sparql', 'category', 'complexity', 'templateId']
        else:
            # University course data format
            header = ['id', 'question', 'sparql', 'category', 'complexity', 'templateId']
        
        # Write header
        writer.writerow(header)
        
        # Write rows
        for item in dataset:
            sparql_escaped = item["sparql"].replace("\n", " ")
            
            # Get the question field based on the dataset type
            question_field = item.get("englishQuestion", item.get("question", ""))
            
            row = [
                item["id"],
                question_field,
                sparql_escaped,
                item.get("category", ""),
                item.get("complexity", ""),
                item.get("templateId", "")
            ]
            
            writer.writerow(row)
        
        return output.getvalue()

    def export_jsonl(self, dataset):
        """
        Export dataset to JSONL format (one JSON object per line)
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: JSONL string
        """
        return "\n".join(json.dumps(item) for item in dataset)