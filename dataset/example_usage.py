"""
Example usage of the NL2SPARQL Generator

This example demonstrates how to use the generator with:
1. DBpedia knowledge graph schema
2. Wikidata knowledge graph schema
3. Custom domain-specific knowledge graph
"""

import json
import os
from kg_schema_extractor import KGSchemaExtractor
from nl2sparql_generator import NL2SPARQLGenerator

# Example 1: Using the generator with DBpedia
def generate_dbpedia_dataset():
    print("Generating DBpedia question-SPARQL dataset...")
    
    dbpedia_config = {
        "prefixes": {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'dbo': 'http://dbpedia.org/ontology/',
            'dbr': 'http://dbpedia.org/resource/',
            'dbp': 'http://dbpedia.org/property/',
            'xsd': 'http://www.w3.org/2001/XMLSchema#'
        },
        "entityExamples": [
            {"value": "dbr:Berlin", "label": "Berlin", "uri": "http://dbpedia.org/resource/Berlin"},
            {"value": "dbr:Paris", "label": "Paris", "uri": "http://dbpedia.org/resource/Paris"},
            {"value": "dbr:Germany", "label": "Germany", "uri": "http://dbpedia.org/resource/Germany"},
            {"value": "dbr:France", "label": "France", "uri": "http://dbpedia.org/resource/France"},
            {"value": "dbr:Leonardo_da_Vinci", "label": "Leonardo da Vinci", "uri": "http://dbpedia.org/resource/Leonardo_da_Vinci"},
            {"value": "dbr:Mona_Lisa", "label": "Mona Lisa", "uri": "http://dbpedia.org/resource/Mona_Lisa"}
        ],
        "schemaInfo": {
            "properties": [
                {"value": "dbo:capital", "label": "capital", "uri": "http://dbpedia.org/ontology/capital"},
                {"value": "dbo:country", "label": "country", "uri": "http://dbpedia.org/ontology/country"},
                {"value": "dbo:populationTotal", "label": "population", "uri": "http://dbpedia.org/ontology/populationTotal"},
                {"value": "dbo:author", "label": "author", "uri": "http://dbpedia.org/ontology/author"},
                {"value": "dbo:artist", "label": "artist", "uri": "http://dbpedia.org/ontology/artist"}
            ],
            "types": [
                {"value": "dbo:City", "label": "City", "uri": "http://dbpedia.org/ontology/City"},
                {"value": "dbo:Country", "label": "Country", "uri": "http://dbpedia.org/ontology/Country"},
                {"value": "dbo:Person", "label": "Person", "uri": "http://dbpedia.org/ontology/Person"}
            ],
            "numericProperties": [
                {"value": "dbo:populationTotal", "label": "population", "uri": "http://dbpedia.org/ontology/populationTotal"}
            ],
            "dateProperties": [
                {"value": "dbo:foundingDate", "label": "founding date", "uri": "http://dbpedia.org/ontology/foundingDate"},
                {"value": "dbo:birthDate", "label": "birth date", "uri": "http://dbpedia.org/ontology/birthDate"}
            ]
        }
    }

    generator = NL2SPARQLGenerator(dbpedia_config)
    
    # Generate a small dataset
    dataset = generator.generate_dataset(
        size=100,
        complexity_distribution={"basic": 0.5, "intermediate": 0.3, "advanced": 0.15, "expert": 0.05},
        include_variations=True,
        variations_per_question=2
    )
    
    print(f"Generated {len(dataset)} question-SPARQL pairs")
    
    # Export to different formats
    json_output = generator.export_json(dataset)
    csv_output = generator.export_csv(dataset)
    
    # Write to files
    with open('dbpedia_dataset.json', 'w', encoding='utf-8') as f:
        f.write(json_output)
    
    with open('dbpedia_dataset.csv', 'w', encoding='utf-8') as f:
        f.write(csv_output)
    
    print("Dataset exported to JSON and CSV files")
    
    return dataset

