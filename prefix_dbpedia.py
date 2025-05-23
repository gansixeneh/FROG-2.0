import json
import os
import re

def convert_uris_to_prefixes(input_files):
    """
    Convert URIs in SPARQL queries to prefix format for all specified JSON files.
    
    Args:
        input_files: List of JSON file paths to process
        
    Returns:
        Dictionary mapping output filenames to processed data
    """
    # Define common prefixes
    prefixes = {
        # DBpedia prefixes
        "http://dbpedia.org/resource/": "res",
        "http://dbpedia.org/ontology/": "dbo",
        "http://dbpedia.org/property/": "dbp",
        "http://dbpedia.org/class/yago/": "yago",
        
        # Common RDF prefixes
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs",
        "http://www.w3.org/2002/07/owl#": "owl",
        "http://www.w3.org/2001/XMLSchema#": "xsd",
        "http://xmlns.com/foaf/0.1/": "foaf",
        "http://purl.org/dc/terms/": "dct",
        "http://www.w3.org/2004/02/skos/core#": "skos",
        
        # Other prefixes
        "http://purl.org/dc/elements/1.1/": "dc",
        "http://schema.org/": "schema",
        "http://purl.org/ontology/bibo/": "bibo",
        "http://www.w3.org/ns/prov#": "prov",
    }
    
    def replace_uri_with_prefix(match):
        uri = match.group(1)
        for prefix_uri, prefix_name in prefixes.items():
            if uri.startswith(prefix_uri):
                local_name = uri[len(prefix_uri):]
                return f"{prefix_name}:{local_name}"
        return f"<{uri}>"
    
    # Dictionary to store results
    results = {}
    
    for input_file in input_files:
        # Determine output filename
        base_name = os.path.basename(input_file)
        file_name_without_ext = os.path.splitext(base_name)[0]
        output_file = f"{file_name_without_ext}_prefix.json"
        
        # Read input JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process each item
        for item in data:
            if 'sparql' in item:
                # Convert URIs to prefixes
                sparql = item['sparql']
                # Replace URIs enclosed in < >
                sparql = re.sub(r'<(http://[^>]+)>', replace_uri_with_prefix, sparql)
                item['sparql'] = sparql
        
        # Store the processed data
        results[output_file] = data
        
        # Write the processed data to file
        output_path = os.path.join(os.path.dirname(input_file), output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"Processed {input_file} -> {output_path}")
    
    return results

# Example usage
if __name__ == "__main__":
    input_files = [
        "dataset/qald_9_plus/qald_9_plus_test_dbpedia_converted.json",
        "dataset/qald_9_plus/qald_9_plus_train_dbpedia_converted.json"
    ]
    
    processed_files = convert_uris_to_prefixes(input_files)