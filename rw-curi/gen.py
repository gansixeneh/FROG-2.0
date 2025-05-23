"""
Pattern-based SPARQL Query Generator

This generator creates SPARQL queries based on graph patterns rather than fixed templates.
It generates queries with 1-3 properties using various connection patterns.

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
                'ns1': 'http://example.org/',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#'
            }
        else:
            self.prefixes = prefixes
            
        # Bind namespaces
        for prefix, uri in self.prefixes.items():
            self.graph.bind(prefix, Namespace(uri))
            
        # Extract entities and properties from graph
        self.entities = self._extract_entities()
        self.properties = self._extract_properties()
        
        # Create property-entity mapping for efficient pattern generation
        self.prop_to_subjects = defaultdict(set)
        self.prop_to_objects = defaultdict(set)
        self._build_property_mappings()
        
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
        
    def _build_property_mappings(self):
        """Build mappings from properties to their subjects/objects"""
        for s, p, o in self.graph:
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                self.prop_to_subjects[p].add(s)
                self.prop_to_objects[p].add(o)
                
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
        Generate 1-property patterns: ? — O and O — ?
        
        Args:
            count (int): Number of patterns to generate
            
        Returns:
            list: List of pattern dictionaries
        """
        patterns = []
        attempts = 0
        max_attempts = count * 5
        
        while len(patterns) < count and attempts < max_attempts:
            attempts += 1
            
            # Randomly select a property
            prop = random.choice(self.properties)
            prop_str = self._shorten_uri(prop)
            
            # Get available subjects and objects for this property
            subjects = list(self.prop_to_subjects[prop])
            objects = list(self.prop_to_objects[prop])
            
            if not subjects or not objects:
                continue
                
            # Pattern 1: ?target prop fixed_entity (target as subject)
            if objects and random.random() < 0.5:
                fixed_entity = random.choice(objects)
                fixed_str = self._shorten_uri(fixed_entity)
                
                sparql = f"SELECT ?target WHERE {{ ?target {prop_str} {fixed_str} . }}"
                
                if self._validate_pattern(sparql):
                    patterns.append({
                        'id': f'1p_subj_{len(patterns)}',
                        'sparql': self._format_sparql(sparql),
                        'pattern_type': '1_prop_subject_target',
                        'complexity': 'basic',
                        'property': prop_str,
                        'fixed_entity': fixed_str
                    })
                    
            # Pattern 2: fixed_entity prop ?target (target as object)
            else:
                fixed_entity = random.choice(subjects)
                fixed_str = self._shorten_uri(fixed_entity)
                
                sparql = f"SELECT ?target WHERE {{ {fixed_str} {prop_str} ?target . }}"
                
                if self._validate_pattern(sparql):
                    patterns.append({
                        'id': f'1p_obj_{len(patterns)}',
                        'sparql': self._format_sparql(sparql),
                        'pattern_type': '1_prop_object_target',
                        'complexity': 'basic',
                        'property': prop_str,
                        'fixed_entity': fixed_str
                    })
                    
        return patterns
    
    def generate_2_property_patterns(self, count=100):
        """
        Generate 2-property patterns:
        - O—?—O (target in middle)
        - ?—X—O (target at start, branching)
        
        Each pattern has 4 variations (2^2) based on subject/object position swapping
        """
        patterns = []
        attempts = 0
        max_attempts = count * 10
        
        while len(patterns) < count and attempts < max_attempts:
            attempts += 1
            
            # Randomly select two properties
            if len(self.properties) < 2:
                break
                
            prop1, prop2 = random.sample(self.properties, 2)
            prop1_str = self._shorten_uri(prop1)
            prop2_str = self._shorten_uri(prop2)
            
            pattern_type = random.choice(['middle_target', 'branching'])
            
            if pattern_type == 'middle_target':
                # O—?—O pattern: fixed_entity1 prop1 ?target . ?target prop2 fixed_entity2
                patterns.extend(self._generate_middle_target_pattern(prop1, prop2, prop1_str, prop2_str))
            else:
                # ?—X—O pattern: ?target prop1 ?hidden . ?hidden prop2 fixed_entity
                patterns.extend(self._generate_branching_pattern(prop1, prop2, prop1_str, prop2_str))
                
            if len(patterns) >= count:
                break
                
        return patterns[:count]
    
    def _generate_middle_target_pattern(self, prop1, prop2, prop1_str, prop2_str):
        """Generate O—?—O pattern with 4 variations"""
        patterns = []
        
        # Find entities that can connect via these properties
        entities1 = list(self.prop_to_subjects[prop1])
        entities2 = list(self.prop_to_objects[prop2])
        
        if not entities1 or not entities2:
            return patterns
            
        entity1 = random.choice(entities1)
        entity2 = random.choice(entities2)
        entity1_str = self._shorten_uri(entity1)
        entity2_str = self._shorten_uri(entity2)
        
        # Generate 4 variations by swapping subject/object positions
        variations = [
            f"{entity1_str} {prop1_str} ?target . ?target {prop2_str} {entity2_str}",  # original
            f"?target {prop1_str} {entity1_str} . {entity2_str} {prop2_str} ?target",  # both swapped
            f"{entity1_str} {prop1_str} ?target . {entity2_str} {prop2_str} ?target",  # second swapped
            f"?target {prop1_str} {entity1_str} . ?target {prop2_str} {entity2_str}"   # first swapped
        ]
        
        for i, variation in enumerate(variations):
            sparql = f"SELECT ?target WHERE {{ {variation} . }}"
            
            if self._validate_pattern(sparql):
                patterns.append({
                    'id': f'2p_mid_{i}_{len(patterns)}',
                    'sparql': self._format_sparql(sparql),
                    'pattern_type': f'2_prop_middle_target_v{i+1}',
                    'complexity': 'intermediate',
                    'properties': [prop1_str, prop2_str],
                    'fixed_entities': [entity1_str, entity2_str]
                })
                
        return patterns
    
    def _generate_branching_pattern(self, prop1, prop2, prop1_str, prop2_str):
        """Generate ?—X—O pattern with 4 variations"""
        patterns = []
        
        # Find entity that can be connected via prop2
        entities = list(self.prop_to_objects[prop2])
        if not entities:
            return patterns
            
        fixed_entity = random.choice(entities)
        fixed_str = self._shorten_uri(fixed_entity)
        
        # Generate 4 variations
        variations = [
            f"?target {prop1_str} ?hidden . ?hidden {prop2_str} {fixed_str}",      # original
            f"?hidden {prop1_str} ?target . {fixed_str} {prop2_str} ?hidden",      # both swapped
            f"?target {prop1_str} ?hidden . {fixed_str} {prop2_str} ?hidden",      # second swapped
            f"?hidden {prop1_str} ?target . ?hidden {prop2_str} {fixed_str}"       # first swapped
        ]
        
        for i, variation in enumerate(variations):
            sparql = f"SELECT ?target WHERE {{ {variation} . }}"
            
            if self._validate_pattern(sparql):
                patterns.append({
                    'id': f'2p_branch_{i}_{len(patterns)}',
                    'sparql': self._format_sparql(sparql),
                    'pattern_type': f'2_prop_branching_v{i+1}',
                    'complexity': 'intermediate',
                    'properties': [prop1_str, prop2_str],
                    'fixed_entity': fixed_str
                })
                
        return patterns
    
    def generate_3_property_patterns(self, count=100):
        """
        Generate 3-property patterns:
        - O—X—X—? (linear, target at end)
        - O—X—?—O (linear, target in middle)  
        - X branches to O, O, ? (star pattern, target is one branch)
        
        Each pattern has 8 variations (2^3) based on subject/object position swapping
        """
        patterns = []
        attempts = 0
        max_attempts = count * 15
        
        while len(patterns) < count and attempts < max_attempts:
            attempts += 1
            
            if len(self.properties) < 3:
                break
                
            # Randomly select three properties
            prop1, prop2, prop3 = random.sample(self.properties, 3)
            props_str = [self._shorten_uri(p) for p in [prop1, prop2, prop3]]
            
            pattern_type = random.choice(['linear_end', 'linear_middle', 'star'])
            
            if pattern_type == 'linear_end':
                patterns.extend(self._generate_linear_end_pattern(prop1, prop2, prop3, props_str))
            elif pattern_type == 'linear_middle':
                patterns.extend(self._generate_linear_middle_pattern(prop1, prop2, prop3, props_str))
            else:
                patterns.extend(self._generate_star_pattern(prop1, prop2, prop3, props_str))
                
            if len(patterns) >= count:
                break
                
        return patterns[:count]
    
    def _generate_linear_end_pattern(self, prop1, prop2, prop3, props_str):
        """Generate O—X—X—? pattern with 8 variations"""
        patterns = []
        
        # Find a starting entity
        entities = list(self.prop_to_subjects[prop1])
        if not entities:
            return patterns
            
        start_entity = random.choice(entities)
        start_str = self._shorten_uri(start_entity)
        
        # Generate 8 variations using bit manipulation
        for i in range(8):
            pattern_parts = []
            
            # Determine direction of each triple based on bit pattern
            if i & 1:  # bit 0: reverse first triple
                pattern_parts.append(f"?hidden1 {props_str[0]} {start_str}")
            else:
                pattern_parts.append(f"{start_str} {props_str[0]} ?hidden1")
                
            if i & 2:  # bit 1: reverse second triple
                pattern_parts.append(f"?hidden2 {props_str[1]} ?hidden1")
            else:
                pattern_parts.append(f"?hidden1 {props_str[1]} ?hidden2")
                
            if i & 4:  # bit 2: reverse third triple
                pattern_parts.append(f"?target {props_str[2]} ?hidden2")
            else:
                pattern_parts.append(f"?hidden2 {props_str[2]} ?target")
                
            pattern = " . ".join(pattern_parts)
            sparql = f"SELECT ?target WHERE {{ {pattern} . }}"
            
            if self._validate_pattern(sparql):
                patterns.append({
                    'id': f'3p_linear_end_{i}_{len(patterns)}',
                    'sparql': self._format_sparql(sparql),
                    'pattern_type': f'3_prop_linear_end_v{i+1}',
                    'complexity': 'advanced',
                    'properties': props_str,
                    'fixed_entity': start_str
                })
                
        return patterns
    
    def _generate_linear_middle_pattern(self, prop1, prop2, prop3, props_str):
        """Generate O—X—?—O pattern with 8 variations"""
        patterns = []
        
        # Find start and end entities
        start_entities = list(self.prop_to_subjects[prop1])
        end_entities = list(self.prop_to_objects[prop3])
        
        if not start_entities or not end_entities:
            return patterns
            
        start_entity = random.choice(start_entities)
        end_entity = random.choice(end_entities)
        start_str = self._shorten_uri(start_entity)
        end_str = self._shorten_uri(end_entity)
        
        # Generate 8 variations
        for i in range(8):
            pattern_parts = []
            
            if i & 1:  # bit 0
                pattern_parts.append(f"?hidden {props_str[0]} {start_str}")
            else:
                pattern_parts.append(f"{start_str} {props_str[0]} ?hidden")
                
            if i & 2:  # bit 1
                pattern_parts.append(f"?target {props_str[1]} ?hidden")
            else:
                pattern_parts.append(f"?hidden {props_str[1]} ?target")
                
            if i & 4:  # bit 2
                pattern_parts.append(f"{end_str} {props_str[2]} ?target")
            else:
                pattern_parts.append(f"?target {props_str[2]} {end_str}")
                
            pattern = " . ".join(pattern_parts)
            sparql = f"SELECT ?target WHERE {{ {pattern} . }}"
            
            if self._validate_pattern(sparql):
                patterns.append({
                    'id': f'3p_linear_mid_{i}_{len(patterns)}',
                    'sparql': self._format_sparql(sparql),
                    'pattern_type': f'3_prop_linear_middle_v{i+1}',
                    'complexity': 'advanced',
                    'properties': props_str,
                    'fixed_entities': [start_str, end_str]
                })
                
        return patterns
    
    def _generate_star_pattern(self, prop1, prop2, prop3, props_str):
        """Generate star pattern: ?hidden branches to fixed_entity1, fixed_entity2, ?target"""
        patterns = []
        
        # Find fixed entities for two branches
        entities1 = list(self.prop_to_objects[prop1])
        entities2 = list(self.prop_to_objects[prop2])
        
        if not entities1 or not entities2:
            return patterns
            
        fixed_entity1 = random.choice(entities1)
        fixed_entity2 = random.choice(entities2)
        fixed_str1 = self._shorten_uri(fixed_entity1)
        fixed_str2 = self._shorten_uri(fixed_entity2)
        
        # Generate 8 variations
        for i in range(8):
            pattern_parts = []
            
            if i & 1:  # bit 0
                pattern_parts.append(f"{fixed_str1} {props_str[0]} ?hidden")
            else:
                pattern_parts.append(f"?hidden {props_str[0]} {fixed_str1}")
                
            if i & 2:  # bit 1
                pattern_parts.append(f"{fixed_str2} {props_str[1]} ?hidden")
            else:
                pattern_parts.append(f"?hidden {props_str[1]} {fixed_str2}")
                
            if i & 4:  # bit 2
                pattern_parts.append(f"?target {props_str[2]} ?hidden")
            else:
                pattern_parts.append(f"?hidden {props_str[2]} ?target")
                
            pattern = " . ".join(pattern_parts)
            sparql = f"SELECT ?target WHERE {{ {pattern} . }}"
            
            if self._validate_pattern(sparql):
                patterns.append({
                    'id': f'3p_star_{i}_{len(patterns)}',
                    'sparql': self._format_sparql(sparql),
                    'pattern_type': f'3_prop_star_v{i+1}',
                    'complexity': 'advanced',
                    'properties': props_str,
                    'fixed_entities': [fixed_str1, fixed_str2]
                })
                
        return patterns
    
    def generate_dataset(self, size=1000):
        """Generate dataset based on pattern weights"""
        dataset = []
        
        # Calculate number of queries for each complexity level
        num_1_prop = int(size * self.pattern_weights[1])
        num_2_prop = int(size * self.pattern_weights[2])
        num_3_prop = size - num_1_prop - num_2_prop
        
        print(f"Generating {num_1_prop} 1-property, {num_2_prop} 2-property, {num_3_prop} 3-property patterns...")
        
        # Generate patterns
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
    ttl_file = 'final_result.ttl'
    
    if not os.path.exists(ttl_file):
        print(f"Error: {ttl_file} not found!")
        return
        
    # Initialize generator
    print("Initializing pattern-based SPARQL generator...")
    generator = PatternBasedSPARQLGenerator(ttl_file)
    
    # Generate dataset
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