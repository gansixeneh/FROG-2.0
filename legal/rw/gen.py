"""
Enhanced Pattern-based SPARQL Query Generator using SPARQLWrapper with Apache Jena Endpoint

This generator creates SPARQL queries based on graph patterns using a discovery-first approach.
Modified to produce output matching the template-based generator format, including:
- Entity and property labels extraction
- Entity and property matching using Weaviate
- Compatible output format with template-based generator

Patterns:
- O = Fixed entity (known)
- X = Hidden variable (connects but not asked about)
- ? = Target variable (what we're asking for)

Case 1 (1 property): ? — O, O — ?
Case 2 (2 properties): O—?—O, ?—X—O
Case 3 (3 properties): O—X—X—?, O—X—?—O, X branches to O,O,?
"""

import json
import random
import re
import csv
import os
import logging
from collections import defaultdict, Counter
from SPARQLWrapper import SPARQLWrapper, JSON  # Using SPARQLWrapper instead of requests
from datetime import datetime
import sys

# Add NLTK imports for improved text processing
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from property_retrieval import LegalPropertyRetrieval  # Import PropertyRetrieval
from kg_schema_extractor import legal_entity_label, legal_property_label, separate_camel_case

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SPARQLWrapperClient:
    def __init__(
        self, endpoint_url="http://localhost:3030/modified-lex2kg/query", prefixes=None
    ):
        """Initialize the SPARQLWrapper client with explicit prefixes

        Args:
            endpoint_url (str): URL of the SPARQL endpoint
            prefixes (dict): Dictionary of prefix-namespace mappings
        """
        from SPARQLWrapper import SPARQLWrapper, JSON

        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(30)  # 30 second timeout

        # Set default prefixes if none provided
        if prefixes is None:
            self.prefixes = {
                "lex2kg-o": "<https://example.org/lex2kg/ontology/>",
                "rdfs": "<https://www.w3.org/2000/01/rdf-schema#>",
                "xsd": "<http://www.w3.org/2001/XMLSchema#>",
            }
        else:
            self.prefixes = prefixes

    def _format_prefixes(self):
        """Format the prefixes for inclusion in SPARQL queries"""
        prefix_str = ""
        for prefix, uri in self.prefixes.items():
            # Make sure the URI is properly wrapped in angle brackets
            if not uri.startswith("<"):
                uri = f"<{uri}>"
            prefix_str += f"PREFIX {prefix}: {uri}\n"
        return prefix_str

    def query(self, sparql_query):
        """Execute SPARQL query using SPARQLWrapper with explicit prefixes

        Args:
            sparql_query (str): SPARQL query without prefixes

        Returns:
            dict: Query results in JSON format
        """
        try:
            # Add prefixes to the query
            full_query = f"{self._format_prefixes()}\n{sparql_query}"

            self.sparql.setQuery(full_query)
            results = self.sparql.query().convert()
            return results  # Returns JSON format
        except Exception as e:
            print(f"Error querying SPARQL endpoint: {e}")
            return None


