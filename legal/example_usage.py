"""
Example usage of the NL2SPARQL Generator with Indonesian Legal Documents Data

This example focuses on generating NL2SPARQL pairs from the data-lex2kg knowledge graph.
"""

import json
import os
import sys
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator

def generate_legal_document_dataset(file_path='data-lex2kg.ttl'):
    """
    Extract schema from the legal document TTL file and generate question-SPARQL dataset
    
    Args:
        file_path (str): Path to the TTL file
        
    Returns:
        list: Generated dataset
    """
    try:
        print(f"Extracting schema from legal document TTL file: {file_path}")
        
        # Create a schema extractor with debugging enabled
        extractor = KGSchemaExtractor({"debug": True})
        
        # Extract schema from the TTL file
        schema = extractor.extract_from_file(file_path, format='turtle')
        
        print(f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties")
        print(f"Found {len(schema['entityExamples'])} entity examples")
        
        # Display extracted entity types
        entity_types = {}
        for type_info in schema['schemaInfo']['types']:
            entity_types[type_info['value']] = type_info['label']
            
        print("\nEntity Types found in the legal knowledge graph:")
        for value, label in entity_types.items():
            print(f"  - {label} ({value})")
            
        # Display sample properties
        print("\nSample Properties found in the legal knowledge graph:")
        for i, prop in enumerate(schema['schemaInfo']['properties'][:10]):
            print(f"  - {prop['label']} ({prop['value']})")
        if len(schema['schemaInfo']['properties']) > 10:
            print(f"  ... and {len(schema['schemaInfo']['properties']) - 10} more")
            
        # Display sample entities
        print("\nSample Entities found in the legal knowledge graph:")
        for i, entity in enumerate(schema['entityExamples'][:10]):
            print(f"  - {entity['label']} ({entity['value']})")
        if len(schema['entityExamples']) > 10:
            print(f"  ... and {len(schema['entityExamples']) - 10} more")
        
        print("Numeric properties:", schema["schemaInfo"]["numericProperties"])
        print("Date properties:", schema["schemaInfo"]["dateProperties"])

        # Generate dataset using extracted schema
        generator = NL2SPARQLGenerator(schema)
        
        print("\nGenerating question-SPARQL pairs for legal documents data...")
        dataset = generator.generate_dataset(
            size=100,  # Smaller size for debugging
            complexity_distribution={"basic": 0.3, "intermediate": 0.3, "advanced": 0.4},
            include_variations=False,
            variations_per_question=2
        )
        
        print(f"Generated {len(dataset)} question-SPARQL pairs about legal documents")
        
        # Sample questions by complexity
        print("\nSample questions by complexity level:")
        
        for complexity in ["basic", "intermediate", "advanced"]:
            sample_questions = [item for item in dataset if item['complexity'] == complexity][:3]
            print(f"\n{complexity.capitalize()} questions:")
            for q in sample_questions:
                print(f"  - {q['question']}")
                print(f"    SPARQL: {q['sparql'].replace('{', '{{').replace('}', '}}')[:80]}...")
        
        # Write to files
        output_json_path = 'legal_documents_dataset.json'
        output_csv_path = 'legal_documents_dataset.csv'
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_json(dataset))
            
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_csv(dataset))
            
        print(f"\nLegal documents dataset exported to:")
        print(f"  - JSON: {output_json_path}")
        print(f"  - CSV: {output_csv_path}")
        
        return dataset
    except Exception as e:
        import traceback
        print(f"Error processing legal documents data: {e}")
        print(traceback.format_exc())
        raise e

def main():
    """Main function to run the legal documents example"""
    try:
        # Check if the TTL file exists
        if not os.path.exists('data-lex2kg.ttl'):
            print("Warning: data-lex2kg.ttl file not found!")
            print("This script expects the legal knowledge graph TTL file to be in the current directory.")
            print("You can continue but will need to provide the correct path to the TTL file.")
            
            # Ask for the path to the TTL file
            file_path = input("Please enter the path to your legal knowledge graph TTL file (or press Enter to exit): ")
            if not file_path:
                sys.exit(1)
            if not os.path.exists(file_path):
                print(f"Error: File {file_path} not found!")
                sys.exit(1)
        else:
            file_path = 'data-lex2kg.ttl'
            
        # Generate dataset from legal documents TTL
        dataset = generate_legal_document_dataset(file_path)
        print("\nLegal documents example completed successfully!")
    except Exception as e:
        print(f"Error in legal documents example: {e}")

if __name__ == "__main__":
    main()