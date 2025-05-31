# gesis/kg_schema_extractor.py
"""
Knowledge Graph Schema Extractor - Modified for GESIS Knowledge Graph

This utility extracts schema information from the GESIS Knowledge Graph using either:
1. CSV files (preferred for efficiency)
2. Fuseki server SPARQL endpoint (fallback)
"""

import requests
import json
import re
import os
import pandas as pd
import logging
from urllib.parse import urlencode
from SPARQLWrapper import SPARQLWrapper, JSON

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def separate_camel_case(text):
    """
    Separate camelCase text into words
    """
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def gesis_entity_label(url):
    """
    Generate a human-readable label from a GESIS entity URL
    """
    if not url or not isinstance(url, str):
        return "Unknown"
        
    # Try to extract a meaningful label from the URL
    parts = url.strip("/").split("/")
    
    # If it's a resource URL, focus on the last part
    if "resource" in parts:
        resource_name = parts[-1]
        # URL decode
        resource_name = resource_name.replace("%3A", ":").replace("%2F", "/")
        # Clean up any URL encoding or hyphens
        resource_name = resource_name.replace("-", " ")
        return separate_camel_case(resource_name)
    
    # For schema URLs, extract the property or class name
    elif "schema" in parts:
        schema_name = parts[-1]
        return separate_camel_case(schema_name)
    
    # Default case - just return the last part of the URL
    else:
        return separate_camel_case(parts[-1])


