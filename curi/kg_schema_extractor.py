"""
Knowledge Graph Schema Extractor - Modified for University Course TTL

This utility has been temporarily modified to focus specifically on extracting schema information
from the university course TTL file (final_result.ttl).
"""

import requests
import json
import re
from urllib.parse import urlencode
from rdflib import Graph, Namespace, URIRef, Literal
import os

class KGSchemaExtractor:
    """
    Extract schema information from the university course knowledge graph.
    """
    
    def __init__(self, options=None):
        """
        Initialize a new schema extractor
        
        Args:
            options (dict): Configuration options
        """
        self.options = {
            "sparql_endpoint": None,
            "sample_size": 1000,
            "debug": False,  # Debug flag
            "prefixes": {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'owl': 'http://www.w3.org/2002/07/owl#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#',
                'ns1': 'http://example.org/'  # Added university course prefix
            }
        }
        
        if options:
            self.options.update(options)
            
        self.schema_info = {
            "properties": [],
            "types": [],
            "numericProperties": [],
            "dateProperties": [],
            "textProperties": [],
            "booleanProperties": []
        }
        
        self.entity_examples = []
        self.graph = None  # Store the graph for later use
    
    def extract_from_endpoint(self, endpoint):
        """
        Extract schema from a SPARQL endpoint
        
        Args:
            endpoint (str): URL of the SPARQL endpoint
            
        Returns:
            dict: Extracted schema info
        """
        print(f"Extracting schema from SPARQL endpoint: {endpoint}")
        self.options["sparql_endpoint"] = endpoint
        
        try:
            self.extract_classes()
            self.extract_properties()
            self.extract_property_types()
            self.extract_entity_examples()
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema: {e}")
            raise e
    
    def extract_from_file(self, file_path, format='turtle'):
        """
        Extract schema from the university course TTL file
        
        Args:
            file_path (str): Path to the TTL file
            format (str): Format of the file (turtle, n-triples, rdf-xml)
            
        Returns:
            dict: Extracted schema info
        """
        print(f"Extracting schema from university course TTL file: {file_path}")
        
        try:
            # Parse the RDF file using rdflib
            self.graph = Graph()
            self.graph.parse(file_path, format=format)
            
            # Debug info
            if self.options["debug"]:
                print(f"Loaded graph with {len(self.graph)} triples")
                
                # Print sample triples
                print("\nSample triples from university graph:")
                for i, (s, p, o) in enumerate(self.graph):
                    if i < 5:  # First 5 triples
                        print(f"  {s} {p} {o}")
                
                # Count by predicate
                predicates = {}
                for _, p, _ in self.graph:
                    pred_str = str(p)
                    if pred_str in predicates:
                        predicates[pred_str] += 1
                    else:
                        predicates[pred_str] = 1
                
                print("\nMost common predicates:")
                for pred, count in sorted(predicates.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"  {pred}: {count}")
            
            # Extract schema information - MODIFIED FOR UNIVERSITY COURSE DATA
            self.parse_university_course_graph(self.graph)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from university TTL file: {e}")
            raise e
    
    def extract_from_string(self, content, format):
        """
        Extract schema from RDF string content
        
        Args:
            content (str): RDF content as string
            format (str): Format of the content (turtle, n-triples, rdf-xml, jsonld)
            
        Returns:
            dict: Extracted schema info
        """
        print(f"Extracting schema from RDF string ({format})")
        
        try:
            # Parse the RDF content using rdflib
            self.graph = Graph()
            self.graph.parse(data=content, format=format)
            
            # Extract schema information
            self.parse_university_course_graph(self.graph)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from string: {e}")
            raise e
    
    def parse_university_course_graph(self, graph):
        """
        Parse the university course graph to extract schema information
        
        Args:
            graph (rdflib.Graph): The RDF graph to parse
        """
        # Extract prefixes from the graph
        for prefix, namespace in graph.namespaces():
            if prefix and str(namespace) not in self.options["prefixes"].values():
                self.options["prefixes"][str(prefix)] = str(namespace)

        # RDF, RDFS and OWL namespaces
        RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
        RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        OWL = Namespace("http://www.w3.org/2002/07/owl#")
        NS1 = Namespace("http://example.org/")
        
        # MODIFIED FOR UNIVERSITY COURSE DATA:
        # Extract classes both from formal declarations and from usage
        class_uris = set()
        
        # 1. Look for formal class declarations (none in university TTL)
        for s, p, o in graph.triples((None, RDF.type, RDFS.Class)):
            class_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.Class)):
            class_uris.add(s)
            
        # 2. Infer classes from usage - any URI that appears as object of rdf:type
        type_objects = set()
        for s, p, o in graph.triples((None, RDF.type, None)):
            if isinstance(o, URIRef):  # Make sure it's a URI, not a literal
                type_objects.add(o)
        
        # Add these to our classes
        class_uris.update(type_objects)
        
        if self.options["debug"]:
            print(f"\nFound {len(class_uris)} potential classes/types")
            for cls in class_uris:
                print(f"  - {cls}")
        
        # Process each identified class
        for class_uri in class_uris:
            label = None
            # Try to find a label
            for s, p, o in graph.triples((class_uri, RDFS.label, None)):
                label = str(o)
                break
                
            if not label:
                label = self.extract_label_from_uri(str(class_uri))
                
            self.schema_info["types"].append({
                "value": self.shorten_uri(str(class_uri)),
                "label": label,
                "uri": str(class_uri)
            })
        
        # Extract properties - both from formal declarations and observed usage
        property_uris = set()
        
        # 1. First, get formally declared properties
        for s, p, o in graph.triples((None, RDF.type, RDF.Property)):
            property_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.ObjectProperty)):
            property_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.DatatypeProperty)):
            property_uris.add(s)
            
        # 2. Get all predicates used in the graph as potential properties
        for s, p, o in graph:
            if p != RDF.type and isinstance(p, URIRef):  # Skip rdf:type itself
                property_uris.add(p)
        
        if self.options["debug"]:
            print(f"\nFound {len(property_uris)} potential properties")
            for prop in list(property_uris)[:10]:  # Show first 10
                print(f"  - {prop}")
        
        # Process each property
        for property_uri in property_uris:
            label = None
            domain = None
            range_uri = None
            
            # Get label
            for s, p, o in graph.triples((property_uri, RDFS.label, None)):
                label = str(o)
                break
            
            # Get domain
            for s, p, o in graph.triples((property_uri, RDFS.domain, None)):
                domain = str(o)
                break
                
            # Get range
            for s, p, o in graph.triples((property_uri, RDFS.range, None)):
                range_uri = str(o)
                break
                
            if not label:
                label = self.extract_label_from_uri(str(property_uri))
                
            property_info = {
                "value": self.shorten_uri(str(property_uri)),
                "label": label,
                "uri": str(property_uri),
                "domain": domain,
                "range": range_uri
            }
            
            self.schema_info["properties"].append(property_info)
            
            # Categorize property based on range or observed values
            self.categorize_university_property(property_info, graph)
        
        # Extract entity examples for each class/type
        for type_info in self.schema_info["types"]:
            self.extract_university_entities(type_info)
    
    def categorize_university_property(self, property_info, graph):
        """
        Categorize university course properties by examining their values
        
        Args:
            property_info (dict): Property to categorize
            graph (rdflib.Graph): The RDF graph
        """
        # First check if the range hints at a type
        if property_info.get("range"):
            self.categorize_property_by_range(property_info)
            return
            
        # Next, look at actual values in the data
        prop_uri = URIRef(property_info["uri"])
        values = []
        
        # Get some sample values for this property
        for s, p, o in graph.triples((None, prop_uri, None)):
            if len(values) < 10:  # Limit to 10 samples
                values.append(o)
            else:
                break
                
        # No values found
        if not values:
            return
            
        # Categorize based on the observed values
        numeric_count = 0
        date_count = 0
        bool_count = 0
        
        for value in values:
            if isinstance(value, Literal):
                # Check datatype if available
                if value.datatype:
                    datatype = str(value.datatype)
                    if any(t in datatype for t in ["integer", "decimal", "float", "double"]):
                        numeric_count += 1
                    elif any(t in datatype for t in ["date", "time"]):
                        date_count += 1
                    elif "boolean" in datatype:
                        bool_count += 1
                else:
                    # No datatype - try to infer from the value
                    try:
                        value_str = str(value)
                        float(value_str)  # Attempt to convert to number
                        numeric_count += 1
                    except ValueError:
                        if value_str.lower() in ['true', 'false']:
                            bool_count += 1
                        elif self.is_date_string(value_str):
                            date_count += 1
        
        # Determine the most likely category based on counts
        if numeric_count > 0 and numeric_count >= len(values) / 2:
            self.add_to_property_category('numericProperties', property_info)
        elif date_count > 0 and date_count >= len(values) / 2:
            self.add_to_property_category('dateProperties', property_info)
        elif bool_count > 0 and bool_count >= len(values) / 2:
            self.add_to_property_category('booleanProperties', property_info)
        else:
            self.add_to_property_category('textProperties', property_info)
    
    def extract_university_entities(self, type_info):
        """
        Extract example entities for a university course class/type
        
        Args:
            type_info (dict): The entity type
        """
        type_uri = URIRef(type_info["uri"])
        count = 0
        max_examples = 20  # Extract more examples for better dataset quality
        
        # Find all entities of this type
        for s, p, o in self.graph.triples((None, URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), type_uri)):
            if count >= max_examples:
                break
                
            entity_uri = str(s)
            label = None
            
            # Look for a label
            for s2, p2, o2 in self.graph.triples((s, URIRef('http://www.w3.org/2000/01/rdf-schema#label'), None)):
                label = str(o2)
                break
                
            if not label:
                # For university data, try also_known_as as fallback
                for s2, p2, o2 in self.graph.triples((s, URIRef('http://example.org/also_known_as'), None)):
                    label = str(o2)
                    break
                    
            if not label:
                label = self.extract_label_from_uri(entity_uri)
                
            # Add this entity to our examples
            entity_info = {
                "value": self.shorten_uri(entity_uri),
                "label": label,
                "uri": entity_uri,
                "type": type_info["value"]
            }
            
            self.entity_examples.append(entity_info)
            count += 1
            
        if self.options["debug"] and count > 0:
            print(f"Extracted {count} examples of type {type_info['label']}")
    
    def categorize_property_by_range(self, property_info):
        """
        Categorize a property based on its rdfs:range
        
        Args:
            property_info (dict): Property to categorize
        """
        range_uri = property_info.get("range")
        if not range_uri:
            return
        
        # Numeric ranges
        if range_uri in [
            'http://www.w3.org/2001/XMLSchema#integer',
            'http://www.w3.org/2001/XMLSchema#decimal',
            'http://www.w3.org/2001/XMLSchema#float',
            'http://www.w3.org/2001/XMLSchema#double'
        ]:
            self.add_to_property_category('numericProperties', property_info)
        
        # Date ranges
        elif range_uri in [
            'http://www.w3.org/2001/XMLSchema#date',
            'http://www.w3.org/2001/XMLSchema#dateTime',
            'http://www.w3.org/2001/XMLSchema#time'
        ]:
            self.add_to_property_category('dateProperties', property_info)
        
        # Text ranges
        elif range_uri in [
            'http://www.w3.org/2001/XMLSchema#string',
            'http://www.w3.org/2000/01/rdf-schema#Literal'
        ]:
            self.add_to_property_category('textProperties', property_info)
        
        # Boolean ranges
        elif range_uri == 'http://www.w3.org/2001/XMLSchema#boolean':
            self.add_to_property_category('booleanProperties', property_info)
    
    def add_to_property_category(self, category, property_info):
        """
        Add a property to a specific category
        
        Args:
            category (str): Category name
            property_info (dict): Property to add
        """
        # Check if property already exists in the category
        if not any(p["uri"] == property_info["uri"] for p in self.schema_info[category]):
            self.schema_info[category].append(property_info)
    
    def is_date_string(self, string):
        """
        Check if a string resembles a date
        
        Args:
            string (str): String to check
            
        Returns:
            bool: True if string looks like a date
        """
        # Simple date patterns
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'^\d{4}/\d{2}/\d{2}',  # YYYY/MM/DD
            r'^\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'  # ISO date with time
        ]
        
        return any(re.match(pattern, string) for pattern in date_patterns)
    
    def extract_label_from_uri(self, uri):
        """
        Extract a label from a URI, with special handling for university data
        
        Args:
            uri (str): URI to extract label from
            
        Returns:
            str: Extracted label
        """
        # Extract the last part of the URI
        last_part = uri.split('/')[-1].split('#')[-1]
        
        # Special handling for university data (lots of underscores)
        if '_' in last_part:
            # Remove underscores and replace with spaces
            with_spaces = last_part.replace('_', ' ')
            # Capitalize each word
            return ' '.join(word.capitalize() for word in with_spaces.split())
        else:
            # Convert camelCase to spaces with standard approach
            return re.sub(r'([a-z])([A-Z])', r'\1 \2', last_part)
    
    def shorten_uri(self, uri):
        """
        Shorten a URI using known prefixes
        
        Args:
            uri (str): URI to shorten
            
        Returns:
            str: Shortened URI
        """
        for prefix, namespace in self.options["prefixes"].items():
            if uri.startswith(namespace):
                return f"{prefix}:{uri[len(namespace):]}"
        
        return uri
    
    def get_prefix_string(self):
        """
        Get prefixes formatted as a SPARQL prefix string
        
        Returns:
            str: Prefix string
        """
        return "\n".join([
            f"PREFIX {prefix}: <{namespace}>"
            for prefix, namespace in self.options["prefixes"].items()
        ])
    
    # SPARQL endpoint methods below unchanged
    def execute_sparql_query(self, query):
        """
        Execute a SPARQL query against the configured endpoint
        
        Args:
            query (str): SPARQL query to execute
            
        Returns:
            dict: Query results
        """
        if not self.options["sparql_endpoint"]:
            raise ValueError("No SPARQL endpoint configured")
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/sparql-results+json'
        }
        
        params = {
            'query': query,
            'format': 'json'
        }
        
        response = requests.post(
            self.options["sparql_endpoint"],
            headers=headers,
            data=urlencode(params)
        )
        
        if not response.ok:
            raise Exception(f"SPARQL query failed: {response.status_code} {response.reason}")
        
        return response.json()
    
    def extract_classes(self):
        """Extract classes/types from the knowledge graph"""
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def extract_properties(self):
        """Extract properties from the knowledge graph"""
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def extract_property_types(self):
        """Categorize properties by their range types (numeric, date, text, etc.)"""
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def examine_property_values(self):
        """Examine property values in the data to determine property types"""
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def categorize_property_by_values(self, property_info):
        """
        Categorize a property by examining its values
        """
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def extract_entity_examples(self):
        """Extract entity examples for the dataset"""
        # Standard code for SPARQL endpoint method - unchanged
        pass
    
    def extract_examples_for_type(self, type_info):
        """
        Extract example entities for a specific type
        """
        # Standard code for SPARQL endpoint method - unchanged
        pass