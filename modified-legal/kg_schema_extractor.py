"""
Knowledge Graph Schema Extractor - Modified for Fuseki Server Integration

This utility has been modified to extract schema information from a Fuseki server.
"""

import requests
import json
import re
from urllib.parse import urlencode
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON


def separate_camel_case(text):
    """
    Separate camelCase text into words
    """
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def legal_entity_label(url):
    """
    Generate a human-readable label from a legal entity URL
    """
    parts = url.strip("/").split("/")
    transformed_parts = []

    month_mapping = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember",
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

    return " ".join(transformed_parts)


def legal_property_label(x):
    """
    Generate a human-readable label from a legal property
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()


class KGSchemaExtractor:
    """
    Extract schema information from the legal document knowledge graph using Fuseki server.
    """

    def __init__(self, options=None):
        """
        Initialize a new schema extractor

        Args:
            options (dict): Configuration options
        """
        self.options = {
            "sparql_endpoint": "http://localhost:3030/legal",
            "sample_size": 1000,
            "debug": False,  # Debug flag
            "prefixes": {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
                "owl": "http://www.w3.org/2002/07/owl#",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "lex2kg-o": "https://example.org/lex2kg/ontology/",  # Added legal ontology prefix
            },
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

        # Initialize the SPARQL client
        self.sparql_client = SPARQLWrapper(self.options["sparql_endpoint"])
        self.sparql_client.setReturnFormat(JSON)

    def extract_schema(self):
        """
        Extract schema information from the Fuseki SPARQL endpoint

        Returns:
            dict: Extracted schema info
        """
        print(
            f"Extracting schema from SPARQL endpoint: {self.options['sparql_endpoint']}"
        )

        try:
            self.extract_classes()
            self.extract_properties()
            self.extract_property_types()
            self.extract_entity_examples()

            return {
                "schemaInfo": self.schema_info,
                "entityExamples": self.entity_examples,
                "prefixes": self.options["prefixes"],
            }
        except Exception as e:
            print(f"Error extracting schema: {e}")
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
            print(f"Error executing SPARQL query: {e}")
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
                        label = legal_property_label(type_uri)

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
                        label = legal_property_label(property_uri)

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
                        label = legal_entity_label(entity_uri)

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
        # Date patterns for Indonesian legal documents
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