def gesis_property_label(x):
    """
    Generate a human-readable label from a GESIS property
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()


class KGSchemaExtractor:
    """
    Extract schema information from the GESIS knowledge graph using either CSV files
    or Fuseki server.
    """

    def __init__(self, options=None):
        """
        Initialize a new schema extractor

        Args:
            options (dict): Configuration options
        """
        self.options = {
            "sparql_endpoint": "http://localhost:3030/gesis",
            "sample_size": 1000,
            "debug": False,  # Debug flag
            "prefixes": {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "owl": "http://www.w3.org/2002/07/owl#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "schema": "https://schema.org/",
                "gesiskg": "https://data.gesis.org/gesiskg/schema/",
                "disco": "https://rdf-vocabulary.ddialliance.org/discovery.html#",
                "nfdicore": "https://nfdi.fiz-karlsruhe.de/ontology/",
                "skos": "http://www.w3.org/2004/02/skos/core#",
                "void": "http://rdfs.org/ns/void#",
            },
            # Default CSV file paths
            "entities_csv_path": "gesis_entities.csv",
            "properties_csv_path": "gesis_properties.csv",
            "types_csv_path": "gesis_types.csv",
            "schema_info_csv_path": "gesis_schema_info.csv",
            # Use CSV files if available
            "use_csv": True
        }

        if options:
            self.options.update(options)

        self.schema_info = {
            "properties": [],
            "types": [],
            "numericProperties": [],
            "dateProperties": [],
            "textProperties": [],
            "booleanProperties": [],
        }

        self.entity_examples = []
        self.csv_available = self._check_csv_availability()

        # Initialize the SPARQL client (as fallback)
        self.sparql_client = SPARQLWrapper(self.options["sparql_endpoint"])
        self.sparql_client.setReturnFormat(JSON)

    def _check_csv_availability(self):
        """Check if CSV files are available for use"""
        if not self.options["use_csv"]:
            return False
            
        # Check if all required CSV files exist
        for file_key in ["entities_csv_path", "properties_csv_path", "types_csv_path", "schema_info_csv_path"]:
            if not os.path.exists(self.options[file_key]):
                if self.options["debug"]:
                    logger.warning(f"CSV file {self.options[file_key]} not found")
                return False
        
        return True

    def extract_schema(self):
        """
        Extract schema information from CSV files or the Fuseki SPARQL endpoint

        Returns:
            dict: Extracted schema info
        """
        if self.csv_available:
            logger.info(f"Extracting schema from CSV files")
            self._extract_from_csv()
        else:
            logger.info(f"Extracting schema from SPARQL endpoint: {self.options['sparql_endpoint']}")
            self._extract_from_sparql()

        return {
            "schemaInfo": self.schema_info,
            "entityExamples": self.entity_examples,
            "prefixes": self.options["prefixes"],
        }

    def _extract_from_csv(self):
        """Extract schema information from CSV files"""
        try:
            # Load properties
            properties_df = pd.read_csv(self.options["properties_csv_path"])
            for _, row in properties_df.iterrows():
                property_info = {
                    "value": row.get("short", ""),
                    "label": row.get("label", ""),
                    "uri": row.get("uri", ""),
                    "domain": row.get("domain", ""),
                    "range": row.get("range", "")
                }
                self.schema_info["properties"].append(property_info)
            
            # Load types
            types_df = pd.read_csv(self.options["types_csv_path"])
            for _, row in types_df.iterrows():
                type_info = {
                    "value": row.get("short", ""),
                    "label": row.get("label", ""),
                    "uri": row.get("uri", "")
                }
                self.schema_info["types"].append(type_info)
            
            # Load schema info (property categories)
            schema_info_df = pd.read_csv(self.options["schema_info_csv_path"])
            # Group by category
            for category, group in schema_info_df.groupby("category"):
                # Find the property info for each property in this category
                for _, row in group.iterrows():
                    prop_short = row.get("property", "")
                    # Find the property info from the properties list
                    prop_info = next((p for p in self.schema_info["properties"] if p["value"] == prop_short), None)
                    if prop_info and category in self.schema_info:
                        self.schema_info[category].append(prop_info)
            
            # Load entity examples
            entities_df = pd.read_csv(self.options["entities_csv_path"])
            # Take a sample of entities for each type
            entity_types = entities_df["type"].unique()
            for type_value in entity_types:
                if not type_value or pd.isna(type_value):
                    continue
                    
                # Get entities of this type
                type_entities = entities_df[entities_df["type"] == type_value]
                # Take a sample
                sample_size = min(20, len(type_entities))
                sample = type_entities.sample(n=sample_size) if sample_size > 0 else type_entities
                
                for _, row in sample.iterrows():
                    entity_info = {
                        "value": row.get("short", ""),
                        "label": row.get("label", ""),
                        "uri": row.get("uri", ""),
                        "type": type_value
                    }
                    self.entity_examples.append(entity_info)
            
            logger.info(f"Loaded schema from CSV files: {len(self.schema_info['properties'])} properties, "
                       f"{len(self.schema_info['types'])} types, {len(self.entity_examples)} entity examples")
            
        except Exception as e:
            logger.error(f"Error loading schema from CSV files: {e}")
            # Fall back to SPARQL extraction
            logger.warning("Falling back to SPARQL extraction")
            self._extract_from_sparql()

    def _extract_from_sparql(self):
        """Extract schema information from SPARQL endpoint"""
        try:
            self.extract_classes()
            self.extract_properties()
            self.extract_property_types()
            self.extract_entity_examples()
        except Exception as e:
            logger.error(f"Error extracting schema from SPARQL: {e}")
            raise e

    def execute_sparql_query(self, query):
        """
        Execute a SPARQL query against the configured endpoint

        Args:
            query (str): SPARQL query to execute

        Returns:
            dict: Query results
        """
        try:
            self.sparql_client.setQuery(query)
            results = self.sparql_client.query().convert()
            return results
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            raise e

    def extract_classes(self):
        """
        Extract classes/types from the knowledge graph
        """
        # Query to find all classes (types) in the graph
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX schema: <https://schema.org/>
        
        SELECT DISTINCT ?type ?label
        WHERE {
          { ?type a rdfs:Class }
          UNION
          { ?type a owl:Class }
          UNION
          { ?s a ?type }
          OPTIONAL { ?type rdfs:label ?label }
        }
        LIMIT 1000
        """

        results = self.execute_sparql_query(query)

        # Process the results
        if results.get("results") and results["results"].get("bindings"):
            for binding in results["results"]["bindings"]:
                type_uri = binding.get("type", {}).get("value")
                if type_uri:
                    # Get label if available
                    label = binding.get("label", {}).get("value")
                    if not label:
                        label = gesis_property_label(type_uri)

                    # Add to schema info
                    self.schema_info["types"].append(
                        {
                            "value": self.shorten_uri(type_uri),
                            "label": label,
                            "uri": type_uri,
                        }
                    )

    def extract_properties(self):
        """
        Extract properties from the knowledge graph
        """
        # Query to find all properties in the graph
        query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        PREFIX schema: <https://schema.org/>
        
        SELECT DISTINCT ?property ?label ?domain ?range
        WHERE {
          { ?property a rdf:Property }
          UNION
          { ?property a owl:ObjectProperty }
          UNION
          { ?property a owl:DatatypeProperty }
          UNION
          { ?s ?property ?o }
          OPTIONAL { ?property rdfs:label ?label }
          OPTIONAL { ?property rdfs:domain ?domain }
          OPTIONAL { ?property rdfs:range ?range }
        }
        LIMIT 1000
        """

        results = self.execute_sparql_query(query)

        # Process the results
        if results.get("results") and results["results"].get("bindings"):
            for binding in results["results"]["bindings"]:
                property_uri = binding.get("property", {}).get("value")
                if property_uri:
                    # Skip rdf:type as it's already handled
                    if (
                        property_uri
                        == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
                    ):
                        continue

                    # Get label, domain, and range if available
                    label = binding.get("label", {}).get("value")
                    domain = binding.get("domain", {}).get("value")
                    range_uri = binding.get("range", {}).get("value")

                    if not label:
                        label = gesis_property_label(property_uri)

                    # Add to schema info
                    self.schema_info["properties"].append(
                        {
                            "value": self.shorten_uri(property_uri),
                            "label": label,
                            "uri": property_uri,
                            "domain": domain,
                            "range": range_uri,
                        }
                    )

    def extract_property_types(self):
        """
        Categorize properties by their range types (numeric, date, text, etc.)
        """
        # For each property, examine its range and sample values to determine its type
        for prop in self.schema_info["properties"]:
            self.categorize_property(prop)

    def categorize_property(self, property_info):
        """
        Categorize a property based on its range and sample values

        Args:
            property_info (dict): Property to categorize
        """
        # First check if the range hints at a type
        if property_info.get("range"):
            # Numeric ranges
            if any(
                t in property_info["range"]
                for t in ["integer", "decimal", "float", "double"]
            ):
                self.add_to_property_category("numericProperties", property_info)
                return

            # Date ranges
            elif any(t in property_info["range"] for t in ["date", "time"]):
                self.add_to_property_category("dateProperties", property_info)
                return

            # Text ranges
            elif any(t in property_info["range"] for t in ["string", "Literal"]):
                self.add_to_property_category("textProperties", property_info)
                return

            # Boolean ranges
            elif "boolean" in property_info["range"]:
                self.add_to_property_category("booleanProperties", property_info)
                return

        # If no range or couldn't categorize by range, check sample values
        property_uri = property_info["uri"]

        # Query to get sample values for this property
        query = f"""
        SELECT ?value
        WHERE {{
          ?s <{property_uri}> ?value .
        }}
        LIMIT 10
        """

        results = self.execute_sparql_query(query)

        if results.get("results") and results["results"].get("bindings"):
            # Count different value types
            numeric_count = 0
            date_count = 0
            bool_count = 0

            for binding in results["results"]["bindings"]:
                value = binding.get("value", {})
                value_type = value.get("type")

                if value_type == "typed-literal":
                    datatype = value.get("datatype", "")

                    if any(
                        t in datatype for t in ["integer", "decimal", "float", "double"]
                    ):
                        numeric_count += 1
                    elif any(t in datatype for t in ["date", "time"]):
                        date_count += 1
                    elif "boolean" in datatype:
                        bool_count += 1

                elif value_type == "literal":
                    value_str = value.get("value", "")

                    # Try to infer from the value
                    try:
                        float(value_str)  # Attempt to convert to number
                        numeric_count += 1
                    except ValueError:
                        if value_str.lower() in ["true", "false"]:
                            bool_count += 1
                        elif self.is_date_string(value_str):
                            date_count += 1

            # Categorize based on the majority type
            total_samples = len(results["results"]["bindings"])
            if numeric_count > 0 and numeric_count >= total_samples / 2:
                self.add_to_property_category("numericProperties", property_info)
            elif date_count > 0 and date_count >= total_samples / 2:
                self.add_to_property_category("dateProperties", property_info)
            elif bool_count > 0 and bool_count >= total_samples / 2:
                self.add_to_property_category("booleanProperties", property_info)
            else:
                self.add_to_property_category("textProperties", property_info)

    def extract_entity_examples(self):
        """
        Extract entity examples for each type in the schema
        """
        for type_info in self.schema_info["types"]:
            self.extract_examples_for_type(type_info)

    def extract_examples_for_type(self, type_info):
        """
        Extract example entities for a specific type

        Args:
            type_info (dict): Information about the entity type
        """
        type_uri = type_info["uri"]

        # Query to find entities of this type
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?entity ?label
        WHERE {{
          ?entity rdf:type <{type_uri}> .
          OPTIONAL {{ ?entity rdfs:label ?label }}
        }}
        LIMIT 20
        """

        results = self.execute_sparql_query(query)

        # Process the results
        if results.get("results") and results["results"].get("bindings"):
            for binding in results["results"]["bindings"]:
                entity_uri = binding.get("entity", {}).get("value")
                if entity_uri:
                    # Get label if available
                    label = binding.get("label", {}).get("value")
                    if not label:
                        label = gesis_entity_label(entity_uri)

                    # Add to entity examples
                    self.entity_examples.append(
                        {
                            "value": self.shorten_uri(entity_uri),
                            "label": label,
                            "uri": entity_uri,
                            "type": type_info["value"],
                        }
                    )

    def add_to_property_category(self, category, property_info):
        """
        Add a property to a specific category

        Args:
            category (str): Category name
            property_info (dict): Property to add
        """
        # Check if property already exists in the category
        if not any(
            p["uri"] == property_info["uri"] for p in self.schema_info[category]
        ):
            self.schema_info[category].append(property_info)

    def is_date_string(self, string):
        """
        Check if a string resembles a date

        Args:
            string (str): String to check

        Returns:
            bool: True if string looks like a date
        """
        # Common date patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD (ISO format)
            r"^\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY
            r"^\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY
            r"^\d{4}$",  # Just a year
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
        if not uri:
            return ""
            
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
        return "\n".join(
            [
                f"PREFIX {prefix}: <{namespace}>"
                for prefix, namespace in self.options["prefixes"].items()
            ]
        )