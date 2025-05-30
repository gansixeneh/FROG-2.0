"""
Example usage of the NL2SPARQL Generator with Indonesian Legal Documents Data

This example focuses on generating NL2SPARQL pairs from the data-lex2kg knowledge graph
using a Fuseki server endpoint.
"""

import json
import os
import sys
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator
from property_retrieval import LegalPropertyRetrieval


def generate_legal_document_dataset(
    endpoint_url="http://localhost:3030/modified-lex2kg",
):
    """
    Extract schema from the Fuseki server and generate question-SPARQL dataset

    Args:
        endpoint_url (str): URL of the Fuseki SPARQL endpoint

    Returns:
        list: Generated dataset
    """
    try:
        print(f"Connecting to Fuseki server at: {endpoint_url}")

        # Create a schema extractor that connects to Fuseki
        extractor = KGSchemaExtractor({"debug": True, "sparql_endpoint": endpoint_url})

        # Extract schema from the Fuseki server
        schema = extractor.extract_schema()

        print(
            f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties"
        )
        print(f"Found {len(schema['entityExamples'])} entity examples")

        # Display extracted entity types
        entity_types = {}
        for type_info in schema["schemaInfo"]["types"]:
            entity_types[type_info["value"]] = type_info["label"]

        print("\nEntity Types found in the legal knowledge graph:")
        for value, label in entity_types.items():
            print(f"  - {label} ({value})")

        # Display sample properties
        print("\nSample Properties found in the legal knowledge graph:")
        for i, prop in enumerate(schema["schemaInfo"]["properties"][:10]):
            print(f"  - {prop['label']} ({prop['value']})")
        if len(schema["schemaInfo"]["properties"]) > 10:
            print(f"  ... and {len(schema['schemaInfo']['properties']) - 10} more")

        # Display sample entities
        print("\nSample Entities found in the legal knowledge graph:")
        for i, entity in enumerate(schema["entityExamples"][:10]):
            print(f"  - {entity['label']} ({entity['value']})")
        if len(schema["entityExamples"]) > 10:
            print(f"  ... and {len(schema['entityExamples']) - 10} more")

        print("Numeric properties:", schema["schemaInfo"]["numericProperties"])
        print("Date properties:", schema["schemaInfo"]["dateProperties"])

        # Initialize the property retrieval system for entity/property matching
        print("\nInitializing property retrieval system...")
        try:
            property_retrieval = LegalPropertyRetrieval(
                endpoint_url=endpoint_url + "/query",  # Add /query for SPARQL endpoint
                embedding_model_name="jinaai/jina-embeddings-v3",
                is_local_client=True,
                weaviate_host="localhost",
                weaviate_port=8080
            )
            print("Property retrieval system initialized successfully!")
        except Exception as e:
            print(f"Warning: Could not initialize property retrieval system: {e}")
            print("Continuing without entity/property matching...")
            property_retrieval = None

        # Generate dataset using extracted schema with property retrieval
        generator = NL2SPARQLGenerator(
            schema, 
            endpoint_url=endpoint_url + "/query",
            property_retrieval=property_retrieval
        )

        print("\nGenerating question-SPARQL pairs for legal documents data...")
        dataset = generator.generate_dataset(
            size=200,  # Smaller size for debugging
            complexity_distribution={
                "basic": 0.4,
                "intermediate": 0.3,
                "advanced": 0.3,
            },
            include_variations=False,
            variations_per_question=2,
        )

        print(f"Generated {len(dataset)} question-SPARQL pairs about legal documents")

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
        output_json_path = "legal_documents_dataset.json"
        output_csv_path = "legal_documents_dataset.csv"

        with open(output_json_path, "w", encoding="utf-8") as f:
            f.write(generator.export_json(dataset))

        with open(output_csv_path, "w", encoding="utf-8") as f:
            f.write(generator.export_csv(dataset))

        print(f"\nLegal documents dataset exported to:")
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

        print(f"Error processing legal documents data: {e}")
        print(traceback.format_exc())
        raise e


def main():
    """Main function to run the legal documents example"""
    try:
        # Define the Fuseki endpoint URL
        endpoint_url = "http://localhost:3030/modified-lex2kg"

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

        # Generate dataset from Fuseki endpoint
        dataset = generate_legal_document_dataset(endpoint_url)
        print("\nLegal documents example completed successfully!")
    except Exception as e:
        print(f"Error in legal documents example: {e}")


if __name__ == "__main__":
    main()