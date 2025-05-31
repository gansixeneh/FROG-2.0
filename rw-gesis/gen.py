"""
Pattern-based SPARQL Query Generator using SPARQLWrapper for GESIS Knowledge Graph

This generator creates SPARQL queries based on graph patterns using a discovery-first approach.
It first discovers valid property combinations through discovery queries, then selects from them.
This ensures that generated queries always have at least 1 result.

Modified for GESIS Knowledge Graph with schema.org vocabulary.

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
from collections import defaultdict, Counter
from SPARQLWrapper import SPARQLWrapper, JSON  # Using SPARQLWrapper instead of requests


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
        self.sparql.setTimeout(30)  # 30 second timeout

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
        self, endpoint_url="http://localhost:3030/gesis/query", prefixes=None
    ):
        """
        Initialize the pattern-based generator for GESIS Knowledge Graph

        Args:
            endpoint_url (str): SPARQL endpoint URL
            prefixes (dict): Namespace prefixes
        """
        self.client = SPARQLWrapperClient(endpoint_url, prefixes)

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
            "https://schema.org/url",  # URLs are usually not interesting targets
            "https://schema.org/hasPart",
            "https://schema.org/name",
            "https://schema.org/mainEntity",
            "https://data.gesis.org/gesiskg/schema/duplicate",
            "https://data.gesis.org/gesiskg/schema/referenceMetadata",
            # Add other properties that might be too generic or technical
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

        # Get total triple count
        total_triples = self._get_total_triples()
        print(f"Connected to GESIS SPARQL endpoint with {total_triples} triples")
        print(
            f"Found {len(self.entities)} entities and {len(self.properties)} properties"
        )

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
        """Extract meaningful properties from schema.org and GESIS vocabularies"""
        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.append(f"?property != <{prop}>")

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

        # Build exclusion filters for the query
        exclusion_filters = []
        for prop in self.excluded_properties:
            exclusion_filters.append(f"?prop != <{prop}>")

        exclusion_filter_str = " && ".join(exclusion_filters) if exclusion_filters else "true"

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

        exclusion_filter_str = " && ".join(exclusion_filters) if exclusion_filters else "true"

        # Discovery query for middle target pattern: entity1 prop1 ?target . ?target prop2 entity2
        middle_discovery_query = f"""
            SELECT DISTINCT ?prop1 ?prop2 ?entity1 ?entity2 ?middle WHERE {{
                ?entity1 ?prop1 ?middle .
                ?middle ?prop2 ?entity2 .
                FILTER(
                    (STRSTARTS(STR(?prop1), "https://schema.org/") || STRSTARTS(STR(?prop1), "https://data.gesis.org/gesiskg/schema/")) &&
                    (STRSTARTS(STR(?prop2), "https://schema.org/") || STRSTARTS(STR(?prop2), "https://data.gesis.org/gesiskg/schema/"))
                )
                FILTER(
                    STRSTARTS(STR(?entity1), "https://data.gesis.org/gesiskg/resource/") &&
                    STRSTARTS(STR(?entity2), "https://data.gesis.org/gesiskg/resource/")
                )
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
                FILTER(
                    (STRSTARTS(STR(?prop1), "https://schema.org/") || STRSTARTS(STR(?prop1), "https://data.gesis.org/gesiskg/schema/")) &&
                    (STRSTARTS(STR(?prop2), "https://schema.org/") || STRSTARTS(STR(?prop2), "https://data.gesis.org/gesiskg/schema/"))
                )
                FILTER(STRSTARTS(STR(?entity), "https://data.gesis.org/gesiskg/resource/"))
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
        Generate 3-property patterns using discovery-first approach for GESIS KG

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

        exclusion_filter_str = " && ".join(exclusion_filters) if exclusion_filters else "true"

        # Simplified property filter for readability
        prop_filter = """
            (STRSTARTS(STR(?prop1), "https://schema.org/") || STRSTARTS(STR(?prop1), "https://data.gesis.org/gesiskg/schema/")) &&
            (STRSTARTS(STR(?prop2), "https://schema.org/") || STRSTARTS(STR(?prop2), "https://data.gesis.org/gesiskg/schema/")) &&
            (STRSTARTS(STR(?prop3), "https://schema.org/") || STRSTARTS(STR(?prop3), "https://data.gesis.org/gesiskg/schema/"))
        """

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
                dataset.append(
                    {
                        "id": f"q{i+1}",
                        "sparql": pattern["sparql"],
                        "pattern_type": pattern["pattern_type"],
                        "complexity": pattern["complexity"],
                    }
                )
        except Exception as e:
            print(f"Error in dataset generation: {e}")

        return dataset

    def export_json(self, dataset, output_path="gesis_pattern_based_dataset.json"):
        """Export dataset to JSON"""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset exported to {output_path}")

    def export_csv(self, dataset, output_path="gesis_pattern_based_dataset.csv"):
        """Export dataset to CSV"""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "sparql", "pattern_type", "complexity"])

            for item in dataset:
                writer.writerow(
                    [
                        item["id"],
                        item["sparql"],
                        item["pattern_type"],
                        item["complexity"],
                    ]
                )

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

    # Initialize generator with custom prefixes
    print("Initializing pattern-based SPARQL generator for GESIS Knowledge Graph...")
    generator = PatternBasedSPARQLGenerator(endpoint_url, custom_prefixes)

    # Generate dataset using discovery-first approach
    print("Generating pattern-based dataset...")
    dataset = generator.generate_dataset(size=200)

    # Export results
    try:
        generator.export_json(dataset)
        generator.export_csv(dataset)
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

    # Show sample queries
    print("\nSample generated queries:")
    for complexity in ["basic", "intermediate", "advanced"]:
        samples = [item for item in dataset if item["complexity"] == complexity][:2]
        print(f"\n{complexity.capitalize()} queries:")
        for sample in samples:
            print(f"  {sample['id']}: {sample['sparql']}")


if __name__ == "__main__":
    main()