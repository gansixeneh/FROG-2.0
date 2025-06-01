# gesis/example_usage.py
"""
Example usage of the NL2SPARQL Generator with GESIS Knowledge Graph Data

This example focuses on generating NL2SPARQL pairs from the GESIS knowledge graph
using a Fuseki server endpoint and CSV files for faster processing.
Enhanced with entity/property matching using Weaviate.
"""

import json
import os
import sys
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator
from property_retrieval import GesisPropertyRetrieval
from extract_entities_properties import GesisKGExtractor


def check_and_extract_kg_data(endpoint_url="http://localhost:3030/gesis", force_extract=False):
    """
    Check if CSV files exist for the KG data, extract them if they don't exist or if forced

    Args:
        endpoint_url (str): URL of the Fuseki SPARQL endpoint
        force_extract (bool): Force extraction even if CSV files exist

    Returns:
        dict: Paths to the extracted CSV files
    """
    # Define CSV file paths
    csv_paths = {
        "entities_csv_path": "data/gesis_entities.csv",
        "properties_csv_path": "data/gesis_properties.csv",
        "schema_info_csv_path": "data/gesis_schema_info.csv"
    }
    
    # Check if files exist
    files_exist = all(os.path.exists(path) for path in csv_paths.values())
    
    if not files_exist or force_extract:
        print("Extracting KG data to CSV files...")
        # Create extractor and extract data
        extractor = GesisKGExtractor("http://localhost:3030/gesis/query")
        extracted_paths = extractor.extract_and_save_all()
        print("KG data extraction completed!")
        return extracted_paths
    else:
        print("Using existing CSV files for KG data")
        return csv_paths


def generate_gesis_kg_dataset(endpoint_url="http://localhost:3030/gesis", use_csv=True, force_extract=False):
    """
    Extract schema from the Fuseki server (or CSV files) and generate question-SPARQL dataset for GESIS KG

    Args:
        endpoint_url (str): URL of the Fuseki SPARQL endpoint
        use_csv (bool): Whether to use CSV files for schema extraction
        force_extract (bool): Force extraction of CSV files even if they already exist

    Returns:
        list: Generated dataset
    """
    try:
        print(f"Connecting to Fuseki server at: {endpoint_url}")
        
        # Check if CSV files exist and extract them if needed
        if use_csv:
            csv_paths = check_and_extract_kg_data(endpoint_url, force_extract)
            print(f"Using CSV files for schema extraction: {csv_paths}")
        else:
            csv_paths = {}

        # Create a schema extractor
        extractor_options = {
            "debug": True, 
            "sparql_endpoint": endpoint_url,
            "use_csv": use_csv
        }
        
        # Add CSV paths if using CSV files
        if use_csv:
            extractor_options.update(csv_paths)
            
        extractor = KGSchemaExtractor(extractor_options)

        # Extract schema
        schema = extractor.extract_schema()

        print(
            f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties"
        )
        print(f"Found {len(schema['entityExamples'])} entity examples")

        # Display extracted entity types
        entity_types = {}
        for type_info in schema["schemaInfo"]["types"]:
            entity_types[type_info["value"]] = type_info["label"]

        print("\nEntity Types found in the GESIS knowledge graph:")
        for value, label in entity_types.items():
            print(f"  - {label} ({value})")

        # Display sample properties
        print("\nSample Properties found in the GESIS knowledge graph:")
        for i, prop in enumerate(schema["schemaInfo"]["properties"][:10]):
            print(f"  - {prop['label']} ({prop['value']})")
        if len(schema["schemaInfo"]["properties"]) > 10:
            print(f"  ... and {len(schema['schemaInfo']['properties']) - 10} more")

        # Display sample entities
        print("\nSample Entities found in the GESIS knowledge graph:")
        for i, entity in enumerate(schema["entityExamples"][:10]):
            print(f"  - {entity['label']} ({entity['value']})")
        if len(schema["entityExamples"]) > 10:
            print(f"  ... and {len(schema['entityExamples']) - 10} more")

        print("Numeric properties:", [p["value"] for p in schema["schemaInfo"]["numericProperties"]])
        print("Date properties:", [p["value"] for p in schema["schemaInfo"]["dateProperties"]])

        # Initialize the property retrieval system for entity/property matching
        print("\nInitializing property retrieval system...")
        try:
            raise ImportError("Simulating import error for testing purposes")
            property_retrieval = GesisPropertyRetrieval(
                endpoint_url="http://localhost:3030/gesis/query",  # Add /query for SPARQL endpoint
                embedding_model_name="jinaai/jina-embeddings-v3",
                is_local_client=True,
                weaviate_host="localhost",
                weaviate_port=8080,
                # Use CSV file paths if available
                entities_csv_path=csv_paths.get("entities_csv_path") if use_csv else None,
                properties_csv_path=csv_paths.get("properties_csv_path") if use_csv else None
            )
            print("Property retrieval system initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize property retrieval system: {e}")
            print("Continuing without entity/property matching...")
            property_retrieval = None

        # Generate dataset using extracted schema with property retrieval
        generator = NL2SPARQLGenerator(
            schema, 
            endpoint_url="http://localhost:3030/gesis/query",
            property_retrieval=property_retrieval
        )

        print("\nGenerating question-SPARQL pairs for GESIS knowledge graph...")
        dataset = generator.generate_dataset(
            size=200,  # Smaller size for debugging
            complexity_distribution={
                "basic": 0.4,
                "intermediate": 0.3,
                "advanced": 0.3,
            },
            include_variations=True,
            variations_per_question=2
        )

        print(f"Generated {len(dataset)} question-SPARQL pairs about scholarly resources")

        # Sample questions by complexity
        print("\nSample questions by complexity level:")

        for complexity in ["basic", "intermediate", "advanced"]:
            sample_questions = [
                item for item in dataset if item["complexity"] == complexity
            ][:3]
            print(f"\n{complexity.capitalize()} questions:")
            for q in sample_questions:
                print(f"  - {q['question']}")
                print(
                    f"    SPARQL: {q['sparql'].replace('{', '{{').replace('}', '}}')[:80]}..."
                )
                print(f"    Entities matches: {len(q.get('entities_matches', []))}")
                print(f"    Properties matches: {len(q.get('properties_matches', []))}")

        # Write to files
        output_json_path = "gesis_dataset.json"
        output_csv_path = "gesis_dataset.csv"

        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(generator.export_json(dataset))

        with open(output_csv_path, "w", encoding="utf-8") as f:
            f.write(generator.export_csv(dataset))

        print(f"\nGESIS dataset exported to:")
        print(f"  - JSON: {output_json_path}")
        print(f"  - CSV: {output_csv_path}")

        # Clean up property retrieval system
        if property_retrieval:
            try:
                property_retrieval.close()
                print("Property retrieval system closed.")
            except Exception as e:
                print(f"Warning: Error closing property retrieval system: {e}")

        return dataset
    except Exception as e:
        import traceback

        print(f"Error processing GESIS data: {e}")
        print(traceback.format_exc())
        raise e