# Example 2: Extract schema from SPARQL endpoint and generate dataset
def extract_and_generate():
    try:
        print("Extracting schema from DBpedia endpoint...")
        
        extractor = KGSchemaExtractor()
        schema = extractor.extract_from_endpoint('https://dbpedia.org/sparql')
        
        print(f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties")
        
        # Generate dataset using extracted schema
        generator = NL2SPARQLGenerator(schema)
        
        dataset = generator.generate_dataset(
            size=100,
            complexity_distribution={"basic": 0.6, "intermediate": 0.3, "advanced": 0.1}
        )
        
        print(f"Generated {len(dataset)} question-SPARQL pairs from extracted schema")
        
        # Write to file
        with open('extracted_dataset.json', 'w', encoding='utf-8') as f:
            f.write(generator.export_json(dataset))
        
        return dataset
    except Exception as e:
        print(f"Error extracting schema and generating dataset: {e}")
        raise e

# Example 3: Generate dataset with custom domain-specific templates
def generate_biomedical_dataset():
    print("Generating biomedical question-SPARQL dataset...")
    
    # Configuration for a biomedical knowledge graph
    biomedical_config = {
        "prefixes": {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
            'owl': 'http://www.w3.org/2002/07/owl#',
            'xsd': 'http://www.w3.org/2001/XMLSchema#',
            'bio': 'http://example.org/biomedical/',
            'disease': 'http://example.org/biomedical/disease/',
            'drug': 'http://example.org/biomedical/drug/',
            'gene': 'http://example.org/biomedical/gene/'
        },
        "entityExamples": [
            {"value": "disease:D001249", "label": "Alzheimer's Disease", "uri": "http://example.org/biomedical/disease/D001249"},
            {"value": "disease:D003924", "label": "Diabetes Mellitus", "uri": "http://example.org/biomedical/disease/D003924"},
            {"value": "drug:DB00619", "label": "Aspirin", "uri": "http://example.org/biomedical/drug/DB00619"},
            {"value": "drug:DB00945", "label": "Insulin", "uri": "http://example.org/biomedical/drug/DB00945"},
            {"value": "gene:G001", "label": "BRCA1", "uri": "http://example.org/biomedical/gene/G001"},
            {"value": "gene:G002", "label": "TP53", "uri": "http://example.org/biomedical/gene/G002"}
        ],
        "schemaInfo": {
            "properties": [
                {"value": "bio:treats", "label": "treats", "uri": "http://example.org/biomedical/treats"},
                {"value": "bio:causedBy", "label": "caused by", "uri": "http://example.org/biomedical/causedBy"},
                {"value": "bio:associatedWith", "label": "associated with", "uri": "http://example.org/biomedical/associatedWith"},
                {"value": "bio:hasSymptom", "label": "has symptom", "uri": "http://example.org/biomedical/hasSymptom"}
            ],
            "types": [
                {"value": "bio:Disease", "label": "Disease", "uri": "http://example.org/biomedical/Disease"},
                {"value": "bio:Drug", "label": "Drug", "uri": "http://example.org/biomedical/Drug"},
                {"value": "bio:Gene", "label": "Gene", "uri": "http://example.org/biomedical/Gene"},
                {"value": "bio:Protein", "label": "Protein", "uri": "http://example.org/biomedical/Protein"}
            ],
            "numericProperties": [
                {"value": "bio:prevalence", "label": "prevalence", "uri": "http://example.org/biomedical/prevalence"}
            ],
            "dateProperties": [
                {"value": "bio:discoveryDate", "label": "discovery date", "uri": "http://example.org/biomedical/discoveryDate"}
            ]
        },
        # Add domain-specific custom templates
        "customTemplates": [
            {
                "id": "bio-drug-disease",
                "category": "biomedical",
                "questionTemplate": "Which drugs are used to treat {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?drug WHERE {
                        ?drug a bio:Drug .
                        ?drug bio:treats {entity} .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "bio-gene-disease",
                "category": "biomedical",
                "questionTemplate": "Which genes are associated with {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?gene WHERE {
                        ?gene a bio:Gene .
                        ?gene bio:associatedWith {entity} .
                    }
                """,
                "complexity": "basic"
            }
        ]
    }

    generator = NL2SPARQLGenerator(biomedical_config)
    
    # Generate dataset
    dataset = generator.generate_dataset(
        size=100,
        complexity_distribution={"basic": 0.7, "intermediate": 0.3},
        include_variations=True
    )
    
    print(f"Generated {len(dataset)} biomedical question-SPARQL pairs")
    
    return dataset

# Example 4: Extract schema from TTL file and generate dataset
def extract_from_file_and_generate(file_path):
    try:
        print(f"Extracting schema from TTL file: {file_path}")
        
        extractor = KGSchemaExtractor()
        schema = extractor.extract_from_file(file_path, format='turtle')
        
        print(f"Extracted schema with {len(schema['schemaInfo']['types'])} types and {len(schema['schemaInfo']['properties'])} properties")
        
        # Generate dataset using extracted schema
        generator = NL2SPARQLGenerator(schema)
        
        dataset = generator.generate_dataset(
            size=500,
            complexity_distribution={"basic": 0.6, "intermediate": 0.3, "advanced": 0.1}
        )
        
        print(f"Generated {len(dataset)} question-SPARQL pairs from extracted schema")
        
        # Write to files
        with open('file_extracted_dataset.json', 'w', encoding='utf-8') as f:
            f.write(generator.export_json(dataset))
            
        with open('file_extracted_dataset.csv', 'w', encoding='utf-8') as f:
            f.write(generator.export_csv(dataset))
        
        return dataset
    except Exception as e:
        print(f"Error extracting schema from file and generating dataset: {e}")
        raise e

# Main function to run all examples
def main():
    try:
        # Generate dataset with predefined schema
        dbpedia_dataset = generate_dbpedia_dataset()
        
        # Generate dataset with domain-specific templates
        biomedical_dataset = generate_biomedical_dataset()
        
        # Extract schema from TTL file and generate dataset
        if os.path.exists('final_result.ttl'):
            ttl_dataset = extract_from_file_and_generate('final_result.ttl')
        
        # Extract schema and generate dataset (commented out as it requires internet connection)
        # extracted_dataset = extract_and_generate()
        
        print("All examples completed successfully!")
    except Exception as e:
        print(f"Error in examples: {e}")

if __name__ == "__main__":
    main()