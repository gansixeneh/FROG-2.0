"""
Example usage of the NL2SPARQL Generator with University Course Data

This example demonstrates how to:
1. Extract schema from a TTL file (final_result.ttl)
2. Generate natural language questions and SPARQL queries
3. Export the dataset to JSON and CSV files
"""

import json
import os
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator

def generate_university_course_dataset(file_path='final_result.ttl'):
    """
    Extract schema from a TTL file and generate question-SPARQL dataset
    
    Args:
        file_path (str): Path to the TTL file
        
    Returns:
        list: Generated dataset
    """
    try:
        print(f"Extracting schema from TTL file: {file_path}")
        
        # Create a schema extractor
        extractor = KGSchemaExtractor()
        
        # Extract schema from the TTL file
        schema = extractor.extract_from_file(file_path, format='turtle')
        
        print(f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties")
        print(f"Found {len(schema['entityExamples'])} entity examples")
        
        # Create categories for better readability
        entity_types = {}
        for type_info in schema['schemaInfo']['types']:
            entity_types[type_info['value']] = type_info['label']
            
        print("\nEntity Types found in the knowledge graph:")
        for value, label in entity_types.items():
            print(f"  - {label} ({value})")
            
        print("\nSample Properties found in the knowledge graph:")
        for i, prop in enumerate(schema['schemaInfo']['properties'][:10]):  # Show first 10 properties
            print(f"  - {prop['label']} ({prop['value']})")
        if len(schema['schemaInfo']['properties']) > 10:
            print(f"  ... and {len(schema['schemaInfo']['properties']) - 10} more")
            
        # Generate dataset using extracted schema
        generator = NL2SPARQLGenerator(schema)
        
        print("\nGenerating question-SPARQL pairs...")
        dataset = generator.generate_dataset(
            size=10,
            complexity_distribution={"basic": 0.6, "intermediate": 0.3, "advanced": 0.1},
            include_variations=True,
            variations_per_question=2
        )
        
        print(f"Generated {len(dataset)} question-SPARQL pairs from extracted schema")
        
        # Sample questions by complexity
        print("\nSample questions by complexity level:")
        
        for complexity in ["basic", "intermediate", "advanced"]:
            sample_questions = [item for item in dataset if item['complexity'] == complexity][:3]
            print(f"\n{complexity.capitalize()} questions:")
            for q in sample_questions:
                print(f"  - {q['question']}")
        
        # Write to files
        output_json_path = 'university_course_dataset.json'
        output_csv_path = 'university_course_dataset.csv'
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_json(dataset))
            
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_csv(dataset))
            
        print(f"\nDataset exported to:")
        print(f"  - JSON: {output_json_path}")
        print(f"  - CSV: {output_csv_path}")
        
        return dataset
    except Exception as e:
        print(f"Error extracting schema from file and generating dataset: {e}")
        raise e

def main():
    """Main function to run the example"""
    try:
        # Check if the TTL file exists
        if os.path.exists('final_result.ttl'):
            dataset = generate_university_course_dataset('final_result.ttl')
            print("\nExample completed successfully!")
        else:
            print("Error: final_result.ttl file not found!")
            print("Please ensure the file is in the current directory.")
    except Exception as e:
        print(f"Error in example: {e}")

if __name__ == "__main__":
    main()