"""
Pattern-based SPARQL Query Generator

This generator creates SPARQL queries based on graph patterns using a discovery-first approach.
It first discovers valid property combinations through discovery queries, then selects from them.
This ensures that generated queries always have at least 1 result.

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
from rdflib import Graph, Namespace, URIRef, Literal
from collections import defaultdict, Counter

class PatternBasedSPARQLGenerator:
    def __init__(self, ttl_file_path, prefixes=None):
        """
        Initialize the pattern-based generator
        
        Args:
            ttl_file_path (str): Path to TTL file
            prefixes (dict): Namespace prefixes
        """
        self.graph = Graph()
        self.graph.parse(ttl_file_path, format='turtle')
        
        if prefixes is None:
            self.prefixes = {
                'ns1': 'https://example.org/',
                'rdfs': 'https://www.w3.org/2000/01/rdf-schema#',
                'xsd': 'https://www.w3.org/2001/XMLSchema#'
            }
        else:
            self.prefixes = prefixes
            
        # Bind namespaces
        for prefix, uri in self.prefixes.items():
            self.graph.bind(prefix, Namespace(uri))
            
        # Extract entities and properties from graph
        self.entities = self._extract_entities()
        self.properties = self._extract_properties()
        
        # Pattern weights (higher = more likely)
        self.pattern_weights = {
            1: 0.5,  # 50% chance for 1-property patterns
            2: 0.3,  # 30% chance for 2-property patterns  
            3: 0.2   # 20% chance for 3-property patterns
        }
        
        print(f"Loaded graph with {len(self.graph)} triples")
        print(f"Found {len(self.entities)} entities and {len(self.properties)} properties")
        
    def _extract_entities(self):
        """Extract all entities from the graph"""
        entities = set()
        
        # Get all subjects and objects that are URIs (excluding literals)
        for s, p, o in self.graph:
            if isinstance(s, URIRef) and str(s).startswith('https://example.org/'):
                entities.add(s)
            if isinstance(o, URIRef) and str(o).startswith('https://example.org/'):
                entities.add(o)
                
        return list(entities)
    
    def _extract_properties(self):
        """Extract meaningful properties, excluding low-quality ones"""
        properties = set()
        
        # Properties to exclude for better quality
        excluded_properties = {
            # Universal properties (same value everywhere)
            # 'https://example.org/lex2kg/ontology/jenisPeraturan',
            # 'https://example.org/lex2kg/ontology/yurisdiksi', 
            # 'https://example.org/lex2kg/ontology/disahkanDi',
            # 'https://example.org/lex2kg/ontology/bahasa',
            # 'https://example.org/lex2kg/ontology/jabatanPengesah',
            # 'https://exampxle.org/lex2kg/ontology/jenisVersi',
            
            # Technical/internal properties  
            # 'https://example.org/lex2kg/ontology/segmen',
            # 'https://example.org/lex2kg/ontology/teks',
            
            # Over-granular properties
            # 'https://example.org/lex2kg/ontology/huruf',
            # 'https://example.org/lex2kg/ontology/nomor'
        }
        
        # Skip RDF type and RDFS properties
        rdf_type = URIRef('https://www.w3.org/1999/02/22-rdf-syntax-ns#type')
        rdfs_namespace = 'https://www.w3.org/2000/01/rdf-schema#'
        
        for s, p, o in self.graph:
            if (isinstance(p, URIRef) and 
                p != rdf_type and 
                not str(p).startswith(rdfs_namespace) and
                str(p) not in excluded_properties):
                properties.add(p)
                
        return list(properties)
        
    def _shorten_uri(self, uri):
        """Convert full URI to prefixed form"""
        uri_str = str(uri)
        for prefix, namespace in self.prefixes.items():
            if uri_str.startswith(namespace):
                return f"{prefix}:{uri_str[len(namespace):]}"
        return f"<{uri_str}>"
        
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
        
    def _validate_pattern(self, sparql_query):
        """Check if pattern has results in the graph"""
        try:
            results = list(self.graph.query(sparql_query))
            return len(results) > 0
        except Exception as e:
            print(f"Error validating query: {e}")
            return False
    
    def generate_1_property_patterns(self, count=100):
        """
        Generate 1-property patterns using discovery-first approach
        
        Args:
            count (int): Number of patterns to generate
            
        Returns:
            list: List of pattern dictionaries
        """
        patterns = []
        
        # Discovery query to find all valid property-entity combinations
        discovery_query = """
            SELECT DISTINCT ?prop ?entity WHERE {
                ?s ?prop ?entity .
                FILTER(STRSTARTS(STR(?prop), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/"))
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
        """
        Generate 2-property patterns using discovery-first approach
        
        Args:
            count (int): Number of patterns to generate
            
        Returns:
            list: List of pattern dictionaries
        """
        patterns = []
        
        # Discovery query for middle target pattern: entity1 prop1 ?target . ?target prop2 entity2
        middle_discovery_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?entity1 ?entity2 ?middle WHERE {
                ?entity1 ?prop1 ?middle .
                ?middle ?prop2 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/"))
                FILTER(?prop1 != ?prop2)
            }
        """
        
        # Discovery query for branching pattern: ?target prop1 ?hidden . ?hidden prop2 entity
        branching_discovery_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?entity WHERE {
                ?target ?prop1 ?hidden .
                ?hidden ?prop2 ?entity .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/"))
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
        """
        Generate 3-property patterns using discovery-first approach
        
        Args:
            count (int): Number of patterns to generate
            
        Returns:
            list: List of pattern dictionaries
        """
        patterns = []
        
        # Discovery query for linear end pattern: entity prop1 ?h1 . ?h1 prop2 ?h2 . ?h2 prop3 ?target
        linear_end_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity WHERE {
                ?entity ?prop1 ?h1 .
                ?h1 ?prop2 ?h2 .
                ?h2 ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity), "https://example.org/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
            }
        """
        
        # Discovery query for linear middle pattern: entity1 prop1 ?h . ?h prop2 ?target . ?target prop3 entity2
        linear_middle_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {
                ?entity1 ?prop1 ?h .
                ?h ?prop2 ?target .
                ?target ?prop3 ?entity2 .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/"))
                FILTER(?prop1 != ?prop2 && ?prop2 != ?prop3 && ?prop1 != ?prop3)
            }
        """
        
        # Discovery query for star pattern: ?hidden prop1 entity1 . ?hidden prop2 entity2 . ?hidden prop3 ?target
        star_query = """
            SELECT DISTINCT ?prop1 ?prop2 ?prop3 ?entity1 ?entity2 WHERE {
                ?hidden ?prop1 ?entity1 .
                ?hidden ?prop2 ?entity2 .
                ?hidden ?prop3 ?target .
                FILTER(STRSTARTS(STR(?prop1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop2), "https://example.org/"))
                FILTER(STRSTARTS(STR(?prop3), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity1), "https://example.org/"))
                FILTER(STRSTARTS(STR(?entity2), "https://example.org/"))
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
    
    def generate_dataset(self, size=1000):
        """Generate dataset based on pattern weights using discovery-first approach"""
        dataset = []
        
        # Calculate number of queries for each complexity level
        num_1_prop = int(size * self.pattern_weights[1])
        num_2_prop = int(size * self.pattern_weights[2])
        num_3_prop = size - num_1_prop - num_2_prop
        
        print(f"Generating {num_1_prop} 1-property, {num_2_prop} 2-property, {num_3_prop} 3-property patterns...")
        
        # Generate patterns using discovery-first approach
        patterns_1 = self.generate_1_property_patterns(num_1_prop)
        patterns_2 = self.generate_2_property_patterns(num_2_prop)  
        patterns_3 = self.generate_3_property_patterns(num_3_prop)
        
        print(f"Generated {len(patterns_1)} 1-prop, {len(patterns_2)} 2-prop, {len(patterns_3)} 3-prop patterns")
        
        all_patterns = patterns_1 + patterns_2 + patterns_3
        random.shuffle(all_patterns)
        
        # Convert to final format and assign sequential IDs
        for i, pattern in enumerate(all_patterns[:size]):
            dataset.append({
                'id': f'q{i+1}',
                'sparql': pattern['sparql'],
                'pattern_type': pattern['pattern_type'],
                'complexity': pattern['complexity']
            })
            
        return dataset
        
    def export_json(self, dataset, output_path='pattern_based_dataset.json'):
        """Export dataset to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset exported to {output_path}")
        
    def export_csv(self, dataset, output_path='pattern_based_dataset.csv'):
        """Export dataset to CSV"""
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'sparql', 'pattern_type', 'complexity'])
            
            for item in dataset:
                writer.writerow([
                    item['id'],
                    item['sparql'], 
                    item['pattern_type'],
                    item['complexity']
                ])
                
        print(f"Dataset exported to {output_path}")


def main():
    """Main function to generate pattern-based dataset"""
    ttl_file = 'modified_data-lex2kg.ttl'
    
    if not os.path.exists(ttl_file):
        print(f"Error: {ttl_file} not found!")
        return
        
    # Initialize generator
    print("Initializing pattern-based SPARQL generator...")
    generator = PatternBasedSPARQLGenerator(ttl_file)
    
    # Generate dataset using discovery-first approach
    print("Generating pattern-based dataset...")
    dataset = generator.generate_dataset(size=200)
    
    # Export results
    generator.export_json(dataset)
    generator.export_csv(dataset)
    
    # Print statistics
    complexity_counts = Counter()
    pattern_counts = Counter()
    
    for item in dataset:
        complexity_counts[item['complexity']] += 1
        pattern_counts[item['pattern_type']] += 1
        
    print(f"\nGenerated {len(dataset)} total queries")
    print("\nComplexity distribution:")
    for complexity, count in complexity_counts.items():
        print(f"  {complexity}: {count} ({count/len(dataset)*100:.1f}%)")
        
    print("\nTop 10 pattern types:")
    for pattern_type, count in pattern_counts.most_common(10):
        print(f"  {pattern_type}: {count}")
        
    # Show sample queries
    print("\nSample generated queries:")
    for complexity in ['basic', 'intermediate', 'advanced']:
        samples = [item for item in dataset if item['complexity'] == complexity][:2]
        print(f"\n{complexity.capitalize()} queries:")
        for sample in samples:
            print(f"  {sample['id']}: {sample['sparql']}")

if __name__ == "__main__":
    main()