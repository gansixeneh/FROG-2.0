# extract_entities_properties.py
"""
Extract entities, properties and types from the GESIS Knowledge Graph
and store them in CSV files for faster access.

This script connects to a Fuseki SPARQL endpoint, extracts all entities,
properties, and type information, and saves them to CSV files.
"""

import pandas as pd
import os
import sys
import logging
import requests
import re
from SPARQLWrapper import SPARQLWrapper, JSON
from kg_schema_extractor import separate_camel_case

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GesisKGExtractor:
    """
    Extracts entities, properties, and schema information from the GESIS Knowledge Graph
    and stores them in CSV files for faster access.
    """
    
    # SPARQL query to get all entities with their schema:name
    get_entities_query = """
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/>
    PREFIX disco: <https://rdf-vocabulary.ddialliance.org/discovery.html#>
    PREFIX nfdicore: <https://nfdi.fiz-karlsruhe.de/ontology/>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

    SELECT DISTINCT ?entity ?type ?name
    WHERE {
      { 
        ?entity ?predicate ?object. 
        OPTIONAL { ?entity rdf:type ?type }
        OPTIONAL { ?entity schema:name ?name }
        FILTER(isIRI(?entity))
      }
    }
    """
    
    # SPARQL query to get all properties
    get_properties_query = """
    PREFIX schema: <https://schema.org/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/>
    PREFIX disco: <https://rdf-vocabulary.ddialliance.org/discovery.html#>
    PREFIX nfdicore: <https://nfdi.fiz-karlsruhe.de/ontology/>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>

    SELECT DISTINCT ?property
    WHERE {
    ?subject ?property ?object.
    }
    """
    
    # Known prefixes for URI shortening
    prefixes = {
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf:",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs:",
        "http://www.w3.org/2002/07/owl#": "owl:",
        "http://www.w3.org/2001/XMLSchema#": "xsd:",
        "https://schema.org/": "schema:",
        "https://data.gesis.org/gesiskg/schema/": "gesiskg:",
        "https://data.gesis.org/gesiskg/": "gesis:",
        "https://rdf-vocabulary.ddialliance.org/discovery.html#": "disco:",
        "https://nfdi.fiz-karlsruhe.de/ontology/": "nfdicore:",
        "http://www.w3.org/2004/02/skos/core#": "skos:",
        "http://rdfs.org/ns/void#": "void:"
    }
    
    def __init__(self, endpoint_url="http://localhost:3030/gesis/query", output_dir="."):
        """
        Initialize the extractor with a SPARQL endpoint and output directory
        
        Args:
            endpoint_url (str): URL of the Fuseki SPARQL endpoint
            output_dir (str): Directory where CSV files will be saved
        """
        self.endpoint_url = endpoint_url
        self.output_dir = output_dir
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize SPARQL client
        self.sparql_client = SPARQLWrapper(endpoint_url)
        self.sparql_client.setReturnFormat(JSON)
        
        # Define CSV file paths
        self.entities_csv_path = os.path.join(output_dir, "gesis_entities.csv")
        self.properties_csv_path = os.path.join(output_dir, "gesis_properties.csv")
        self.types_csv_path = os.path.join(output_dir, "gesis_types.csv")
        self.schema_info_csv_path = os.path.join(output_dir, "gesis_schema_info.csv")
    
    def execute_sparql_query(self, query):
        """Execute a SPARQL query against the configured endpoint"""
        try:
            print(f"Executing SPARQL query: {query}")
            self.sparql_client.setQuery(query)
            results = self.sparql_client.query().convert()
            print("SPARQL query executed successfully")
            return results
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            raise e
    
    def get_property_label(self, uri):
        """
        Extract property label from URI by taking the last part after '/' 
        and converting from camelCase to space-separated words
        
        Args:
            uri (str): Property URI
            
        Returns:
            str: Human-readable property label
        """
        try:
            # Get the last part of the URI
            last_part = uri.split('/')[-1]
            
            # If there are fragments, get the part after #
            if '#' in last_part:
                last_part = last_part.split('#')[-1]
            
            # Convert camelCase to words with spaces
            return separate_camel_case(last_part)
        except Exception as e:
            logger.error(f"Error extracting property label from {uri}: {e}")
            return uri
    
    def shorten_uri(self, uri):
        """Shorten a URI using known prefixes"""
        if not uri:
            return ""
            
        for namespace, prefix in self.prefixes.items():
            if uri.startswith(namespace):
                return prefix + uri[len(namespace):]
        
        return uri
    
    def extract_entities(self):
        """Extract entities from the SPARQL endpoint"""
        try:
            logger.info("Extracting entities from SPARQL endpoint...")
            results = self.execute_sparql_query(self.get_entities_query)
            logger.info("Results received from SPARQL endpoint")
            entities_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                total_entities = len(results["results"]["bindings"])
                logger.info(f"Processing {total_entities} entities...")
                
                for i, binding in enumerate(results["results"]["bindings"]):
                    if i % 100 == 0:
                        logger.info(f"Processed {i}/{total_entities} entities")
                    
                    entity_uri = binding.get("entity", {}).get("value")
                    entity_type = binding.get("type", {}).get("value")
                    entity_name = binding.get("name", {}).get("value")
                    
                    if entity_uri:
                        # Use name from query or generate a default label
                        label = entity_name if entity_name else entity_uri.split('/')[-1]
                        
                        # Generate short form using prefixes
                        short = self.shorten_uri(entity_uri)
                        short_type = self.shorten_uri(entity_type) if entity_type else ""
                        
                        entities_data.append({
                            'label': label,
                            'short': short,
                            'uri': entity_uri,
                            'type': short_type
                        })
            
            df = pd.DataFrame(entities_data)
            logger.info(f"Extracted {len(df)} entities from SPARQL endpoint")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return pd.DataFrame(columns=['label', 'short', 'uri', 'type'])
    
    def extract_properties(self):
        """Extract properties from the SPARQL endpoint"""
        try:
            logger.info("Extracting properties from SPARQL endpoint...")
            results = self.execute_sparql_query(self.get_properties_query)
            logger.info("Results received from SPARQL endpoint")
            properties_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                total_properties = len(results["results"]["bindings"])
                logger.info(f"Processing {total_properties} properties...")
                
                for i, binding in enumerate(results["results"]["bindings"]):
                    if i % 100 == 0:
                        logger.info(f"Processed {i}/{total_properties} properties")
                    
                    property_uri = binding.get("property", {}).get("value")
                    
                    if property_uri:
                        # Get label by extracting from URI and formatting
                        label = self.get_property_label(property_uri)
                        
                        # Generate short form using prefixes
                        short = self.shorten_uri(property_uri)
                        
                        properties_data.append({
                            'label': label,
                            'short': short,
                            'uri': property_uri
                        })
            
            df = pd.DataFrame(properties_data)
            logger.info(f"Extracted {len(df)} properties from SPARQL endpoint")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting properties: {e}")
            return pd.DataFrame(columns=['label', 'short', 'uri'])
    
    def extract_types(self):
        """Extract types/classes from the SPARQL endpoint"""
        try:
            logger.info("Extracting types from SPARQL endpoint...")
            results = self.execute_sparql_query(self.get_types_query)
            logger.info("Results received from SPARQL endpoint")
            types_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                total_types = len(results["results"]["bindings"])
                logger.info(f"Processing {total_types} types...")
                
                for i, binding in enumerate(results["results"]["bindings"]):
                    if i % 100 == 0:
                        logger.info(f"Processed {i}/{total_types} types")
                    
                    type_uri = binding.get("type", {}).get("value")
                    
                    if type_uri:
                        # Get name if available or extract from URI
                        label = binding.get("name", {}).get("value")
                        if not label:
                            label = type_uri.split('/')[-1]
                        
                        # Generate short form using prefixes
                        short = self.shorten_uri(type_uri)
                        
                        types_data.append({
                            'label': label,
                            'short': short,
                            'uri': type_uri
                        })
            
            df = pd.DataFrame(types_data)
            logger.info(f"Extracted {len(df)} types from SPARQL endpoint")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting types: {e}")
            return pd.DataFrame(columns=['label', 'short', 'uri'])
    
    def extract_property_types(self):
        """
        Categorize properties by their range types (numeric, date, text, etc.)
        """
        logger.info("Categorizing properties by type...")
        properties_df = pd.read_csv(self.properties_csv_path)
        
        # Initialize categories
        numeric_properties = []
        date_properties = []
        text_properties = []
        boolean_properties = []
        
        # Process each property
        for _, prop in properties_df.iterrows():
            property_uri = prop['uri']
            range_uri = prop.get('range', '')
            
            # First check if the range hints at a type
            if range_uri:
                # Numeric ranges
                if any(t in range_uri for t in ["integer", "decimal", "float", "double"]):
                    numeric_properties.append(prop['short'])
                    continue
                
                # Date ranges
                elif any(t in range_uri for t in ["date", "time"]):
                    date_properties.append(prop['short'])
                    continue
                
                # Text ranges
                elif any(t in range_uri for t in ["string", "Literal"]):
                    text_properties.append(prop['short'])
                    continue
                
                # Boolean ranges
                elif "boolean" in range_uri:
                    boolean_properties.append(prop['short'])
                    continue
            
            # If no range or couldn't categorize by range, check sample values
            query = f"""
            SELECT ?value
            WHERE {{
              ?s <{property_uri}> ?value .
            }}
            LIMIT 10
            """
            
            try:
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
                            
                            if any(t in datatype for t in ["integer", "decimal", "float", "double"]):
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
                        numeric_properties.append(prop['short'])
                    elif date_count > 0 and date_count >= total_samples / 2:
                        date_properties.append(prop['short'])
                    elif bool_count > 0 and bool_count >= total_samples / 2:
                        boolean_properties.append(prop['short'])
                    else:
                        text_properties.append(prop['short'])
            except Exception as e:
                logger.warning(f"Error categorizing property {property_uri}: {e}")
                # Default to text property
                text_properties.append(prop['short'])
        
        # Create schema info dataframe
        schema_info = {
            'numericProperties': numeric_properties,
            'dateProperties': date_properties,
            'textProperties': text_properties,
            'booleanProperties': boolean_properties
        }
        
        # Save schema info to CSV
        with open(self.schema_info_csv_path, 'w') as f:
            f.write(f"category,property\n")
            for category, props in schema_info.items():
                for prop in props:
                    f.write(f"{category},{prop}\n")
        
        logger.info(f"Categorized properties: numeric={len(numeric_properties)}, date={len(date_properties)}, "
                   f"text={len(text_properties)}, boolean={len(boolean_properties)}")
    
    def is_date_string(self, string):
        """
        Check if a string resembles a date

        Args:
            string (str): String to check

        Returns:
            bool: True if string looks like a date
        """
        import re
        # Common date patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}",  # YYYY-MM-DD (ISO format)
            r"^\d{2}/\d{2}/\d{4}",  # DD/MM/YYYY
            r"^\d{2}-\d{2}-\d{4}",  # DD-MM-YYYY
            r"^\d{4}$",  # Just a year
        ]

        return any(re.match(pattern, string) for pattern in date_patterns)
    
    def extract_and_save_all(self):
        """Extract all data and save to CSV files"""
        # Extract and save entities
        logger.info("Extracting and saving entities...")
        entities_df = self.extract_entities()
        entities_df.to_csv(self.entities_csv_path, index=False)
        logger.info(f"Saved {len(entities_df)} entities to {self.entities_csv_path}")
        
        # Extract and save properties
        logger.info("Extracting and saving properties...")
        properties_df = self.extract_properties()
        properties_df.to_csv(self.properties_csv_path, index=False)
        logger.info(f"Saved {len(properties_df)} properties to {self.properties_csv_path}")
        
        # Categorize properties and save schema info
        logger.info("Categorizing properties and saving schema info...")
        self.extract_property_types()
        logger.info(f"Saved schema info to {self.schema_info_csv_path}")
        
        return {
            "entities_path": self.entities_csv_path,
            "properties_path": self.properties_csv_path,
            "schema_info_path": self.schema_info_csv_path
        }


