"""
Enhanced Pattern-based SPARQL Query Generator

This generator creates SPARQL queries based on graph patterns using a discovery-first approach
and generates the same output format as the template-based approach, including natural language
questions, entity/property extraction, and Weaviate-based matching.
"""

import json
import random
import re
import csv
import os
from rdflib import Graph, Namespace, URIRef, Literal
from collections import defaultdict, Counter
from property_retrieval import UniversityPropertyRetrieval
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

class EnhancedPatternBasedSPARQLGenerator:
    def __init__(self, ttl_file_path, prefixes=None):
        """
        Initialize the enhanced pattern-based generator
        
        Args:
            ttl_file_path (str): Path to TTL file
            prefixes (dict): Namespace prefixes
        """
        self.graph = Graph()
        self.graph.parse(ttl_file_path, format='turtle')
        
        if prefixes is None:
            self.prefixes = {
                'ns1': 'http://example.org/',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#'
            }
        else:
            self.prefixes = prefixes
            
        # Bind namespaces
        for prefix, uri in self.prefixes.items():
            self.graph.bind(prefix, Namespace(uri))
            
        # Initialize property retrieval system
        self.property_retrieval = UniversityPropertyRetrieval(
            turtle_file_path=ttl_file_path,
            embedding_model_name="jinaai/jina-embeddings-v3",
            is_local_client=True,
            weaviate_host="localhost",
            weaviate_port=8080,
        )
        
        # Initialize stopwords for n-gram generation
        self.stopwords = set(stopwords.words('english'))
        
        # Extract entities and properties from graph
        self.entities = self._extract_entities()
        self.properties = self._extract_properties()
        
        # Pattern weights (higher = more likely)
        self.pattern_weights = {
            1: 0.5,  # 50% chance for 1-property patterns
            2: 0.3,  # 30% chance for 2-property patterns  
            3: 0.2   # 20% chance for 3-property patterns
        }
        
        # Question templates for different patterns
        self.question_templates = self._initialize_question_templates()
        
        print(f"Loaded graph with {len(self.graph)} triples")
        print(f"Found {len(self.entities)} entities and {len(self.properties)} properties")
        
    def _extract_entities(self):
        """Extract all entities from the graph"""
        entities = set()
        
        # Get all subjects and objects that are URIs (excluding literals)
        for s, p, o in self.graph:
            if isinstance(s, URIRef) and str(s).startswith('http://example.org/'):
                entities.add(s)
            if isinstance(o, URIRef) and str(o).startswith('http://example.org/'):
                entities.add(o)
                
        return list(entities)
    
    def _extract_properties(self):
        """Extract all properties from the graph"""
        properties = set()
        
        # Skip RDF type and all RDFS properties
        rdf_type = URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')
        rdfs_namespace = 'http://www.w3.org/2000/01/rdf-schema#'
        
        for s, p, o in self.graph:
            if isinstance(p, URIRef) and p != rdf_type and not str(p).startswith(rdfs_namespace):
                properties.add(p)
                
        return list(properties)
    
    def _initialize_question_templates(self):
        """Initialize question templates for different pattern types"""
        return {
            '1_prop_subject_target': [
                "What {property_label} {entity_label}?",
                "Which items have {property_label} of {entity_label}?",
                "What is related to {entity_label} through {property_label}?",
                "Find all subjects that {property_label} {entity_label}.",
            ],
            '1_prop_object_target': [
                "What is the {property_label} of {entity_label}?",
                "What {property_label} does {entity_label} have?",
                "Which {property_label} is associated with {entity_label}?",
                "Find the {property_label} for {entity_label}.",
            ],
            '2_prop_middle_target': [
                "What connects {entity1_label} and {entity2_label} through {property1_label} and {property2_label}?",
                "Find the intermediate entity between {entity1_label} and {entity2_label} via {property1_label} and {property2_label}.",
                "What is the middle point linking {entity1_label} to {entity2_label}?",
                "Which entity bridges {entity1_label} and {entity2_label}?",
            ],
            '2_prop_branching': [
                "What is connected to {entity_label} through a two-step relationship involving {property1_label} and {property2_label}?",
                "Find entities that are indirectly related to {entity_label} via {property1_label} and {property2_label}.",
                "What can be reached from {entity_label} through {property1_label} then {property2_label}?",
                "Which items are two hops away from {entity_label}?",
            ],
            '3_prop_linear_end': [
                "What is at the end of a three-step path starting from {entity_label} through {property1_label}, {property2_label}, and {property3_label}?",
                "Find the final destination when following {property1_label}, {property2_label}, and {property3_label} from {entity_label}.",
                "What is three relationships away from {entity_label}?",
                "Which entity is reached through a three-hop path from {entity_label}?",
            ],
            '3_prop_linear_middle': [
                "What connects {entity1_label} and {entity2_label} through a three-step path involving {property1_label}, {property2_label}, and {property3_label}?",
                "Find the middle entity in a three-hop relationship between {entity1_label} and {entity2_label}.",
                "What is the central point linking {entity1_label} to {entity2_label} through three relationships?",
                "Which entity serves as an intermediate in the complex relationship between {entity1_label} and {entity2_label}?",
            ],
            '3_prop_star': [
                "What is the central hub connected to both {entity1_label} and {entity2_label} through {property1_label}, {property2_label}, and {property3_label}?",
                "Find the common entity that links to {entity1_label} and {entity2_label} through multiple relationships.",
                "What entity serves as a connection point for {entity1_label} and {entity2_label}?",
                "Which item is at the center of relationships with {entity1_label} and {entity2_label}?",
            ],
        }
        
    def _shorten_uri(self, uri):
        """Convert full URI to prefixed form"""
        uri_str = str(uri)
        for prefix, namespace in self.prefixes.items():
            if uri_str.startswith(namespace):
                return f"{prefix}:{uri_str[len(namespace):]}"
        return f"<{uri_str}>"
        
    def _get_label_from_graph(self, uri):
        """Get rdfs:label for a URI from the RDF graph"""
        try:
            # Query for rdfs:label
            query = f"""
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?label WHERE {{
                    <{uri}> rdfs:label ?label .
                }}
                LIMIT 1
            """
            results = list(self.graph.query(query))
            if results and results[0][0]:
                return str(results[0][0])
        except Exception as e:
            print(f"Error getting label for {uri}: {e}")
        
        return self._extract_label_from_uri(str(uri))
    
    def _extract_label_from_uri(self, uri):
        """Extract a human-readable label from a URI"""
        # Extract the last part of the URI
        last_part = uri.split('/')[-1].split('#')[-1]
        
        # University course specific handling
        if '_' in last_part:
            # Replace underscores with spaces
            with_spaces = last_part.replace('_', ' ')
            # Capitalize each word
            return ' '.join(word.capitalize() for word in with_spaces.split())
        else:
            # Convert camelCase to spaces
            return re.sub(r'([a-z])([A-Z])', r'\1 \2', last_part)
    
    def _extract_uris_from_sparql(self, sparql):
        """Extract entity and property URIs from SPARQL query"""
        entity_uris = []
        property_uris = []
        
        # Extract URIs in angle brackets
        uri_pattern = r'<([^>]+)>'
        uris = re.findall(uri_pattern, sparql)
        
        # Extract prefixed names (ns1:something)
        prefixed_pattern = r'ns1:([a-zA-Z_][a-zA-Z0-9_]*)'
        prefixed_names = re.findall(prefixed_pattern, sparql)
        
        # Convert prefixed names to full URIs
        ns1_prefix = self.prefixes.get('ns1', 'http://example.org/')
        for name in prefixed_names:
            full_uri = f"{ns1_prefix}{name}"
            uris.append(full_uri)
        
        # Classify URIs as entities or properties
        for uri in uris:
            if self._is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)
        
        return entity_uris, property_uris
    
    def _is_property_uri(self, uri):
        """Check if a URI is a property URI"""
        # Common property indicators
        property_indicators = ['has_', 'is_', 'also_known_as']
        
        for indicator in property_indicators:
            if indicator in uri:
                return True
                
        return False
    
    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """Preprocess question into tokens using NLTK RegexpTokenizer"""
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
        """Generate n-grams from tokens using NLTK"""
        result = []
        
        # Generate unigrams, bigrams, and trigrams using NLTK
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        
        return result
    
    def get_entities_and_properties(self, question, sparql):
        """Extract entities and properties from SPARQL query and get their labels"""
        # Extract actual URIs from SPARQL query
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Get labels for entities and properties
        entities_list = []
        properties_list = []
        
        # Get entity labels using rdfs:label
        for uri in entity_uris:
            label = self._get_label_from_graph(uri)
            if label:
                entities_list.append(label)
        
        # Get property labels using rdfs:label  
        for uri in property_uris:
            label = self._get_label_from_graph(uri)
            if label:
                properties_list.append(label)
        
        # Get entity and property candidates for entities_matches and properties_matches
        property_candidates = entities_list + properties_list
        related_candidates = self.get_related_candidates(
            question, 
            property_candidates=property_candidates,
            threshold=0.6,
            k=5
        )
        
        # Format entity matches
        entity_matches = []
        if "entities" in related_candidates:
            for entity in related_candidates["entities"]:
                entity_matches.append({
                    "id": entity['short'],
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

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity and property candidates using n-grams"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type, threshold=threshold):
            """Search for entities or properties and format results"""
            # Search using the appropriate method
            if search_type == "entities":
                df_res = self.property_retrieval.search_entities(ngram, k=k)
            else:
                df_res = self.property_retrieval.search_properties(ngram, k=k)
            
            # Filter by threshold and format results
            filtered_results = []
            for _, row in df_res.iterrows():
                if row.get('score', 0) >= threshold:
                    filtered_results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
            
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
    
    def generate_question_for_pattern(self, pattern_data):
        """Generate natural language question for a pattern"""
        pattern_type = pattern_data['pattern_type']
        
        # Extract base pattern type without variation number
        base_pattern_type = re.sub(r'_v\d+$', '', pattern_type)
        
        if base_pattern_type not in self.question_templates:
            return f"What is the result of this query pattern?"
        
        templates = self.question_templates[base_pattern_type]
        template = random.choice(templates)
        
        # Get entity and property labels for template substitution
        question = template
        
        if 'fixed_entity' in pattern_data:
            entity_uri = self._expand_prefixed_uri(pattern_data['fixed_entity'])
            entity_label = self._get_label_from_graph(entity_uri)
            question = question.replace('{entity_label}', entity_label)
        
        if 'fixed_entities' in pattern_data:
            entities = pattern_data['fixed_entities']
            for i, entity in enumerate(entities):
                entity_uri = self._expand_prefixed_uri(entity)
                entity_label = self._get_label_from_graph(entity_uri)
                question = question.replace(f'{{entity{i+1}_label}}', entity_label)
        
        if 'properties' in pattern_data:
            properties = pattern_data['properties']
            for i, prop in enumerate(properties):
                prop_uri = self._expand_prefixed_uri(prop)
                prop_label = self._get_label_from_graph(prop_uri)
                question = question.replace(f'{{property{i+1}_label}}', prop_label)
        
        if 'property' in pattern_data:
            prop_uri = self._expand_prefixed_uri(pattern_data['property'])
            prop_label = self._get_label_from_graph(prop_uri)
            question = question.replace('{property_label}', prop_label)
        
        return question
    
    def _expand_prefixed_uri(self, prefixed_uri):
        """Expand prefixed URI to full URI"""
        if ':' in prefixed_uri:
            prefix, local_name = prefixed_uri.split(':', 1)
            if prefix in self.prefixes:
                return f"{self.prefixes[prefix]}{local_name}"
        return prefixed_uri
    
    def generate_chain_of_thoughts(self, question, sparql, pattern_data):
        """Generate chain of thoughts for the question-query pair"""
        complexity = pattern_data.get('complexity', 'basic')
        pattern_type = pattern_data.get('pattern_type', 'unknown')
        
        thoughts = [
            f"1. The question asks for information using a {complexity} {pattern_type} pattern.",
            "2. This requires analyzing the relationships in the university course knowledge graph.",
            "3. The query involves entities and properties defined in the university domain ontology.",
        ]
        
        if complexity == 'basic':
            thoughts.extend([
                "4. This is a simple one-hop relationship query.",
                "5. The SPARQL query directly retrieves the requested information through a single property."
            ])
        elif complexity == 'intermediate':
            thoughts.extend([
                "4. This involves a two-hop relationship requiring an intermediate connection.",
                "5. The SPARQL query uses multiple triple patterns to navigate the relationships.",
                "6. The result provides information through connected entities in the graph."
            ])
        else:  # advanced
            thoughts.extend([
                "4. This is a complex multi-hop query requiring navigation through multiple relationships.",
                "5. The SPARQL query uses several triple patterns with hidden variables to connect entities.",
                "6. This type of query demonstrates the interconnected nature of the knowledge graph.",
                "7. The result reveals deep relationships within the university course domain."
            ])
            
        return thoughts
    
    def _format_sparql(self, sparql):
        """Format SPARQL query for readability"""
        # Clean up spacing
        sparql = re.sub(r'\s+', ' ', sparql.strip())
        
        # Format SELECT and WHERE
        sparql = re.sub(r'SELECT\s+', 'SELECT ', sparql)
        sparql = re.sub(r'\s+WHERE\s+', ' WHERE ', sparql)
        
        # Format braces
        sparql = re.sub(r'\s*{\s*', ' { ', sparql)
        sparql = re.sub(r'\s*}\s*', ' }', sparql)
        
        return sparql
    
    def generate_1_property_patterns(self, count=100):
        """Generate 1-property patterns using discovery-first approach"""
        patterns = []
        
        # Discovery query to find all valid property-entity combinations
        discovery_query = """
            SELECT DISTINCT ?prop ?entity WHERE {
                ?s ?prop ?entity .
                FILTER(STRSTARTS(STR(?prop), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "http://example.org/"))
            }
        """
        
        print("Executing discovery query for 1-property patterns...")
        try:
            results = list(self.graph.query(discovery_query))
            print(f"Found {len(results)} valid property-entity combinations")
            
            if not results:
                return patterns
                
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
                pattern_type = random.choice(['subject_target', 'object_target'])
                
                if pattern_type == 'subject_target':
                    # Pattern: ?target prop fixed_entity
                    sparql = f"SELECT ?target WHERE {{ ?target {prop_str} {entity_str} . }}"
                    pattern_id = f'1p_subj_{len(patterns)}'
                    pattern_type_name = '1_prop_subject_target'
                else:
                    # Pattern: fixed_entity prop ?target  
                    # Need to find a valid subject for this property
                    subject_query = f"""
                        SELECT DISTINCT ?subj WHERE {{
                            ?subj <{str(prop)}> <{str(entity)}> .
                        }}
                    """
                    subject_results = list(self.graph.query(subject_query))
                    if not subject_results:
                        continue
                        
                    subj = random.choice(subject_results)[0]
                    subj_str = self._shorten_uri(subj)
                    sparql = f"SELECT ?target WHERE {{ {subj_str} {prop_str} ?target . }}"
                    pattern_id = f'1p_obj_{len(patterns)}'
                    pattern_type_name = '1_prop_object_target'
                
                # Validate that this pattern has results
                if self._validate_pattern(sparql):
                    patterns.append({
                        'id': pattern_id,
                        'sparql': self._format_sparql(sparql),
                        'pattern_type': pattern_type_name,
                        'complexity': 'basic',
                        'property': prop_str,
                        'fixed_entity': entity_str if pattern_type == 'subject_target' else subj_str
                    })
                    
        except Exception as e:
            print(f"Error in 1-property pattern discovery: {e}")
            
        return patterns
    
    def generate_2_property_patterns(self, count=100):
        """Generate 2-property patterns using discovery-first approach"""
        patterns = []
        
        # Discovery query for middle target pattern: entity1 prop1 ?target . ?target prop2 entity2
        middle_discovery_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?entity1 ?entity2 ?middle WHERE {
                ?entity1 ?prop1 ?middle .
                ?middle ?prop2 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "http://example.org/"))
                FILTER(?prop1 != ?prop2)
            }
        """
        
        # Discovery query for branching pattern: ?target prop1 ?hidden . ?hidden prop2 entity
        branching_discovery_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?entity WHERE {
                ?target ?prop1 ?hidden .
                ?hidden ?prop2 ?entity .
                FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "http://example.org/"))
                FILTER(?prop1 != ?prop2)
            }
        """
        
        print("Executing discovery queries for 2-property patterns...")
        
        try:
            # Get middle target combinations
            middle_results = list(self.graph.query(middle_discovery_query))
            print(f"Found {len(middle_results)} valid middle-target combinations")
            
            # Get branching combinations  
            branching_results = list(self.graph.query(branching_discovery_query))
            print(f"Found {len(branching_results)} valid branching combinations")
            
            all_combinations = []
            
            # Process middle target results
            for result in middle_results:
                prop1, prop2, entity1, entity2, middle = result
                all_combinations.append({
                    'type': 'middle_target',
                    'data': (prop1, prop2, entity1, entity2, middle)
                })
            
            # Process branching results
            for result in branching_results:
                prop1, prop2, entity = result  
                all_combinations.append({
                    'type': 'branching',
                    'data': (prop1, prop2, entity)
                })
            
            if not all_combinations:
                return patterns
                
            # Generate patterns by randomly selecting from valid combinations
            attempts = 0
            max_attempts = count * 3
            
            while len(patterns) < count and attempts < max_attempts:
                attempts += 1
                
                combination = random.choice(all_combinations)
                
                if combination['type'] == 'middle_target':
                    pattern = self._create_middle_target_pattern(combination['data'], len(patterns))
                else:
                    pattern = self._create_branching_pattern(combination['data'], len(patterns))
                
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
            f"?target {prop1_str} {entity1_str} . ?target {prop2_str} {entity2_str}"   # first swapped
        ]
        
        sparql = f"SELECT ?target WHERE {{ {variations[variation]} . }}"
        
        if self._validate_pattern(sparql):
            return {
                'id': f'2p_mid_{variation}_{pattern_index}',
                'sparql': self._format_sparql(sparql),
                'pattern_type': f'2_prop_middle_target_v{variation+1}',
                'complexity': 'intermediate',
                'properties': [prop1_str, prop2_str],
                'fixed_entities': [entity1_str, entity2_str]
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
            f"?target {prop1_str} ?hidden . ?hidden {prop2_str} {entity_str}",      # original
            f"?hidden {prop1_str} ?target . {entity_str} {prop2_str} ?hidden",      # both swapped
            f"?target {prop1_str} ?hidden . {entity_str} {prop2_str} ?hidden",      # second swapped
            f"?hidden {prop1_str} ?target . ?hidden {prop2_str} {entity_str}"       # first swapped
        ]
        
        sparql = f"SELECT ?target WHERE {{ {variations[variation]} . }}"
        
        if self._validate_pattern(sparql):
            return {
                'id': f'2p_branch_{variation}_{pattern_index}',
                'sparql': self._format_sparql(sparql),
                'pattern_type': f'2_prop_branching_v{variation+1}',
                'complexity': 'intermediate',
                'properties': [prop1_str, prop2_str],
                'fixed_entity': entity_str
            }
        return None
    
    def generate_3_property_patterns(self, count=100):
        """Generate 3-property patterns using discovery-first approach"""
        patterns = []
        
        # Discovery query for linear end pattern: entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target
        linear_end_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity WHERE {
                ?entity ?prop1 ?h1 .
                ?h1 ?prop2 ?h2 .
                ?h2 ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "http://example.org/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
            }
        """
        
        # Discovery query for linear middle pattern: entity1 prop1 ?h . ?h prop2 ?target . ?target prop3 entity2
        linear_middle_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {
                ?entity1 ?prop1 ?h .
                ?h ?prop2 ?target .
                ?target ?prop3 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "http://example.org/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
            }
        """
        
        # Discovery query for star pattern: ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target
        star_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {
                ?hidden ?prop1 ?entity1 .
                ?hidden ?prop2 ?entity2 .
                ?hidden ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "http://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "http://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "http://example.org/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
                FILTER(?entity1 != ?entity2)
            }
        """
        
        print("Executing discovery queries for 3-property patterns...")
        
        try:
            # Get all types of 3-property combinations
            linear_end_results = list(self.graph.query(linear_end_query))
            linear_middle_results = list(self.graph.query(linear_middle_query))
            star_results = list(self.graph.query(star_query))
            
            print(f"Found {len(linear_end_results)} linear-end combinations")
            print(f"Found {len(linear_middle_results)} linear-middle combinations")
            print(f"Found {len(star_results)} star combinations")
            
            all_combinations = []
            
            # Process all result types
            for result in linear_end_results:
                all_combinations.append({
                    'type': 'linear_end',
                    'data': result
                })
            
            for result in linear_middle_results:
                all_combinations.append({
                    'type': 'linear_middle', 
                    'data': result
                })
                
            for result in star_results:
                all_combinations.append({
                    'type': 'star',
                    'data': result
                })
            
            if not all_combinations:
                return patterns
                
            # Generate patterns by randomly selecting from valid combinations
            attempts = 0
            max_attempts = count * 3
            
            while len(patterns) < count and attempts < max_attempts:
                attempts += 1
                
                combination = random.choice(all_combinations)
                
                if combination['type'] == 'linear_end':
                    pattern = self._create_linear_end_pattern(combination['data'], len(patterns))
                elif combination['type'] == 'linear_middle':
                    pattern = self._create_linear_middle_pattern(combination['data'], len(patterns))
                else:
                    pattern = self._create_star_pattern(combination['data'], len(patterns))
                
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
                'id': f'3p_linear_end_{variation}_{pattern_index}',
                'sparql': self._format_sparql(sparql),
                'pattern_type': f'3_prop_linear_end_v{variation+1}',
                'complexity': 'advanced',
                'properties': props_str,
                'fixed_entity': entity_str
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
                'id': f'3p_linear_mid_{variation}_{pattern_index}',
                'sparql': self._format_sparql(sparql),
                'pattern_type': f'3_prop_linear_middle_v{variation+1}',
                'complexity': 'advanced',
                'properties': props_str,
                'fixed_entities': [entity1_str, entity2_str]
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
                'id': f'3p_star_{variation}_{pattern_index}',
                'sparql': self._format_sparql(sparql),
                'pattern_type': f'3_prop_star_v{variation+1}',
                'complexity': 'advanced',
                'properties': props_str,
                'fixed_entities': [entity1_str, entity2_str]
            }
        return None
    
    def _validate_pattern(self, sparql_query):
        """Check if pattern has results in the graph"""
        try:
            results = list(self.graph.query(sparql_query))
            return len(results) > 0
        except Exception as e:
            print(f"Error validating query: {e}")
            return False
    
    def generate_dataset(self, size=1000, complexity_distribution=None):
        """Generate dataset with same format as template-based approach"""
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.5,
                "intermediate": 0.3,
                "advanced": 0.2
            }
        
        dataset = []
        id_counter = 1
        
        # Calculate number of queries for each complexity level
        num_1_prop = int(size * complexity_distribution["basic"])
        num_2_prop = int(size * complexity_distribution["intermediate"])
        num_3_prop = size - num_1_prop - num_2_prop
        
        print(f"Generating {num_1_prop} 1-property, {num_2_prop} 2-property, {num_3_prop} 3-property patterns...")
        
        # Generate patterns using discovery-first approach
        patterns_1 = self.generate_1_property_patterns(num_1_prop)
        patterns_2 = self.generate_2_property_patterns(num_2_prop)  
        patterns_3 = self.generate_3_property_patterns(num_3_prop)
        
        print(f"Generated {len(patterns_1)} 1-prop, {len(patterns_2)} 2-prop, {len(patterns_3)} 3-prop patterns")
        
        all_patterns = patterns_1 + patterns_2 + patterns_3
        random.shuffle(all_patterns)
        
        # Convert to final format with same structure as template-based approach
        for i, pattern in enumerate(all_patterns[:size]):
            # Generate natural language question
            question = self.generate_question_for_pattern(pattern)
            sparql = pattern['sparql']
            
            # Generate chain of thoughts
            thoughts = self.generate_chain_of_thoughts(question, sparql, pattern)
            
            # Extract entities and properties with Weaviate search
            entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(question, sparql)
            
            # Create dataset entry with same format as template-based approach
            entry = {
                "id": f"q{id_counter}",
                "question": question,
                "sparql": sparql,
                "category": "university",
                "complexity": pattern['complexity'],
                "templateId": pattern['pattern_type'],
                "thoughts": thoughts,
                "entities": entities_list,
                "properties": properties_list,
                "entities_matches": entity_matches,
                "properties_matches": property_matches
            }
            
            dataset.append(entry)
            id_counter += 1
            
        return dataset
        
    def export_json(self, dataset, output_path='enhanced_pattern_based_dataset.json'):
        """Export dataset to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset exported to {output_path}")
        
    def export_csv(self, dataset, output_path='enhanced_pattern_based_dataset.csv'):
        """Export dataset to CSV"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'question', 'sparql', 'category', 'complexity', 'templateId'])
            
            for item in dataset:
                writer.writerow([
                    item['id'],
                    item['question'],
                    item['sparql'], 
                    item['category'],
                    item['complexity'],
                    item['templateId']
                ])
                
        print(f"Dataset exported to {output_path}")


def main():
    """Main function to generate enhanced pattern-based dataset"""
    ttl_file = 'final_result.ttl'
    
    if not os.path.exists(ttl_file):
        print(f"Error: {ttl_file} not found!")
        return
        
    # Initialize enhanced generator
    print("Initializing enhanced pattern-based SPARQL generator...")
    generator = EnhancedPatternBasedSPARQLGenerator(ttl_file)
    
    # Generate dataset with same format as template-based approach
    print("Generating enhanced pattern-based dataset...")
    dataset = generator.generate_dataset(size=200)
    
    # Export results
    generator.export_json(dataset, 'curi_pattern_based.json')
    generator.export_csv(dataset, 'curi_pattern_based.csv')
    
    # Print statistics
    complexity_counts = Counter()
    pattern_counts = Counter()
    
    for item in dataset:
        complexity_counts[item['complexity']] += 1
        pattern_counts[item['templateId']] += 1
        
    print(f"\nGenerated {len(dataset)} total questions")
    print("\nComplexity distribution:")
    for complexity, count in complexity_counts.items():
        print(f"  {complexity}: {count} ({count/len(dataset)*100:.1f}%)")
        
    print("\nTop 10 pattern types:")
    for pattern_type, count in pattern_counts.most_common(10):
        print(f"  {pattern_type}: {count}")
        
    # Show sample questions
    print("\nSample generated questions:")
    for complexity in ['basic', 'intermediate', 'advanced']:
        samples = [item for item in dataset if item['complexity'] == complexity][:2]
        print(f"\n{complexity.capitalize()} questions:")
        for sample in samples:
            print(f"  Q: {sample['question']}")
            print(f"  SPARQL: {sample['sparql']}")
            print()

if __name__ == "__main__":
    main()