def main():
    """Main function to run the GESIS example"""
    try:
        # Define the Fuseki endpoint URL
        endpoint_url = "http://localhost:3030"
        
        # Check if Fuseki server is accessible
        import requests

        try:
            response = requests.get(endpoint_url)
            if response.status_code != 200:
                print(
                    f"Warning: Fuseki endpoint at {endpoint_url} returned status code {response.status_code}"
                )
                print("Make sure the Fuseki server is running.")
                proceed = input("Do you want to proceed anyway? (y/n): ")
                if proceed.lower() != "y":
                    sys.exit(1)
        except requests.exceptions.RequestException:
            print(f"Warning: Could not connect to Fuseki endpoint at {endpoint_url}")
            print("Make sure the Fuseki server is running.")
            proceed = input("Do you want to proceed anyway? (y/n): ")
            if proceed.lower() != "y":
                sys.exit(1)

        # Check if Weaviate is running
        try:
            import requests
            weaviate_response = requests.get("http://localhost:8080/v1/.well-known/ready")
            if weaviate_response.status_code != 200:
                print("Warning: Weaviate server may not be running at localhost:8080")
                print("Entity/property matching may not work properly.")
                proceed = input("Do you want to proceed anyway? (y/n): ")
                if proceed.lower() != "y":
                    sys.exit(1)
        except requests.exceptions.RequestException:
            print("Warning: Could not connect to Weaviate at localhost:8080")
            print("Entity/property matching may not work properly.")
            proceed = input("Do you want to proceed anyway? (y/n): ")
            if proceed.lower() != "y":
                sys.exit(1)
        
        # Ask if we should use CSV files
        use_csv = True  # Default to using CSV for efficiency
        force_extract = False
        
        if os.path.exists("data/gesis_entities.csv"):
            print("CSV files found. Will use existing files.")
        else:
            print("No CSV files found. Will extract data from SPARQL endpoint.")
        
        # Generate dataset
        dataset = generate_gesis_kg_dataset(endpoint_url, use_csv=use_csv, force_extract=force_extract)
        print("\nGESIS example completed successfully!")
    except Exception as e:
        print(f"Error in GESIS example: {e}")


if __name__ == "__main__":
    main()