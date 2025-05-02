"""
Knowledge Graph Schema Extractor - Modified for Indonesian Legal Document Knowledge Graph

This utility has been modified to focus specifically on extracting schema information
from the Indonesian legal document knowledge graph (data-lex2kg).
"""

import requests
import json
import re
from urllib.parse import urlencode
from rdflib import Graph, Namespace, URIRef, Literal
import os
from datetime import datetime

def separate_camel_case(text):
    """
    Separate camelCase text into words
    
    Args:
        text (str): Text in camelCase
        
    Returns:
        str: Text with spaces between words
    """
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

def legal_entity_label(url):
    """
    Generate a human-readable label from a legal entity URL
    
    Args:
        url (str): The entity URL
        
    Returns:
        str: A formatted label
    """
    parts = url.strip('/').split('/')
    transformed_parts = []
    
    month_mapping = {
        "January": "Januari", "February": "Februari", "March": "Maret", "April": "April", "May": "Mei", "June": "Juni",
        "July": "Juli", "August": "Agustus", "September": "September", "October": "Oktober", "November": "November", "December": "Desember"
    }
    
    for i, part in enumerate(parts):
        if part == "lex2kg":
            transformed_parts = []
            continue
        if part == "uu":
            transformed_parts.append("UU")
        elif part.isdigit() and len(part) <= 2:
            transformed_parts.append(f"no {part}")
        elif part.isdigit() and len(part) == 4 and int(part) >= 1945:
            transformed_parts.append(f"tahun {part}")
        elif part.isdigit() and len(part) == 8:
            try:
                date_obj = datetime.strptime(part, "%Y%m%d")
                formatted_date = date_obj.strftime("%-d %B %Y")
                for eng, indo in month_mapping.items():
                    formatted_date = formatted_date.replace(eng, indo)
                transformed_parts.append(formatted_date)
            except ValueError:
                transformed_parts.append(part)
        elif part.isdigit():
            num = str(int(part))
            transformed_parts.append(num)
        else:
            transformed_parts.append(separate_camel_case(part).lower())
    
    return ' '.join(transformed_parts)

