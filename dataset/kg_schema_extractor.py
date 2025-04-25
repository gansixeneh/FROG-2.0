"""
Knowledge Graph Schema Extractor

This utility helps extract schema information from a knowledge graph
to configure the NL2SPARQL Generator.

It works with:
1. SPARQL endpoints
2. RDF files (Turtle, N-Triples, RDF/XML)
3. JSON-LD data
"""

import requests
import json
import re
from urllib.parse import urlencode
from rdflib import Graph, Namespace, URIRef
import os

class KGSchemaExtractor:
    """
    Extract schema information from a knowledge graph to configure the NL2SPARQL Generator.
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
            "prefixes": {
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'owl': 'http://www.w3.org/2002/07/owl#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#'
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
        Extract schema from an RDF file
        
        Args:
            file_path (str): Path to the RDF file
            format (str): Format of the file (turtle, n-triples, rdf-xml)
            
        Returns:
            dict: Extracted schema info
        """
        print(f"Extracting schema from RDF file: {file_path} ({format})")
        
        try:
            # Parse the RDF file using rdflib
            g = Graph()
            g.parse(file_path, format=format)
            
            # Extract schema information
            self.parse_rdf_graph(g)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from file: {e}")
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
            g = Graph()
            g.parse(data=content, format=format)
            
            # Extract schema information
            self.parse_rdf_graph(g)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from string: {e}")
            raise e
    
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
        print("Extracting classes/types...")
        
        prefixes = self.get_prefix_string()
        query = f"""
            {prefixes}
            SELECT DISTINCT ?class ?label
            WHERE {{
              {{
                ?class a rdfs:Class .
                OPTIONAL {{ ?class rdfs:label ?label }}
              }}
              UNION 
              {{
                ?class a owl:Class .
                OPTIONAL {{ ?class rdfs:label ?label }}
              }}
            }}
            LIMIT {self.options["sample_size"]}
        """
        
        try:
            result = self.execute_sparql_query(query)
            
            self.schema_info["types"] = [
                {
                    "value": self.shorten_uri(binding["class"]["value"]),
                    "label": binding.get("label", {}).get("value", self.extract_label_from_uri(binding["class"]["value"])),
                    "uri": binding["class"]["value"]
                }
                for binding in result["results"]["bindings"]
            ]
            
            print(f"Extracted {len(self.schema_info['types'])} classes/types")
        except Exception as e:
            print(f"Error extracting classes: {e}")
    
    def extract_properties(self):
        """Extract properties from the knowledge graph"""
        print("Extracting properties...")
        
        prefixes = self.get_prefix_string()
        query = f"""
            {prefixes}
            SELECT DISTINCT ?property ?label ?domain ?range
            WHERE {{
              {{
                ?property a rdf:Property .
                OPTIONAL {{ ?property rdfs:label ?label }}
                OPTIONAL {{ ?property rdfs:domain ?domain }}
                OPTIONAL {{ ?property rdfs:range ?range }}
              }}
              UNION 
              {{
                ?property a owl:ObjectProperty .
                OPTIONAL {{ ?property rdfs:label ?label }}
                OPTIONAL {{ ?property rdfs:domain ?domain }}
                OPTIONAL {{ ?property rdfs:range ?range }}
              }}
              UNION 
              {{
                ?property a owl:DatatypeProperty .
                OPTIONAL {{ ?property rdfs:label ?label }}
                OPTIONAL {{ ?property rdfs:domain ?domain }}
                OPTIONAL {{ ?property rdfs:range ?range }}
              }}
            }}
            LIMIT {self.options["sample_size"]}
        """
        
        try:
            result = self.execute_sparql_query(query)
            
            self.schema_info["properties"] = []
            for binding in result["results"]["bindings"]:
                uri = binding["property"]["value"]
                label = binding.get("label", {}).get("value", self.extract_label_from_uri(uri))
                
                property_info = {
                    "value": self.shorten_uri(uri),
                    "label": label,
                    "uri": uri,
                    "domain": binding.get("domain", {}).get("value"),
                    "range": binding.get("range", {}).get("value")
                }
                
                self.schema_info["properties"].append(property_info)
            
            print(f"Extracted {len(self.schema_info['properties'])} properties")
        except Exception as e:
            print(f"Error extracting properties: {e}")
    
    def extract_property_types(self):
        """Categorize properties by their range types (numeric, date, text, etc.)"""
        print("Categorizing properties by type...")
        
        # First, check the range of properties from schema info
        for property_info in self.schema_info["properties"]:
            if property_info.get("range"):
                self.categorize_property_by_range(property_info)
        
        # Then, examine actual property values in the data
        self.examine_property_values()
        
        print(f"""Categorized properties: 
            - Numeric: {len(self.schema_info['numericProperties'])}
            - Date: {len(self.schema_info['dateProperties'])}
            - Text: {len(self.schema_info['textProperties'])}
            - Boolean: {len(self.schema_info['booleanProperties'])}""")
    
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
    
    def examine_property_values(self):
        """Examine property values in the data to determine property types"""
        print("Examining property values to determine types...")
        
        # Find uncategorized properties
        uncategorized_properties = []
        for prop in self.schema_info["properties"]:
            if (not any(p["uri"] == prop["uri"] for p in self.schema_info["numericProperties"]) and
                not any(p["uri"] == prop["uri"] for p in self.schema_info["dateProperties"]) and
                not any(p["uri"] == prop["uri"] for p in self.schema_info["textProperties"]) and
                not any(p["uri"] == prop["uri"] for p in self.schema_info["booleanProperties"])):
                uncategorized_properties.append(prop)
        
        for property_info in uncategorized_properties:
            try:
                self.categorize_property_by_values(property_info)
            except Exception as e:
                print(f"Error categorizing property {property_info['uri']}: {e}")
    
    def categorize_property_by_values(self, property_info):
        """
        Categorize a property by examining its values
        
        Args:
            property_info (dict): Property to categorize
        """
        if not self.options["sparql_endpoint"]:
            return  # Skip if no endpoint configured
            
        prefixes = self.get_prefix_string()
        property_uri = property_info["uri"]
        
        query = f"""
            {prefixes}
            SELECT ?value (DATATYPE(?value) as ?datatype)
            WHERE {{
              ?s <{property_uri}> ?value .
            }}
            LIMIT 100
        """
        
        try:
            result = self.execute_sparql_query(query)
            
            if not result["results"]["bindings"]:
                return  # No values found
            
            # Count occurrences of each datatype
            datatype_counts = {}
            
            for binding in result["results"]["bindings"]:
                if "datatype" in binding:
                    datatype = binding["datatype"]["value"]
                    datatype_counts[datatype] = datatype_counts.get(datatype, 0) + 1
                else:
                    # If no datatype, try to infer from the value
                    value = binding["value"]["value"]
                    
                    if value.replace('.', '', 1).isdigit():  # Check if numeric
                        datatype_counts["numeric"] = datatype_counts.get("numeric", 0) + 1
                    elif self.is_date_string(value):
                        datatype_counts["date"] = datatype_counts.get("date", 0) + 1
                    elif value.lower() in ["true", "false"]:
                        datatype_counts["boolean"] = datatype_counts.get("boolean", 0) + 1
                    else:
                        datatype_counts["text"] = datatype_counts.get("text", 0) + 1
            
            # Determine the most common datatype
            most_common_type = None
            max_count = 0
            
            for datatype, count in datatype_counts.items():
                if count > max_count:
                    most_common_type = datatype
                    max_count = count
            
            # Categorize based on the most common datatype
            if most_common_type:
                if (any(numeric_type in most_common_type for numeric_type in 
                       ["integer", "decimal", "float", "double"]) or 
                    most_common_type == "numeric"):
                    self.add_to_property_category("numericProperties", property_info)
                elif any(date_type in most_common_type for date_type in ["date", "time"]):
                    self.add_to_property_category("dateProperties", property_info)
                elif "boolean" in most_common_type:
                    self.add_to_property_category("booleanProperties", property_info)
                else:
                    self.add_to_property_category("textProperties", property_info)
        except Exception as e:
            print(f"Could not examine values for property {property_uri}: {e}")
    
    def extract_entity_examples(self):
        """Extract entity examples for the dataset"""
        print("Extracting entity examples...")
        
        # Extract examples for each class/type
        for type_info in self.schema_info["types"]:
            try:
                self.extract_examples_for_type(type_info)
            except Exception as e:
                print(f"Error extracting examples for type {type_info['uri']}: {e}")
        
        print(f"Extracted {len(self.entity_examples)} entity examples")
    
    def extract_examples_for_type(self, type_info):
        """
        Extract example entities for a specific type
        
        Args:
            type_info (dict): The entity type
        """
        prefixes = self.get_prefix_string()
        type_uri = type_info["uri"]
        
        query = f"""
            {prefixes}
            SELECT DISTINCT ?entity ?label
            WHERE {{
              ?entity a <{type_uri}> .
              OPTIONAL {{ ?entity rdfs:label ?label }}
            }}
            LIMIT 10
        """
        
        try:
            result = self.execute_sparql_query(query)
            
            examples = []
            for binding in result["results"]["bindings"]:
                uri = binding["entity"]["value"]
                label = binding.get("label", {}).get("value", self.extract_label_from_uri(uri))
                
                examples.append({
                    "value": self.shorten_uri(uri),
                    "label": label,
                    "uri": uri,
                    "type": type_info["value"]
                })
            
            self.entity_examples.extend(examples)
        except Exception as e:
            print(f"Could not extract examples for type {type_uri}: {e}")
    
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
        Extract a label from a URI
        
        Args:
            uri (str): URI to extract label from
            
        Returns:
            str: Extracted label
        """
        # Extract the last part of the URI
        last_part = uri.split('/')[-1].split('#')[-1]
        
        # Remove underscores and replace with spaces
        with_spaces = last_part.replace('_', ' ')
        
        # Convert camelCase to spaces
        return re.sub(r'([a-z])([A-Z])', r'\1 \2', with_spaces)
    
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
    
    def parse_rdf_graph(self, graph):
        """
        Parse an RDF graph to extract schema information
        
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
        
        # Extract classes
        class_uris = set()
        for s, p, o in graph.triples((None, RDF.type, RDFS.Class)):
            class_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.Class)):
            class_uris.add(s)
            
        for class_uri in class_uris:
            label = None
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
        
        # Extract properties
        property_uris = set()
        for s, p, o in graph.triples((None, RDF.type, RDF.Property)):
            property_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.ObjectProperty)):
            property_uris.add(s)
        for s, p, o in graph.triples((None, RDF.type, OWL.DatatypeProperty)):
            property_uris.add(s)
            
        for property_uri in property_uris:
            label = None
            domain = None
            range_uri = None
            
            for s, p, o in graph.triples((property_uri, RDFS.label, None)):
                label = str(o)
                break
                
            for s, p, o in graph.triples((property_uri, RDFS.domain, None)):
                domain = str(o)
                break
                
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
            
            # Categorize property based on range
            if range_uri:
                self.categorize_property_by_range(property_info)
        
        # Extract examples for each class
        for type_info in self.schema_info["types"]:
            count = 0
            for s, p, o in graph.triples((None, RDF.type, URIRef(type_info["uri"]))):
                if count >= 10:  # Limit to 10 examples per type
                    break
                    
                label = None
                for s2, p2, o2 in graph.triples((s, RDFS.label, None)):
                    label = str(o2)
                    break
                    
                if not label:
                    label = self.extract_label_from_uri(str(s))
                    
                self.entity_examples.append({
                    "value": self.shorten_uri(str(s)),
                    "label": label,
                    "uri": str(s),
                    "type": type_info["value"]
                })
                
                count += 1