class PatternBasedSPARQLGenerator:
    def __init__(
        self, 
        endpoint_url="http://localhost:3030/modified-lex2kg/query", 
        prefixes=None
    ):
        """
        Initialize the pattern-based generator

        Args:
            endpoint_url (str): SPARQL endpoint URL
            prefixes (dict): Namespace prefixes
        """
        self.client = SPARQLWrapperClient(endpoint_url)

        if prefixes is None:
            self.prefixes = {
                "lex2kg-o": "https://example.org/lex2kg/ontology/",
                "rdfs": "https://www.w3.org/2000/01/rdf-schema#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
            }
        else:
            self.prefixes = prefixes

        # Properties to exclude for better quality
        self.excluded_properties = {
            # Universal properties (same value everywhere)
            "https://example.org/lex2kg/ontology/jenisPeraturan",
            # "https://example.org/lex2kg/ontology/yurisdiksi",
            "https://example.org/lex2kg/ontology/bahasa",
            # "https://example.org/lex2kg/ontology/jabatanPengesah",
            # Technical/internal properties
            "https://example.org/lex2kg/ontology/segmen",
            # "https://example.org/lex2kg/ontology/teks",
            # Over-granular properties
            # "https://example.org/lex2kg/ontology/huruf",
            "https://example.org/lex2kg/ontology/nomor",
        }

        # Extract entities and properties from endpoint
        self.entities = self._extract_entities()
        self.properties = self._extract_properties()

        # Pattern weights (higher = more likely)
        self.pattern_weights = {
            1: 0.5,  # 50% chance for 1-property patterns
            2: 0.3,  # 30% chance for 2-property patterns
            3: 0.2,  # 20% chance for 3-property patterns
        }

        # Initialize property retrieval system for entity and property matching
        try:
            self.property_retrieval = LegalPropertyRetrieval(
                endpoint_url=endpoint_url,
                embedding_model_name="jinaai/jina-embeddings-v3",
                is_local_client=True,
                weaviate_host="localhost",
                weaviate_port=8080,
            )
            print("Initialized LegalPropertyRetrieval successfully")
            
            # Test the connection and data availability
            self._test_weaviate_connection()
            
        except Exception as e:
            print(f"Error initializing PropertyRetrieval: {e}")
            import traceback
            traceback.print_exc()
            self.property_retrieval = None

        # Get total triple count
        total_triples = self._get_total_triples()
        print(f"Connected to SPARQL endpoint with {total_triples} triples")
        print(
            f"Found {len(self.entities)} entities and {len(self.properties)} properties"
        )

    def _test_weaviate_connection(self):
        """Test Weaviate connection and data availability"""
        if self.property_retrieval is None:
            print("Cannot test Weaviate - PropertyRetrieval is None")
            return
            
        try:
            # Test entity collection
            if hasattr(self.property_retrieval, 'df_entities'):
                entity_count = len(self.property_retrieval.df_entities)
                print(f"PropertyRetrieval loaded {entity_count} entities from SPARQL")
            
            # Test property collection  
            if hasattr(self.property_retrieval, 'df_properties'):
                property_count = len(self.property_retrieval.df_properties)
                print(f"PropertyRetrieval loaded {property_count} properties from SPARQL")
            
            # Test a simple search
            test_results = self.property_retrieval.search_entities("test", k=1)
            print(f"Test entity search returned {len(test_results)} results")
            
            test_results = self.property_retrieval.search_properties("test", k=1)
            print(f"Test property search returned {len(test_results)} results")
            
        except Exception as e:
            print(f"Error testing Weaviate connection: {e}")
            import traceback
            traceback.print_exc()

    def _get_property_exclusion_filters(self):
        """Generate SPARQL FILTER clauses to exclude low-quality properties"""
        filters = []
        for prop in self.excluded_properties:
            filters.append(f"?prop != <{prop}>")
            filters.append(f"?prop1 != <{prop}>")
            filters.append(f"?prop2 != <{prop}>")
            filters.append(f"?prop3 != <{prop}>")
        return " && ".join(set(filters))  # Remove duplicates with set()

    def _get_total_triples(self):
        """Get total number of triples in the dataset"""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = self.client.query(query)
        if result and result["results"]["bindings"]:
            return int(result["results"]["bindings"][0]["count"]["value"])
        return 0

    def _extract_entities(self):
        """Extract all entities from the endpoint"""
        query = """
        SELECT DISTINCT ?entity WHERE {
            {
                ?entity ?p ?o .
                FILTER(STRSTARTS(STR(?entity), "https://example.org/lex2kg/"))
            }
            UNION
            {
                ?s ?p ?entity .
                FILTER(STRSTARTS(STR(?entity), "https://example.org/lex2kg/"))
            }
        }
        LIMIT 10000
        """

        result = self.client.query(query)
        entities = []
        if result and result["results"]["bindings"]:
            entities = [
                binding["entity"]["value"] for binding in result["results"]["bindings"]
            ]

        return entities

    def _extract_properties(self):
        """Extract meaningful properties, excluding low-quality ones"""
        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.append(f"?property != <{prop}>")

        exclusion_filter_str = " && ".join(exclusion_filters)

        query = f"""
        SELECT DISTINCT ?property WHERE {{
            ?s ?property ?o .
            FILTER(STRSTARTS(STR(?property), "https://example.org/lex2kg/ontology/"))
            FILTER(?property != <https://www.w3.org/1999/02/22-rdf-syntax-ns#type>)
            FILTER(!STRSTARTS(STR(?property), "https://www.w3.org/2000/01/rdf-schema#"))
            FILTER({exclusion_filter_str})
        }}
        """

        result = self.client.query(query)
        properties = []
        if result and result["results"]["bindings"]:
            properties = [
                binding["property"]["value"]
                for binding in result["results"]["bindings"]
            ]

        return properties

    def _shorten_uri(self, uri):
        """Convert full URI to prefixed form - only for ontology properties, keep entities as full URIs"""
        uri_str = str(uri)

        # Only use lex2kg-o prefix for ontology properties (they don't contain forward slashes after the ontology part)
        if uri_str.startswith("https://example.org/lex2kg/ontology/"):
            return f"lex2kg-o:{uri_str[len('https://example.org/lex2kg/ontology/'):]}"

        # For other prefixes like rdfs, xsd
        for prefix, namespace in self.prefixes.items():
            if prefix != "lex2kg-o" and uri_str.startswith(namespace):
                return f"{prefix}:{uri_str[len(namespace):]}"

        # For entities (which contain forward slashes), keep as full URI in angle brackets
        return f"<{uri_str}>"

    def _expand_uri(self, shortened_uri):
        """Convert shortened URI back to full URI"""
        shortened_str = str(shortened_uri)
        
        # Handle lex2kg-o prefixed properties
        if shortened_str.startswith("lex2kg-o:"):
            property_name = shortened_str[len("lex2kg-o:"):]
            return f"https://example.org/lex2kg/ontology/{property_name}"
        
        # Handle lex2kg prefixed entities
        if shortened_str.startswith("lex2kg:"):
            entity_path = shortened_str[len("lex2kg:"):]
            return f"https://example.org/lex2kg/{entity_path}"
        
        # Handle other prefixes
        for prefix, namespace in self.prefixes.items():
            if shortened_str.startswith(f"{prefix}:"):
                suffix = shortened_str[len(f"{prefix}:"):]
                return f"{namespace}{suffix}"
        
        # If already a full URI (in angle brackets), remove brackets
        if shortened_str.startswith("<") and shortened_str.endswith(">"):
            return shortened_str[1:-1]
        
        # If already a full URI without brackets, return as is
        if shortened_str.startswith("http"):
            return shortened_str
            
        # Default: return as is
        return shortened_str

    def _format_sparql(self, sparql):
        """Format SPARQL query for readability"""
        # Clean up spacing
        sparql = re.sub(r"\s+", " ", sparql.strip())

        # Format SELECT and WHERE
        sparql = re.sub(r"SELECT\s+", "SELECT ", sparql)
        sparql = re.sub(r"\s+WHERE\s+", " WHERE ", sparql)

        # Format braces
        sparql = re.sub(r"\s*{\s*", " { ", sparql)
        sparql = re.sub(r"\s*}\s*", " }", sparql)

        return sparql

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

    def _extract_entities_and_properties_from_sparql(self, sparql):
        """
        Extract entity URIs and property URIs from a SPARQL query (improved version)

        Args:
            sparql (str): SPARQL query to analyze

        Returns:
            tuple: (entity_uris, property_uris)
        """
        entity_uris = []
        property_uris = []

        # Extract URIs in angle brackets
        uri_pattern = r'<([^>]+)>'
        angle_bracket_uris = re.findall(uri_pattern, sparql)

        # Extract prefixed URIs (like lex2kg-o:propertyName)
        prefixed_pattern = r'lex2kg-o:(\w+)'
        prefixed_properties = re.findall(prefixed_pattern, sparql)

        # Convert prefixed properties to full URIs
        for prop_name in prefixed_properties:
            full_uri = f"https://example.org/lex2kg/ontology/{prop_name}"
            property_uris.append(full_uri)

        # Classify URIs from angle brackets as entities or properties based on structure
        for uri in angle_bracket_uris:
            if self._is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)

        return entity_uris, property_uris

    def _is_property_uri(self, uri):
        """Check if a URI is a property URI based on patterns"""
        # Legal ontology properties start with the ontology namespace
        if uri.startswith("https://example.org/lex2kg/ontology/"):
            return True
        
        # Common property indicators
        property_indicators = ['has_', 'is_', 'contains', 'relates']
        
        for indicator in property_indicators:
            if indicator in uri.lower():
                return True
                
        return False

    def get_entities_and_properties(self, question, sparql):
        """Extract entities and properties from SPARQL query and get their labels (improved version)"""
        # Extract actual URIs from SPARQL query
        entity_uris, property_uris = self._extract_entities_and_properties_from_sparql(sparql)
        
        # Get labels for entities and properties using legal-specific functions
        entities_list = []
        properties_list = []
        
        # Get entity labels using legal_entity_label function
        for uri in entity_uris:
            try:
                label = legal_entity_label(uri)
                entities_list.append(label)
                print(f"Entity: {label} (from {uri})")
            except Exception as e:
                print(f"Error generating label for entity {uri}: {e}")
                # Fallback to simple extraction
                fallback_label = self._extract_label_from_uri(str(uri))
                entities_list.append(fallback_label)
                print(f"Entity (fallback): {fallback_label} (from {uri})")
        
        # Get property labels using legal_property_label function
        for uri in property_uris:
            try:
                label = legal_property_label(uri)
                properties_list.append(label)
                print(f"Property: {label} (from {uri})")
            except Exception as e:
                print(f"Error generating label for property {uri}: {e}")
                # Fallback to simple extraction
                fallback_label = self._extract_label_from_uri(str(uri))
                properties_list.append(fallback_label)
                print(f"Property (fallback): {fallback_label} (from {uri})")
        
        # Get entity and property candidates for Weaviate matching
        print(f"Searching Weaviate for question: '{question}'")
        print(f"With entities: {entities_list}")
        print(f"With properties: {properties_list}")
        
        property_candidates = entities_list + properties_list
        related_candidates = self.get_related_candidates(
            question, 
            property_candidates=property_candidates,
            threshold=0.4,  # Lower threshold
            k=5
        )
        
        # Format entity matches
        entity_matches = []
        if "entities" in related_candidates:
            for entity in related_candidates["entities"]:
                if isinstance(entity, dict) and 'short' in entity and 'label' in entity:
                    # Convert shortened URI to full URI
                    full_uri = self._expand_uri(entity['short'])
                    entity_matches.append({
                        "id": full_uri,
                        "label": entity['label'],
                    })
                    print(f"Entity match: {entity['label']} ({full_uri})")
        
        # Format property matches
        property_matches = []
        if "properties" in related_candidates:
            for property in related_candidates["properties"]:
                if isinstance(property, dict) and 'short' in property and 'label' in property:
                    # Convert shortened URI to full URI
                    full_uri = self._expand_uri(property['short'])
                    property_matches.append({
                        "id": full_uri,
                        "label": property['label'],
                    })
                    print(f"Property match: {property['label']} ({full_uri})")
        
        print(f"Final results: {len(entities_list)} entities, {len(properties_list)} properties")
        print(f"Weaviate matches: {len(entity_matches)} entity matches, {len(property_matches)} property matches")
        
        return entities_list, properties_list, entity_matches, property_matches

    def _extract_label_from_uri(self, uri):
        """
        Extract a human-readable label from a URI using legal-specific functions

        Args:
            uri (str): URI to extract label from

        Returns:
            str: Human-readable label
        """
        try:
            # Check if it's a property URI
            if self._is_property_uri(uri):
                return legal_property_label(uri)
            else:
                return legal_entity_label(uri)
        except Exception as e:
            print(f"Error using legal label functions for {uri}: {e}")
            # Fallback to simple extraction
            last_part = uri.split('/')[-1].split('#')[-1]
            
            # Legal document specific handling (simple fallback)
            if '_' in last_part:
                with_spaces = last_part.replace('_', ' ')
                return ' '.join(word.capitalize() for word in with_spaces.split())
            elif last_part.isdigit():
                return f"Item {last_part}"
            else:
                result = re.sub(r'([a-z])([A-Z])', r'\1 \2', last_part)
                
                # Handle common legal abbreviations and terms
                legal_terms = {
                    'uu': 'UU',
                    'pasal': 'Pasal',
                    'ayat': 'Ayat',
                    'huruf': 'Huruf',
                    'bab': 'Bab',
                    'bagian': 'Bagian',
                    'versi': 'Versi',
                    'tahun': 'Tahun'
                }
                
                words = result.split()
                processed_words = []
                for word in words:
                    lower_word = word.lower()
                    if lower_word in legal_terms:
                        processed_words.append(legal_terms[lower_word])
                    else:
                        processed_words.append(word.capitalize())
                
                return ' '.join(processed_words)

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """Preprocess question into tokens using NLTK RegexpTokenizer"""
        from nltk.tokenize import RegexpTokenizer
        from nltk.corpus import stopwords
        
        tok_pattern = r"\w+"
        tokenizer = RegexpTokenizer(tok_pattern)
        tokenized = tokenizer.tokenize(q)
        stopwords_set = set(stopwords.words('english'))
        
        result = []
        for tok in tokenized:
            tok = tok.lower()
            if tok not in stopwords_set:
                result.append(tok)
        return result

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """Generate n-grams from tokens using NLTK"""
        from nltk import ngrams
        
        result = []
        
        # Generate unigrams, bigrams, and trigrams using NLTK
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        
        return result

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.4,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity and property candidates using n-grams (improved version)"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type, threshold=threshold):
            """Search for entities or properties and format results"""
            try:
                # Search using the appropriate method
                if search_type == "entities":
                    df_res = self.property_retrieval.search_entities(ngram, k=k)
                else:
                    df_res = self.property_retrieval.search_properties(ngram, k=k)
                
                # Filter by threshold and format results
                filtered_results = []
                if not df_res.empty:
                    for _, row in df_res.iterrows():
                        score = row.get('score', 0)
                        if score >= threshold:
                            filtered_results.append({
                                'short': row.get('short', ''),
                                'label': row.get('label', ''),
                                'score': score
                            })
                            print(f"  Found {search_type[:-1]}: {row.get('label', '')} (score: {score:.3f})")
                
                return search_type, filtered_results
            except Exception as e:
                print(f"Error in search for '{ngram}' in {search_type}: {e}")
                return search_type, []

        # Search using n-grams and property candidates
        search_terms = ngrams + property_candidates
        print(f"Searching with terms: {search_terms}")
        
        for term in search_terms:
            print(f"Searching for: '{term}'")
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
            
        print(f"Total unique results: {len(result['entities'])} entities, {len(result['properties'])} properties")
        return result

    def generate_1_property_patterns(self, count=100):
        """
        Generate 1-property patterns using discovery-first approach

        Args:
            count (int): Number of patterns to generate

        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.append(f"?prop != <{prop}>")

        exclusion_filter_str = " && ".join(exclusion_filters)

        # Discovery query to find all valid property-entity combinations
        discovery_query = f"""
            SELECT DISTINCT ?prop ?entity WHERE {{
                ?s ?prop ?entity .
                FILTER(STRSTARTS(STR(?prop), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/lex2kg/"))
                FILTER({exclusion_filter_str})
            }}
            LIMIT 1000
        """

        print("Executing discovery query for 1-property patterns...")
        try:
            result = self.client.query(discovery_query)
            if not result or not result["results"]["bindings"]:
                return patterns

            results = [
                (binding["prop"]["value"], binding["entity"]["value"])
                for binding in result["results"]["bindings"]
            ]
            print(f"Found {len(results)} valid property-entity combinations")

            # Generate patterns by randomly selecting from valid combinations
            attempts = 0
            max_attempts = count * 3

            while len(patterns) < count and attempts < max_attempts:
                attempts += 1

                # Randomly select a valid combination
                prop, entity = random.choice(results)
                prop_str = self._shorten_uri(prop)
                entity_str = self._shorten_uri(entity)

                # Generate both subject and object target patterns
                pattern_type = random.choice(["subject_target", "object_target"])

                if pattern_type == "subject_target":
                    # Pattern: ?target prop fixed_entity
                    sparql = (
                        f"SELECT ?target WHERE {{ ?target {prop_str} {entity_str} . }}"
                    )
                    pattern_id = f"1p_subj_{len(patterns)}"
                    pattern_type_name = "1_prop_subject_target"
                else:
                    # Pattern: fixed_entity prop ?target
                    # Need to find a valid subject for this property
                    subject_query = f"""
                        SELECT DISTINCT ?subj WHERE {{
                            ?subj <{prop}> <{entity}> .
                        }}
                        LIMIT 1
                    """
                    subject_result = self.client.query(subject_query)
                    if not subject_result or not subject_result["results"]["bindings"]:
                        continue

                    subj = subject_result["results"]["bindings"][0]["subj"]["value"]
                    subj_str = self._shorten_uri(subj)
                    sparql = (
                        f"SELECT ?target WHERE {{ {subj_str} {prop_str} ?target . }}"
                    )
                    pattern_id = f"1p_obj_{len(patterns)}"
                    pattern_type_name = "1_prop_object_target"

                # Validate that this pattern has results
                if self._validate_pattern(sparql):
                    patterns.append(
                        {
                            "id": pattern_id,
                            "sparql": self._format_sparql(sparql),
                            "pattern_type": pattern_type_name,
                            "complexity": "basic",
                            "property": prop_str,
                            "fixed_entity": (
                                entity_str
                                if pattern_type == "subject_target"
                                else subj_str
                            ),
                        }
                    )

        except Exception as e:
            print(f"Error in 1-property pattern discovery: {e}")

        return patterns

    def generate_2_property_patterns(self, count=100):
        """
        Generate 2-property patterns using discovery-first approach

        Args:
            count (int): Number of patterns to generate

        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.extend([f"?prop1 != <{prop}>", f"?prop2 != <{prop}>"])

        exclusion_filter_str = " && ".join(exclusion_filters)

        # Discovery query for middle target pattern: entity1 prop1 ?target . ?target prop2 entity2
        middle_discovery_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?entity1 ?entity2 ?middle WHERE {{
                ?entity1 ?prop1 ?middle .
                ?middle ?prop2 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/lex2kg/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/lex2kg/"))
                FILTER(?prop1 != ?prop2)
                FILTER({exclusion_filter_str})
            }}
            LIMIT 500
        """

        # Discovery query for branching pattern: ?target prop1 ?hidden . ?hidden prop2 entity
        branching_discovery_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?entity WHERE {{
                ?target ?prop1 ?hidden .
                ?hidden ?prop2 ?entity .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/lex2kg/"))
                FILTER(?prop1 != ?prop2)
                FILTER({exclusion_filter_str})
            }}
            LIMIT 500
        """

        print("Executing discovery queries for 2-property patterns...")

        try:
            # Get middle target combinations
            middle_result = self.client.query(middle_discovery_query)
            middle_results = []
            if middle_result and middle_result["results"]["bindings"]:
                middle_results = [
                    (
                        binding["prop1"]["value"],
                        binding["prop2"]["value"],
                        binding["entity1"]["value"],
                        binding["entity2"]["value"],
                        binding["middle"]["value"],
                    )
                    for binding in middle_result["results"]["bindings"]
                ]
            print(f"Found {len(middle_results)} valid middle-target combinations")

            # Get branching combinations
            branching_result = self.client.query(branching_discovery_query)
            branching_results = []
            if branching_result and branching_result["results"]["bindings"]:
                branching_results = [
                    (
                        binding["prop1"]["value"],
                        binding["prop2"]["value"],
                        binding["entity"]["value"],
                    )
                    for binding in branching_result["results"]["bindings"]
                ]
            print(f"Found {len(branching_results)} valid branching combinations")

            all_combinations = []

            # Process middle target results
            for result in middle_results:
                all_combinations.append({"type": "middle_target", "data": result})

            # Process branching results
            for result in branching_results:
                all_combinations.append({"type": "branching", "data": result})

            if not all_combinations:
                return patterns

            # Generate patterns by randomly selecting from valid combinations
            attempts = 0
            max_attempts = count * 3

            while len(patterns) < count and attempts < max_attempts:
                attempts += 1

                combination = random.choice(all_combinations)

                if combination["type"] == "middle_target":
                    pattern = self._create_middle_target_pattern(
                        combination["data"], len(patterns)
                    )
                else:
                    pattern = self._create_branching_pattern(
                        combination["data"], len(patterns)
                    )

                if pattern:
                    patterns.append(pattern)

        except Exception as e:
            print(f"Error in 2-property pattern discovery: {e}")

        return patterns

    def _create_middle_target_pattern(self, data, pattern_index):
        """Create middle target pattern from discovery data"""
        prop1, prop2, entity1, entity2, middle = data

        prop1_str = self._shorten_uri(prop1)
        prop2_str = self._shorten_uri(prop2)
        entity1_str = self._shorten_uri(entity1)
        entity2_str = self._shorten_uri(entity2)

        # Generate random variation (4 possibilities)
        variation = random.randint(0, 3)

        variations = [
            f"{entity1_str} {prop1_str} ?target . ?target {prop2_str} {entity2_str}",  # original
            f"?target {prop1_str} {entity1_str} . {entity2_str} {prop2_str} ?target",  # both swapped
            f"{entity1_str} {prop1_str} ?target . {entity2_str} {prop2_str} ?target",  # second swapped
            f"?target {prop1_str} {entity1_str} . ?target {prop2_str} {entity2_str}",  # first swapped
        ]

        sparql = f"SELECT ?target WHERE {{ {variations[variation]} . }}"

        if self._validate_pattern(sparql):
            return {
                "id": f"2p_mid_{variation}_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": f"2_prop_middle_target_v{variation+1}",
                "complexity": "intermediate",
                "properties": [prop1_str, prop2_str],
                "fixed_entities": [entity1_str, entity2_str],
            }
        return None

    def _create_branching_pattern(self, data, pattern_index):
        """Create branching pattern from discovery data"""
        prop1, prop2, entity = data

        prop1_str = self._shorten_uri(prop1)
        prop2_str = self._shorten_uri(prop2)
        entity_str = self._shorten_uri(entity)

        # Generate random variation (4 possibilities)
        variation = random.randint(0, 3)

        variations = [
            f"?target {prop1_str} ?hidden . ?hidden {prop2_str} {entity_str}",  # original
            f"?hidden {prop1_str} ?target . {entity_str} {prop2_str} ?hidden",  # both swapped
            f"?target {prop1_str} ?hidden . {entity_str} {prop2_str} ?hidden",  # second swapped
            f"?hidden {prop1_str} ?target . ?hidden {prop2_str} {entity_str}",  # first swapped
        ]

        sparql = f"SELECT ?target WHERE {{ {variations[variation]} . }}"

        if self._validate_pattern(sparql):
            return {
                "id": f"2p_branch_{variation}_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": f"2_prop_branching_v{variation+1}",
                "complexity": "intermediate",
                "properties": [prop1_str, prop2_str],
                "fixed_entity": entity_str,
            }
        return None

    def generate_3_property_patterns(self, count=100):
        """
        Generate 3-property patterns using discovery-first approach

        Args:
            count (int): Number of patterns to generate

        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.extend(
                [f"?prop1 != <{prop}>", f"?prop2 != <{prop}>", f"?prop3 != <{prop}>"]
            )

        exclusion_filter_str = " && ".join(exclusion_filters)

        # Discovery query for linear end pattern: entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target
        linear_end_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity WHERE {{
                ?entity ?prop1 ?h1 .
                ?h1 ?prop2 ?h2 .
                ?h2 ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/lex2kg/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER({exclusion_filter_str})
            }}
            LIMIT 200
        """

        # Discovery query for linear middle pattern: entity1 prop1 ?h . ?h prop2 ?target . ?target prop3 entity2
        linear_middle_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {{
                ?entity1 ?prop1 ?h .
                ?h ?prop2 ?target .
                ?target ?prop3 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/lex2kg/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/lex2kg/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER({exclusion_filter_str})
            }}
            LIMIT 200
        """

        # Discovery query for star pattern: ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target
        star_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {{
                ?hidden ?prop1 ?entity1 .
                ?hidden ?prop2 ?entity2 .
                ?hidden ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/lex2kg/ontology/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/lex2kg/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/lex2kg/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER(?entity1 != ?entity2)
                FILTER({exclusion_filter_str})
            }}
            LIMIT 200
        """

        print("Executing discovery queries for 3-property patterns...")

        try:
            all_combinations = []

            # Get linear end combinations
            linear_end_result = self.client.query(linear_end_query)
            if linear_end_result and linear_end_result["results"]["bindings"]:
                for binding in linear_end_result["results"]["bindings"]:
                    all_combinations.append(
                        {
                            "type": "linear_end",
                            "data": (
                                binding["prop1"]["value"],
                                binding["prop2"]["value"],
                                binding["prop3"]["value"],
                                binding["entity"]["value"],
                            ),
                        }
                    )

            # Get linear middle combinations
            linear_middle_result = self.client.query(linear_middle_query)
            if linear_middle_result and linear_middle_result["results"]["bindings"]:
                for binding in linear_middle_result["results"]["bindings"]:
                    all_combinations.append(
                        {
                            "type": "linear_middle",
                            "data": (
                                binding["prop1"]["value"],
                                binding["prop2"]["value"],
                                binding["prop3"]["value"],
                                binding["entity1"]["value"],
                                binding["entity2"]["value"],
                            ),
                        }
                    )

            # Get star combinations
            star_result = self.client.query(star_query)
            if star_result and star_result["results"]["bindings"]:
                for binding in star_result["results"]["bindings"]:
                    all_combinations.append(
                        {
                            "type": "star",
                            "data": (
                                binding["prop1"]["value"],
                                binding["prop2"]["value"],
                                binding["prop3"]["value"],
                                binding["entity1"]["value"],
                                binding["entity2"]["value"],
                            ),
                        }
                    )

            print(
                f"Found {len([c for c in all_combinations if c['type'] == 'linear_end'])} linear-end combinations"
            )
            print(
                f"Found {len([c for c in all_combinations if c['type'] == 'linear_middle'])} linear-middle combinations"
            )
            print(
                f"Found {len([c for c in all_combinations if c['type'] == 'star'])} star combinations"
            )

            if not all_combinations:
                return patterns

            # Generate patterns by randomly selecting from valid combinations
            attempts = 0
            max_attempts = count * 3

            while len(patterns) < count and attempts < max_attempts:
                attempts += 1

                combination = random.choice(all_combinations)

                if combination["type"] == "linear_end":
                    pattern = self._create_linear_end_pattern(
                        combination["data"], len(patterns)
                    )
                elif combination["type"] == "linear_middle":
                    pattern = self._create_linear_middle_pattern(
                        combination["data"], len(patterns)
                    )
                else:
                    pattern = self._create_star_pattern(
                        combination["data"], len(patterns)
                    )

                if pattern:
                    patterns.append(pattern)

        except Exception as e:
            print(f"Error in 3-property pattern discovery: {e}")

        return patterns

    def _create_linear_end_pattern(self, data, pattern_index):
        """Create linear end pattern from discovery data"""
        prop1, prop2, prop3, entity = data

        props_str = [self._shorten_uri(p) for p in [prop1, prop2, prop3]]
        entity_str = self._shorten_uri(entity)

        # Generate random variation (8 possibilities using bit manipulation)
        variation = random.randint(0, 7)

        pattern_parts = []

        # Determine direction of each triple based on bit pattern
        if variation & 1:  # bit 0: reverse first triple
            pattern_parts.append(f"?hidden1 {props_str[0]} {entity_str}")
        else:
            pattern_parts.append(f"{entity_str} {props_str[0]} ?hidden1")

        if variation & 2:  # bit 1: reverse second triple
            pattern_parts.append(f"?hidden2 {props_str[1]} ?hidden1")
        else:
            pattern_parts.append(f"?hidden1 {props_str[1]} ?hidden2")

        if variation & 4:  # bit 2: reverse third triple
            pattern_parts.append(f"?target {props_str[2]} ?hidden2")
        else:
            pattern_parts.append(f"?hidden2 {props_str[2]} ?target")

        pattern = " . ".join(pattern_parts)
        sparql = f"SELECT ?target WHERE {{ {pattern} . }}"

        if self._validate_pattern(sparql):
            return {
                "id": f"3p_linear_end_{variation}_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": f"3_prop_linear_end_v{variation+1}",
                "complexity": "advanced",
                "properties": props_str,
                "fixed_entity": entity_str,
            }
        return None

    def _create_linear_middle_pattern(self, data, pattern_index):
        """Create linear middle pattern from discovery data"""
        prop1, prop2, prop3, entity1, entity2 = data

        props_str = [self._shorten_uri(p) for p in [prop1, prop2, prop3]]
        entity1_str = self._shorten_uri(entity1)
        entity2_str = self._shorten_uri(entity2)

        # Generate random variation (8 possibilities)
        variation = random.randint(0, 7)

        pattern_parts = []

        if variation & 1:  # bit 0
            pattern_parts.append(f"?hidden {props_str[0]} {entity1_str}")
        else:
            pattern_parts.append(f"{entity1_str} {props_str[0]} ?hidden")

        if variation & 2:  # bit 1
            pattern_parts.append(f"?target {props_str[1]} ?hidden")
        else:
            pattern_parts.append(f"?hidden {props_str[1]} ?target")

        if variation & 4:  # bit 2
            pattern_parts.append(f"{entity2_str} {props_str[2]} ?target")
        else:
            pattern_parts.append(f"?target {props_str[2]} {entity2_str}")

        pattern = " . ".join(pattern_parts)
        sparql = f"SELECT ?target WHERE {{ {pattern} . }}"

        if self._validate_pattern(sparql):
            return {
                "id": f"3p_linear_mid_{variation}_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": f"3_prop_linear_middle_v{variation+1}",
                "complexity": "advanced",
                "properties": props_str,
                "fixed_entities": [entity1_str, entity2_str],
            }
        return None

    def _create_star_pattern(self, data, pattern_index):
        """Create star pattern from discovery data"""
        prop1, prop2, prop3, entity1, entity2 = data

        props_str = [self._shorten_uri(p) for p in [prop1, prop2, prop3]]
        entity1_str = self._shorten_uri(entity1)
        entity2_str = self._shorten_uri(entity2)

        # Generate random variation (8 possibilities)
        variation = random.randint(0, 7)

        pattern_parts = []

        if variation & 1:  # bit 0
            pattern_parts.append(f"{entity1_str} {props_str[0]} ?hidden")
        else:
            pattern_parts.append(f"?hidden {props_str[0]} {entity1_str}")

        if variation & 2:  # bit 1
            pattern_parts.append(f"{entity2_str} {props_str[1]} ?hidden")
        else:
            pattern_parts.append(f"?hidden {props_str[1]} {entity2_str}")

        if variation & 4:  # bit 2
            pattern_parts.append(f"?target {props_str[2]} ?hidden")
        else:
            pattern_parts.append(f"?hidden {props_str[2]} ?target")

        pattern = " . ".join(pattern_parts)
        sparql = f"SELECT ?target WHERE {{ {pattern} . }}"

        if self._validate_pattern(sparql):
            return {
                "id": f"3p_star_{variation}_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": f"3_prop_star_v{variation+1}",
                "complexity": "advanced",
                "properties": props_str,
                "fixed_entities": [entity1_str, entity2_str],
            }
        return None

    def generate_dataset(self, size=1000):
        """Generate dataset based on pattern weights using discovery-first approach"""
        dataset = []

        # Calculate number of queries for each complexity level
        num_1_prop = int(size * self.pattern_weights[1])
        num_2_prop = int(size * self.pattern_weights[2])
        num_3_prop = size - num_1_prop - num_2_prop

        print(
            f"Generating {num_1_prop} 1-property, {num_2_prop} 2-property, {num_3_prop} 3-property patterns..."
        )

        try:
            # Generate patterns using discovery-first approach
            patterns_1 = self.generate_1_property_patterns(num_1_prop)
            print(f"Generated {len(patterns_1)} 1-property patterns")

            patterns_2 = self.generate_2_property_patterns(num_2_prop)
            print(f"Generated {len(patterns_2)} 2-property patterns")

            patterns_3 = self.generate_3_property_patterns(num_3_prop)
            print(f"Generated {len(patterns_3)} 3-property patterns")

            print(
                f"Generated {len(patterns_1)} 1-prop, {len(patterns_2)} 2-prop, {len(patterns_3)} 3-prop patterns"
            )

            all_patterns = patterns_1 + patterns_2 + patterns_3
            random.shuffle(all_patterns)

            # Convert to final format and assign sequential IDs
            for i, pattern in enumerate(all_patterns[:size]):
                print(f"\n--- Processing pattern {i+1}/{min(size, len(all_patterns))} ---")
                
                # Generate a simple question for the pattern
                question = self._generate_simple_question(pattern)
                
                # Extract entities and properties from the SPARQL query with Weaviate search
                sparql = pattern["sparql"]
                print(f"SPARQL: {sparql}")
                
                entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(question, sparql)
                
                # Add to dataset with enhanced fields
                dataset.append(
                    {
                        "id": f"q{i+1}",
                        "sparql": pattern["sparql"],
                        "pattern_type": pattern["pattern_type"],
                        "complexity": pattern["complexity"],
                        "category": "legal",  # Fixed category for legal domain
                        "entities": entities_list,
                        "properties": properties_list,
                        "entities_matches": entity_matches,
                        "properties_matches": property_matches
                    }
                )
                
                # Print progress every 5 items
                if (i + 1) % 5 == 0:
                    print(f"Processed {i + 1}/{min(size, len(all_patterns))} patterns")
                    
        except Exception as e:
            print(f"Error in dataset generation: {e}")

        return dataset

    def _generate_simple_question(self, pattern):
        """Generate a simple question based on the pattern type"""
        pattern_type = pattern.get("pattern_type", "unknown")
        
        if "1_prop" in pattern_type:
            if "subject_target" in pattern_type:
                return "What entities are related through this property?"
            else:
                return "What is the value of this property for this entity?"
        elif "2_prop" in pattern_type:
            if "middle_target" in pattern_type:
                return "What is the intermediate entity connecting these two entities?"
            else:
                return "What entities are connected through this two-hop relationship?"
        elif "3_prop" in pattern_type:
            if "linear_end" in pattern_type:
                return "What is at the end of this three-step path?"
            elif "linear_middle" in pattern_type:
                return "What is the middle entity in this three-step relationship?"
            else:
                return "What is the central hub in this star pattern relationship?"
        else:
            return "What is the result of this query pattern?"

    def export_json(self, dataset, output_path="pattern_based_dataset.json"):
        """Export dataset to JSON"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset exported to {output_path}")

    def export_csv(self, dataset, output_path="pattern_based_dataset.csv"):
        """Export dataset to CSV"""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "sparql", "pattern_type", "complexity", "category", 
                "entities", "properties"
            ])

            for item in dataset:
                entities_str = "|".join(item.get("entities", []))
                properties_str = "|".join(item.get("properties", []))
                
                writer.writerow([
                    item["id"],
                    item["sparql"],
                    item["pattern_type"],
                    item["complexity"],
                    item.get("category", ""),
                    entities_str,
                    properties_str
                ])

        print(f"Dataset exported to {output_path}")


def main():
    """Main function to generate enhanced pattern-based dataset"""
    endpoint_url = "http://localhost:3030/modified-lex2kg/query"

    # Define custom prefixes for the legal knowledge graph
    custom_prefixes = {
        "lex2kg-o": "https://example.org/lex2kg/ontology/",
        "rdfs": "https://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }

    # Initialize generator with custom prefixes
    print("Initializing enhanced pattern-based SPARQL generator...")
    generator = PatternBasedSPARQLGenerator(
        endpoint_url, 
        custom_prefixes
    )

    # Generate dataset with enhanced fields
    print("Generating enhanced pattern-based dataset...")
    dataset = generator.generate_dataset(size=250)

    # Export results
    try:
        generator.export_json(dataset, "legal.json")
        generator.export_csv(dataset, "legal.csv")
    except Exception as e:
        print(f"Error exporting results: {e}")

    # Print statistics
    complexity_counts = Counter()
    pattern_counts = Counter()

    for item in dataset:
        complexity_counts[item["complexity"]] += 1
        pattern_counts[item["pattern_type"]] += 1

    print(f"\nGenerated {len(dataset)} total queries")
    print("\nComplexity distribution:")
    for complexity, count in complexity_counts.items():
        print(f"  {complexity}: {count} ({count/len(dataset)*100:.1f}%)")

    print("\nTop 10 pattern types:")
    for pattern_type, count in pattern_counts.most_common(10):
        print(f"  {pattern_type}: {count}")

    # Show sample queries with enhanced fields
    print("\nSample generated queries with enhanced fields:")
    for complexity in ["basic", "intermediate", "advanced"]:
        samples = [item for item in dataset if item["complexity"] == complexity][:1]
        print(f"\n{complexity.capitalize()} query:")
        for sample in samples:
            print(f"  ID: {sample['id']}")
            print(f"  SPARQL: {sample['sparql']}")
            print(f"  Entities: {sample.get('entities', [])}")
            print(f"  Properties: {sample.get('properties', [])}")
            print(f"  Entity Matches: {len(sample.get('entities_matches', []))} matches")
            print(f"  Property Matches: {len(sample.get('properties_matches', []))} matches")


if __name__ == "__main__":
    main()