def main():
    """Main function to run the extraction process"""
    try:
        # Define the Fuseki endpoint URL
        endpoint_url = "http://localhost:3030/gesis/query"
        
        # Check if Fuseki server is accessible
        try:
            response = requests.get(endpoint_url.replace("/query", ""))
            if response.status_code != 200:
                logger.warning(f"Warning: Fuseki endpoint at {endpoint_url} returned status code {response.status_code}")
                logger.warning("Make sure the Fuseki server is running.")
                proceed = input("Do you want to proceed anyway? (y/n): ")
                if proceed.lower() != "y":
                    sys.exit(1)
        except requests.exceptions.RequestException:
            logger.warning(f"Warning: Could not connect to Fuseki endpoint at {endpoint_url}")
            logger.warning("Make sure the Fuseki server is running.")
            proceed = input("Do you want to proceed anyway? (y/n): ")
            if proceed.lower() != "y":
                sys.exit(1)
        
        # Create extractor and extract data
        extractor = GesisKGExtractor(endpoint_url)
        file_paths = extractor.extract_and_save_all()
        
        logger.info("Extraction completed successfully!")
        logger.info(f"Files saved to:")
        for key, path in file_paths.items():
            logger.info(f"  - {key}: {path}")
        
    except Exception as e:
        logger.error(f"Error in extraction process: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()