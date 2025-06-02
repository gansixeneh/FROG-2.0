import json
import random
import re
import csv
import os
from collections import defaultdict, Counter
from SPARQLWrapper import SPARQLWrapper, JSON  # Using SPARQLWrapper instead of requests
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from property_retrieval import GesisPropertyRetrieval
from kg_schema_extractor import gesis_entity_label, gesis_property_label


class SPARQLWrapperClient:
    def __init__(
        self, endpoint_url="http://localhost:3030/gesis/query", prefixes=None
    ):
        """Initialize the SPARQLWrapper client with explicit prefixes

        Args:
            endpoint_url (str): URL of the SPARQL endpoint
            prefixes (dict): Dictionary of prefix-namespace mappings
        """
        from SPARQLWrapper import SPARQLWrapper, JSON

        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)

        # Set default prefixes for GESIS knowledge graph
        if prefixes is None:
            self.prefixes = {
                "gesiskg": "<https://data.gesis.org/gesiskg/schema/>",
                "schema": "<https://schema.org/>",
                "xsd": "<http://www.w3.org/2001/XMLSchema#>",
                "rdfs": "<https://www.w3.org/2000/01/rdf-schema#>",
                "rdf": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
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
            print(f"Query: {sparql_query}")
            return None


class PatternBasedSPARQLGenerator:
    def __init__(
        self, 
        endpoint_url="http://localhost:3030/gesis/query", 
        prefixes=None,
        use_property_retrieval=True,
        entities_csv_path="data/gesis_entities.csv",
        properties_csv_path="data/gesis_properties.csv"
    ):
        """
        Initialize the pattern-based generator for GESIS Knowledge Graph

        Args:
            endpoint_url (str): SPARQL endpoint URL
            prefixes (dict): Namespace prefixes
            use_property_retrieval (bool): Whether to use property retrieval for entity/property matching
            entities_csv_path (str): Path to entities CSV file
            properties_csv_path (str): Path to properties CSV file
        """
        self.client = SPARQLWrapperClient(endpoint_url, prefixes)
        self.endpoint_url = endpoint_url

        if prefixes is None:
            self.prefixes = {
                "gesiskg": "https://data.gesis.org/gesiskg/schema/",
                "schema": "https://schema.org/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "rdfs": "https://www.w3.org/2000/01/rdf-schema#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            }
        else:
            self.prefixes = prefixes

        # Properties to exclude for better quality (adapted for GESIS/schema.org)
        self.excluded_properties = {
            # Very common properties that might not be interesting for queries
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            # "https://schema.org/url",  # URLs are usually not interesting targets
            "https://schema.org/hasPart",
            # "https://schema.org/name",
            "https://schema.org/mainEntity",
            "https://data.gesis.org/gesiskg/schema/duplicate",
            "https://data.gesis.org/gesiskg/schema/referenceMetadata",
            # Add other properties that might be too generic or technical
        }
        
        # Excluded namespaces - exclude all RDFS properties
        self.excluded_namespaces = {
            "http://www.w3.org/2000/01/rdf-schema#"
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

        # Initialize property retrieval system for entity/property matching
        self.property_retrieval = None
        if use_property_retrieval:
            try:
                print("Initializing property retrieval system for entity/property matching...")
                self.property_retrieval = GesisPropertyRetrieval(
                    endpoint_url=f"{endpoint_url}",
                    embedding_model_name="jinaai/jina-embeddings-v3",
                    is_local_client=True,
                    weaviate_host="localhost",
                    weaviate_port=8080,
                    entities_csv_path=entities_csv_path,
                    properties_csv_path=properties_csv_path
                )
                print("Property retrieval system initialized successfully!")
            except Exception as e:
                print(f"Warning: Could not initialize property retrieval system: {e}")
                print("Continuing without entity/property matching...")

        # Get total triple count
        total_triples = self._get_total_triples()
        print(f"Connected to GESIS SPARQL endpoint with {total_triples} triples")
        print(
            f"Found {len(self.entities)} entities and {len(self.properties)} properties"
        )

    def _get_property_exclusion_filters(self, prop_vars=None):
        """Generate SPARQL FILTER clauses to exclude low-quality properties
        
        Args:
            prop_vars (list): List of property variable names to include in filters (without '?')
                             Example: ['prop'] or ['prop1', 'prop2', 'prop3']
        
        Returns:
            str: SPARQL FILTER expression
        """
        filters = []
        
        # Default to just 'prop' if no variables specified
        if prop_vars is None:
            prop_vars = ['prop']
        
        # Add specific property exclusions
        for prop_var in prop_vars:
            for excluded_prop in self.excluded_properties:
                filters.append(f"?{prop_var} != <{excluded_prop}>")
        
        # Add namespace exclusions
        for prop_var in prop_vars:
            for namespace in self.excluded_namespaces:
                filters.append(f"!STRSTARTS(STR(?{prop_var}), \"{namespace}\")")
            
        return " && ".join(set(filters))  # Remove duplicates with set()

    def _get_total_triples(self):
        """Get total number of triples in the dataset"""
        query = "SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }"
        result = self.client.query(query)
        if result and result["results"]["bindings"]:
            return int(result["results"]["bindings"][0]["count"]["value"])
        return 0

    def _extract_entities(self):
        """Extract all entities from the GESIS endpoint"""
        query = """
        SELECT DISTINCT ?entity WHERE {
            {
                ?entity ?p ?o .
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
            }
            UNION
            {
                ?s ?p ?entity .
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
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
        """Extract meaningful properties from schema.org and GESIS vocabularies, excluding RDFS properties"""
        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.append(f"?property != <{prop}>")
            
        # Add namespace exclusions
        for namespace in self.excluded_namespaces:
            exclusion_filters.append(f"!STRSTARTS(STR(?property), \"{namespace}\")")

        exclusion_filter_str = " && ".join(exclusion_filters) if exclusion_filters else "true"

        query = f"""
        SELECT DISTINCT ?property WHERE {{
            ?s ?property ?o .
            FILTER(
                STRSTARTS(STR(?property), "https://schema.org/") ||
                STRSTARTS(STR(?property), "https://data.gesis.org/gesiskg/schema/")
            )
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
        """Convert full URI to prefixed form"""
        uri_str = str(uri)

        # Check for schema.org properties
        if uri_str.startswith("https://schema.org/"):
            return f"schema:{uri_str[len('https://schema.org/'):]}"
        
        # Check for GESIS schema properties
        if uri_str.startswith("https://data.gesis.org/gesiskg/schema/"):
            return f"gesiskg:{uri_str[len('https://data.gesis.org/gesiskg/schema/'):]}"

        # For other prefixes
        for prefix, namespace in self.prefixes.items():
            if prefix not in ["schema", "gesiskg"] and uri_str.startswith(namespace):
                return f"{prefix}:{uri_str[len(namespace):]}"

        # For entities (keep as full URI in angle brackets)
        return f"<{uri_str}>"

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

    def generate_1_property_patterns(self, count=100):
        """
        Generate 1-property patterns using discovery-first approach for GESIS KG

        Args:
            count (int): Number of patterns to generate

        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Get property exclusion filters for the 'prop' variable
        exclusion_filter_str = self._get_property_exclusion_filters(prop_vars=['prop'])

        # Discovery query to find all valid property-entity combinations for GESIS
        discovery_query = f"""
            SELECT DISTINCT ?prop ?entity WHERE {{
                ?s ?prop ?entity .
                FILTER(
                    STRSTARTS(STR(?prop), "https://schema.org/") ||
                    STRSTARTS(STR(?prop), "https://data.gesis.org/gesiskg/schema/")
                )
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
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
        Generate 2-property patterns using discovery-first approach for GESIS KG
        Modified to ensure literals are always set as the target
        
        Args:
            count (int): Number of patterns to generate
            
        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Get property exclusion filters specific to the variables used in these queries
        exclusion_filter_str = self._get_property_exclusion_filters(prop_vars=['prop1', 'prop2'])

        # Discovery query for branching pattern with literals
        # We get subject-property paths that lead to literals
        literal_discovery_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?subject WHERE {{
                ?subject ?prop1 ?hidden .
                ?hidden ?prop2 ?literal .
                FILTER(?prop1 != ?prop2)
                FILTER({exclusion_filter_str})
                FILTER(ISLITERAL(?literal))
            }}
            LIMIT 500
        """
        
        # Discovery query for regular URI-based patterns
        uri_discovery_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?entity WHERE {{
                ?s ?prop1 ?hidden .
                ?hidden ?prop2 ?entity .
                FILTER(?prop1 != ?prop2)
                FILTER({exclusion_filter_str})
                FILTER(ISURI(?entity))
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
            }}
            LIMIT 500
        """

        print("Executing discovery queries for 2-property patterns...")

        try:
            all_combinations = []
            
            # Get literal patterns first
            literal_result = self.client.query(literal_discovery_query)
            if literal_result and literal_result["results"]["bindings"]:
                for binding in literal_result["results"]["bindings"]:
                    all_combinations.append({
                        "type": "literal_target",
                        "data": (
                            binding["prop1"]["value"],
                            binding["prop2"]["value"],
                            binding["subject"]["value"]
                        )
                    })
            
            print(f"Found {len(all_combinations)} literal target combinations")
            
            # Get URI patterns if we need more
            if len(all_combinations) < count:
                uri_result = self.client.query(uri_discovery_query)
                if uri_result and uri_result["results"]["bindings"]:
                    for binding in uri_result["results"]["bindings"]:
                        all_combinations.append({
                            "type": "uri_entity",
                            "data": (
                                binding["prop1"]["value"],
                                binding["prop2"]["value"],
                                binding["entity"]["value"]
                            )
                        })
                
                print(f"Found {len(all_combinations) - len(all_combinations)} URI entity combinations")

            if not all_combinations:
                return patterns

            # Generate patterns
            attempts = 0
            max_attempts = count * 3

            while len(patterns) < count and attempts < max_attempts:
                attempts += 1

                combination = random.choice(all_combinations)
                
                if combination["type"] == "literal_target":
                    pattern = self._create_literal_target_pattern(combination["data"], len(patterns))
                else:
                    pattern = self._create_uri_entity_pattern(combination["data"], len(patterns))

                if pattern:
                    patterns.append(pattern)

        except Exception as e:
            print(f"Error in 2-property pattern discovery: {e}")

        return patterns
    
    def _create_literal_target_pattern(self, data, pattern_index):
        """Create pattern where a literal is the target variable"""
        prop1, prop2, subject = data

        prop1_str = self._shorten_uri(prop1)
        prop2_str = self._shorten_uri(prop2)
        subject_str = self._shorten_uri(subject)

        # For literal targets, we structure the query without the ISLITERAL filter:
        # fixed_entity prop1 ?hidden . ?hidden prop2 ?target
        sparql = f"""
            SELECT ?target WHERE {{
                {subject_str} {prop1_str} ?hidden .
                ?hidden {prop2_str} ?target .
            }}
        """

        if self._validate_pattern(sparql):
            return {
                "id": f"2p_literal_target_{pattern_index}",
                "sparql": self._format_sparql(sparql),
                "pattern_type": "2_prop_literal_target",
                "complexity": "intermediate",
                "properties": [prop1_str, prop2_str],
                "fixed_entity": subject_str,
            }
        return None

    def _create_uri_entity_pattern(self, data, pattern_index):
        """Create pattern with URI entity (renamed from _create_branching_pattern)"""
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
        Generate 3-property patterns using discovery-first approach for GESIS KG

        Args:
            count (int): Number of patterns to generate

        Returns:
            list: List of pattern dictionaries
        """
        patterns = []

        # Get property exclusion filters specific to 3-property patterns
        exclusion_filter_str = self._get_property_exclusion_filters(prop_vars=['prop1', 'prop2', 'prop3'])

        # Simplified property filter for readability
        prop_filter = """
            (STRSTARTS(STR(?prop1), "https://schema.org/") || STRSTARTS(STR(?prop1), "https://data.gesis.org/gesiskg/schema/")) &&
            (STRSTARTS(STR(?prop2), "https://schema.org/") || STRSTARTS(STR(?prop2), "https://data.gesis.org/gesiskg/schema/")) &&
            (STRSTARTS(STR(?prop3), "https://schema.org/") || STRSTARTS(STR(?prop3), "https://data.gesis.org/gesiskg/schema/"))
        """
        
        # Additional RDFS namespace exclusion for all three properties
        rdfs_exclusion = " && ".join(f"!STRSTARTS(STR(?prop{i}), \"{ns}\")" 
                                    for i in range(1, 4) 
                                    for ns in self.excluded_namespaces)

        # Discovery query for linear end pattern: entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target
        linear_end_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity WHERE {{
                ?entity ?prop1 ?h1 .
                ?h1 ?prop2 ?h2 .
                ?h2 ?prop3 ?target .
                FILTER({prop_filter})
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER({exclusion_filter_str})
                FILTER({rdfs_exclusion})
            }}
            LIMIT 200
        """

        # Discovery query for linear middle pattern: entity1 prop1 ?h . ?h prop2 ?target . ?target prop3 entity2
        linear_middle_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {{
                ?entity1 ?prop1 ?h .
                ?h ?prop2 ?target .
                ?target ?prop3 ?entity2 .
                FILTER({prop_filter})
                FILTER(
                    STRSTARTS(STR(?entity1), "https://data.gesis.org/gesiskg/resource/") &&
                    STRSTARTS(STR(?entity2), "https://data.gesis.org/gesiskg/resource/")
                )
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER({exclusion_filter_str})
                FILTER({rdfs_exclusion})
            }}
            LIMIT 200
        """

        # Discovery query for star pattern: ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target
        star_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {{
                ?hidden ?prop1 ?entity1 .
                ?hidden ?prop2 ?entity2 .
                ?hidden ?prop3 ?target .
                FILTER({prop_filter})
                FILTER(
                    STRSTARTS(STR(?entity1), "https://data.gesis.org/gesiskg/resource/") &&
                    STRSTARTS(STR(?entity2), "https://data.gesis.org/gesiskg/resource/")
                )
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER(?entity1 != ?entity2)
                FILTER({exclusion_filter_str})
                FILTER({rdfs_exclusion})
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
        
        # Extract prefixed names (schema:something, gesiskg:something)
        schema_pattern = r'schema:([a-zA-Z_][a-zA-Z0-9_]*)'
        gesiskg_pattern = r'gesiskg:([a-zA-Z_][a-zA-Z0-9_]*)'
        
        schema_names = re.findall(schema_pattern, sparql)
        gesiskg_names = re.findall(gesiskg_pattern, sparql)
        
        # Convert prefixed names to full URIs
        schema_prefix = self.prefixes.get('schema', 'https://schema.org/')
        gesiskg_prefix = self.prefixes.get('gesiskg', 'https://data.gesis.org/gesiskg/schema/')
        
        for name in schema_names:
            full_uri = f"{schema_prefix}{name}"
            uris.append(full_uri)
            
        for name in gesiskg_names:
            full_uri = f"{gesiskg_prefix}{name}"
            uris.append(full_uri)
        
        # Classify URIs as entities or properties
        for uri in uris:
            if self._is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)
        
        return entity_uris, property_uris

    def _is_property_uri(self, uri):
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
        
        # Check if it's from GESIS schema (properties)
        if "data.gesis.org/gesiskg/schema/" in uri:
            return True
                
        return False
    
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
            result = self.client.query(query)
            
            if result and result["results"]["bindings"] and len(result["results"]["bindings"]) > 0:
                return result["results"]["bindings"][0].get("name", {}).get("value")
            
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
            result = self.client.query(query)
            
            if result and result["results"]["bindings"] and len(result["results"]["bindings"]) > 0:
                return result["results"]["bindings"][0].get("name", {}).get("value")
            
            return None
        except Exception:
            return None

    def get_entities_and_properties(self, sparql):
        """
        Extract entities and properties from SPARQL query and get their labels
        Similar to nl2sparql_generator.py implementation
        
        Args:
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
        
        # Set default empty matches if property_retrieval is not available
        entity_matches = []
        property_matches = []
        
        # Use property_retrieval if available to get matches
        if self.property_retrieval:
            try:
                # Create a combined list of entities and properties as search candidates
                property_candidates = entities_list + properties_list
                
                # Get related candidates using property_retrieval
                related_candidates = self.property_retrieval.get_related_candidates(
                    " ".join(entities_list + properties_list),  # Use entities and properties as search terms
                    property_candidates=property_candidates,
                )
                
                # Format entity matches
                if "entities" in related_candidates:
                    for entity in related_candidates["entities"]:
                        # Use full URI for entities_matches
                        if entity.startswith('http'):
                            # Already a full URI
                            full_uri = entity
                        else:
                            # Expand prefixed URI to full URI
                            full_uri = self._expand_uri(entity)
                        
                        label = self._get_entity_name_from_kg(uri)
                        if not label:
                            # Fallback to gesis_entity_label function
                            label = gesis_entity_label(uri)
                            
                        entity_matches.append({
                            "id": full_uri,
                            "label": self._get_entity_name_from_kg(full_uri),
                        })

                # Format property matches  
                if "properties" in related_candidates:
                    for property in related_candidates["properties"]:
                        property_matches.append({
                            "id": property,  # Keep prefixed form for properties
                            "label": gesis_property_label(self._expand_uri(property)),
                        })
            except Exception as e:
                print(f"Error getting entity/property matches: {e}")
        
        return entities_list, properties_list, entity_matches, property_matches
    
    def _expand_uri(self, shortened_uri):
        """
        Expand a shortened URI back to its full form
        
        Args:
            shortened_uri (str): Shortened URI with prefix (e.g., schema:Publication)
            
        Returns:
            str: Full URI (e.g., https://schema.org/Publication)
        """
        # If it's already a full URI, return as is
        if shortened_uri.startswith('http'):
            return shortened_uri
            
        # Check if the URI has a prefix
        if ":" in shortened_uri:
            prefix, path = shortened_uri.split(":", 1)
            
            # Extended prefix mappings for GESIS knowledge graph
            extended_prefixes = {
                **self.prefixes,
                'gesis': 'https://data.gesis.org/gesiskg/',
                'gesiskg': 'https://data.gesis.org/gesiskg/schema/',
                'disco': 'https://rdf-vocabulary.ddialliance.org/discovery.html#',
                'nfdicore': 'https://nfdi.fiz-karlsruhe.de/ontology/',
                'skos': 'http://www.w3.org/2004/02/skos/core#',
                'void': 'http://rdfs.org/ns/void#'
            }
            
            # If the prefix is in our known prefixes, expand it
            if prefix in extended_prefixes:
                return f"{extended_prefixes[prefix]}{path}"
        
        # Return as is if it doesn't have a recognized prefix
        return shortened_uri

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
                sparql = pattern["sparql"]
                
                # Extract entities and properties from SPARQL query
                entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(sparql)
                
                dataset_item = {
                    "id": f"q{i+1}",
                    "sparql": sparql,
                    "pattern_type": pattern["pattern_type"],
                    "complexity": pattern["complexity"],
                    "entities": entities_list,
                    "properties": properties_list,
                    "entities_matches": entity_matches,
                    "properties_matches": property_matches
                }
                
                dataset.append(dataset_item)
                
                # Print progress
                if (i+1) % 10 == 0:
                    print(f"Processed {i+1}/{min(size, len(all_patterns))} patterns")
                
        except Exception as e:
            print(f"Error in dataset generation: {e}")

        # Clean up property retrieval system if initialized
        if self.property_retrieval:
            try:
                self.property_retrieval.close()
                print("Property retrieval system closed.")
            except Exception as e:
                print(f"Warning: Error closing property retrieval system: {e}")

        return dataset

    def export_json(self, dataset, output_path="gesis_rw.json"):
        """Export dataset to JSON"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset exported to {output_path}")

    def export_csv(self, dataset, output_path="gesis_rw.csv"):
        """Export dataset to CSV with additional entity and property information"""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "sparql", "pattern_type", "complexity", 
                "entities", "properties", "entities_matches", "properties_matches"
            ])

            for item in dataset:
                writer.writerow([
                    item["id"],
                    item["sparql"],
                    item["pattern_type"],
                    item["complexity"],
                    "|".join(item.get("entities", [])),
                    "|".join(item.get("properties", [])),
                    json.dumps(item.get("entities_matches", [])),
                    json.dumps(item.get("properties_matches", []))
                ])

        print(f"Dataset exported to {output_path}")


def main():
    """Main function to generate pattern-based dataset using SPARQLWrapper with GESIS Knowledge Graph"""
    endpoint_url = "http://localhost:3030/gesis/query"

    # Define custom prefixes for the GESIS knowledge graph
    custom_prefixes = {
        "gesiskg": "https://data.gesis.org/gesiskg/schema/",
        "schema": "https://schema.org/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rdfs": "https://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }

    # Define paths to CSV files
    base_dir = ".."
    entities_csv_path = os.path.join(base_dir, "data/gesis_entities.csv")
    properties_csv_path = os.path.join(base_dir, "data/gesis_properties.csv")

    # Initialize generator with custom prefixes and property retrieval
    print("Initializing pattern-based SPARQL generator for GESIS Knowledge Graph...")
    generator = PatternBasedSPARQLGenerator(
        endpoint_url=endpoint_url, 
        prefixes=custom_prefixes,
        use_property_retrieval=True,
        entities_csv_path=entities_csv_path,
        properties_csv_path=properties_csv_path
    )

    # Generate dataset using discovery-first approach
    print("Generating pattern-based dataset...")
    dataset = generator.generate_dataset(size=180)

    # Export results
    try:
        generator.export_json(dataset, os.path.join(base_dir, "rw/gesis_rw.json"))
        generator.export_csv(dataset, os.path.join(base_dir, "rw/gesis_rw.csv"))
    except Exception as e:
        print(f"Error exporting results: {e}")

    # Print statistics
    complexity_counts = Counter()
    pattern_counts = Counter()
    entity_counts = Counter()
    property_counts = Counter()

    for item in dataset:
        complexity_counts[item["complexity"]] += 1
        pattern_counts[item["pattern_type"]] += 1
        entity_counts[len(item.get("entities", []))] += 1
        property_counts[len(item.get("properties", []))] += 1

    print(f"\nGenerated {len(dataset)} total queries")
    print("\nComplexity distribution:")
    for complexity, count in complexity_counts.items():
        print(f"  {complexity}: {count} ({count/len(dataset)*100:.1f}%)")

    print("\nTop 10 pattern types:")
    for pattern_type, count in pattern_counts.most_common(10):
        print(f"  {pattern_type}: {count}")
        
    print("\nEntity count distribution:")
    for count, freq in sorted(entity_counts.items()):
        print(f"  {count} entities: {freq} patterns")
        
    print("\nProperty count distribution:")
    for count, freq in sorted(property_counts.items()):
        print(f"  {count} properties: {freq} patterns")

    # Show sample queries with entity and property information
    print("\nSample generated queries with entity and property information:")
    for complexity in ["basic", "intermediate", "advanced"]:
        samples = [item for item in dataset if item["complexity"] == complexity][:1]
        print(f"\n{complexity.capitalize()} query example:")
        for sample in samples:
            print(f"  {sample['id']}: {sample['sparql']}")
            print(f"  Entities: {sample.get('entities', [])}")
            print(f"  Properties: {sample.get('properties', [])}")
            print(f"  Entity matches: {len(sample.get('entities_matches', []))}")
            print(f"  Property matches: {len(sample.get('properties_matches', []))}")


if __name__ == "__main__":
    main()
