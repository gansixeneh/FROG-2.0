"""
Example usage of the Enhanced NL2SPARQL Generator with University Course Data

This example generates NL2SPARQL pairs with more complex query patterns from the final_result.ttl file,
including multi-condition and multi-hop queries.
"""

import json
import os
import sys
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator
from property_retrieval import UniversityPropertyRetrieval
from rdflib import Graph


def generate_university_course_dataset(file_path='final_result.ttl'):
    """
    Extract schema from the university course TTL file and generate question-SPARQL dataset
    with enhanced complexity
    
    Args:
        file_path (str): Path to the TTL file
        
    Returns:
        list: Generated dataset
    """
    try:
        print(f"Extracting schema from university course TTL file: {file_path}")
        
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
            
        print("\nEntity Types found in the university knowledge graph:")
        for value, label in entity_types.items():
            print(f"  - {label} ({value})")
            
        # Display sample properties
        print("\nSample Properties found in the university knowledge graph:")
        for i, prop in enumerate(schema['schemaInfo']['properties'][:10]):
            print(f"  - {prop['label']} ({prop['value']})")
        if len(schema['schemaInfo']['properties']) > 10:
            print(f"  ... and {len(schema['schemaInfo']['properties']) - 10} more")
            
        # Display sample entities
        print("\nSample Entities found in the university knowledge graph:")
        for i, entity in enumerate(schema['entityExamples'][:10]):
            print(f"  - {entity['label']} ({entity['value']})")
        if len(schema['entityExamples']) > 10:
            print(f"  ... and {len(schema['entityExamples']) - 10} more")
        
        print("Numeric properties:", schema["schemaInfo"]["numericProperties"])
        print("Date properties:", schema["schemaInfo"]["dateProperties"])

        # Initialize the university property retrieval system with Weaviate
        print("\nInitializing University Property Retrieval with Weaviate...")
        
        # Define SPARQL queries for entities and properties
        get_entities_query = """
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label
    (REPLACE(STR(?entity), "http://example.org/", "ns1:") AS ?short)
WHERE {
  { 
    ?entity ?predicate ?object. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  UNION
  { 
    ?subject ?predicate ?entity. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  
  OPTIONAL {
    ?entity rdfs:label ?label.
  }
}
"""
        
        get_properties_query = """
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label 
    (REPLACE(STR(?property), "http://example.org/", "ns1:") AS ?short) 
    (REPLACE(REPLACE(STR(?domain), "http://example.org/", "ns1:"), "http://www.w3.org/2000/01/rdf-schema#", "rdfs:") AS ?shortDomain)
    (REPLACE(REPLACE(STR(?range), "http://example.org/", "ns1:"), "http://www.w3.org/2001/XMLSchema#", "xsd:") AS ?shortRange)
WHERE {
  ?subject ?property ?object.
  FILTER(STRSTARTS(STR(?property), STR(ns1:)))
  
  OPTIONAL {
    ?property rdfs:label ?label.
    ?property rdfs:domain ?domain.
    ?property rdfs:range ?range.
  }
}
"""
        
        # Initialize property retrieval system
        property_retrieval = UniversityPropertyRetrieval(
            turtle_file_path=file_path,
            get_entities_query=get_entities_query,
            get_properties_query=get_properties_query,
            embedding_model_name="jinaai/jina-embeddings-v3",
            is_local_client=True,
            weaviate_host="localhost",
            weaviate_port=8080,
        )

        # Generate dataset using extracted schema and the graph from the extractor
        generator = NL2SPARQLGenerator(schema, graph=extractor.graph, property_retrieval=property_retrieval)
        
        print("\nGenerating question-SPARQL pairs for university course data...")
        dataset = generator.generate_dataset(
            size=200,
            complexity_distribution={"basic": 0.4, "intermediate": 0.3, "advanced": 0.3},
            include_variations=False,
            variations_per_question=0
        )
        
        print(f"Generated {len(dataset)} question-SPARQL pairs about university courses")
        
        # Sample questions by complexity
        print("\nSample questions by complexity level:")
        
        for complexity in ["basic", "intermediate", "advanced"]:
            sample_questions = [item for item in dataset if item['complexity'] == complexity][:3]
            print(f"\n{complexity.capitalize()} questions:")
            for q in sample_questions:
                print(f"  - {q['question']}")
                print(f"    SPARQL: {q['sparql'].replace('{', '{{').replace('}', '}}')[:80]}...")
        
        # Write to files
        output_json_path = 'enhanced_university_course_dataset.json'
        output_csv_path = 'enhanced_university_course_dataset.csv'
        
        with open(output_json_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_json(dataset))
            
        with open(output_csv_path, 'w', encoding='utf-8') as f:
            f.write(generator.export_csv(dataset))
            
        print(f"\nEnhanced university course dataset exported to:")
        print(f"  - JSON: {output_json_path}")
        print(f"  - CSV: {output_csv_path}")
        
        return dataset
    except Exception as e:
        import traceback
        print(f"Error processing university course data: {e}")
        print(traceback.format_exc())
        raise e

def main():
    """Main function to run the enhanced university course example"""
    try:
        # Check if the TTL file exists
        if not os.path.exists('final_result.ttl'):
            print("Error: final_result.ttl file not found!")
            print("Please ensure the university course TTL file is in the current directory.")
            sys.exit(1)
            
        # Generate dataset from university course TTL
        dataset = generate_university_course_dataset('final_result.ttl')
        print("\nEnhanced university course example completed successfully!")
    except Exception as e:
        print(f"Error in university course example: {e}")

if __name__ == "__main__":
    main()