def legal_property_label(x):
    """
    Generate a human-readable label from a legal property
    
    Args:
        x (str): The property URI or prefixed name
        
    Returns:
        str: A formatted label
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()

class KGSchemaExtractor:
    """
    Extract schema information from the legal document knowledge graph.
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
                'lex2kg-o': 'https://example.org/lex2kg/ontology/'  # Added legal ontology prefix
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
        Extract schema from the legal document TTL file
        
        Args:
            file_path (str): Path to the TTL file
            format (str): Format of the file (turtle, n-triples, rdf-xml)
            
        Returns:
            dict: Extracted schema info
        """
        print(f"Extracting schema from legal document TTL file: {file_path}")
        
        try:
            # Parse the RDF file using rdflib
            self.graph = Graph()
            self.graph.parse(file_path, format=format)
            
            # Debug info
            if self.options["debug"]:
                print(f"Loaded graph with {len(self.graph)} triples")
                
                # Print sample triples
                print("\nSample triples from legal document graph:")
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
            
            # Extract schema information - MODIFIED FOR LEGAL DOCUMENT DATA
            self.parse_legal_document_graph(self.graph)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from legal document TTL file: {e}")
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
            self.parse_legal_document_graph(self.graph)
            
            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"]
            }
        except Exception as e:
            print(f"Error extracting schema from string: {e}")
            raise e
    
    def parse_legal_document_graph(self, graph):
        """
        Parse the legal document graph to extract schema information
        
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
        LEX = Namespace("https://example.org/lex2kg/ontology/")
        
        # MODIFIED FOR LEGAL DOCUMENT DATA:
        # Extract classes both from formal declarations and from usage
        class_uris = set()
        
        # 1. Look for formal class declarations
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
        
        # 3. Add common legal document types manually if not found
        legal_classes = [
            LEX.UndangUndang,
            LEX.Pasal,
            LEX.Ayat,
            LEX.Bab,
            LEX.Bagian,
            LEX.Paragraf,
            LEX.Huruf,
            LEX.Segmen
        ]
        
        for cls in legal_classes:
            if cls not in class_uris:
                class_uris.add(cls)
        
        if self.options["debug"]:
            print(f"\nFound {len(class_uris)} potential classes/types")
            for cls in list(class_uris)[:10]:  # Show first 10
                print(f"  - {cls}")
        
        # Process each identified class
        for class_uri in class_uris:
            label = None
            # Try to find a label
            for s, p, o in graph.triples((class_uri, RDFS.label, None)):
                label = str(o)
                break
                
            if not label:
                label = legal_property_label(str(class_uri))
                
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
        
        # 3. Add common legal document properties manually if not found
        legal_properties = [
            LEX.jenisPeraturan,
            LEX.nomor,
            LEX.tanggal,
            LEX.disahkanPada,
            LEX.segmen,
            LEX.judul,
            LEX.bahasa,
            LEX.tentang,
            LEX.paragraf,
            LEX.jabatanPengesah,
            LEX.disahkanDi,
            LEX.disahkanOleh,
            LEX.mengubah,
            LEX.bagianDari,
            LEX.versi,
            LEX.jenisVersi,
            LEX.menyisipkan,
            LEX.menghapus,
            LEX.merujuk,
            LEX.teks
        ]
        
        for prop in legal_properties:
            if prop not in property_uris:
                property_uris.add(prop)
        
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
                label = legal_property_label(str(property_uri))
                
            property_info = {
                "value": self.shorten_uri(str(property_uri)),
                "label": label,
                "uri": str(property_uri),
                "domain": domain,
                "range": range_uri
            }
            
            self.schema_info["properties"].append(property_info)
            
            # Categorize property based on range or observed values
            self.categorize_legal_property(property_info, graph)
        
        # Extract entity examples for each class/type
        for type_info in self.schema_info["types"]:
            self.extract_legal_entities(type_info)
    
    def categorize_legal_property(self, property_info, graph):
        """
        Categorize legal document properties by examining their values
        
        Args:
            property_info (dict): Property to categorize
            graph (rdflib.Graph): The RDF graph
        """
        # First check if the range hints at a type
        if property_info.get("range"):
            self.categorize_property_by_range(property_info)
            return
        
        # Special handling for known legal document properties
        property_uri = property_info["uri"]
        
        # Known numeric properties
        if property_uri in [
            "https://example.org/lex2kg/ontology/nomor",
            "https://example.org/lex2kg/ontology/tahun"
        ]:
            self.add_to_property_category('numericProperties', property_info)
            return
            
        # Known date properties
        if property_uri in [
            "https://example.org/lex2kg/ontology/tanggal",
            "https://example.org/lex2kg/ontology/disahkanPada"
        ]:
            self.add_to_property_category('dateProperties', property_info)
            return
            
        # Known text properties
        if property_uri in [
            "https://example.org/lex2kg/ontology/judul",
            "https://example.org/lex2kg/ontology/tentang",
            "https://example.org/lex2kg/ontology/teks",
            "https://example.org/lex2kg/ontology/disahkanOleh",
            "https://example.org/lex2kg/ontology/disahkanDi",
            "https://example.org/lex2kg/ontology/jabatanPengesah",
            "https://example.org/lex2kg/ontology/bahasa"
        ]:
            self.add_to_property_category('textProperties', property_info)
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
    
    def extract_legal_entities(self, type_info):
        """
        Extract example entities for a legal document class/type
        
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
            
            # MODIFIED: Use the legal_entity_label function to generate a label from the URI
            label = legal_entity_label(entity_uri)
                
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
        # Date patterns for Indonesian legal documents
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD (ISO format)
            r'^\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'^\d{2}-\d{2}-\d{4}',  # DD-MM-YYYY
            r'^\d{4}$'              # Just a year
        ]
        
        return any(re.match(pattern, string) for pattern in date_patterns)
    
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
    
    # SPARQL endpoint methods below are unchanged
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