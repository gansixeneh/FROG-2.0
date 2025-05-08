import json
import re

def remove_spaces_before_chars(sparql_query):
    """Remove spaces before ? and . in SPARQL queries"""
    # Remove spaces before ?
    modified_query = re.sub(r' \?', '?', sparql_query)
    # Remove spaces before .
    modified_query = re.sub(r' \.', '.', modified_query)
    return modified_query

def convert_sparql_to_prefix_notation(sparql_query):
    """
    Convert a SPARQL query from full URI notation to prefix notation.
    """
    # Define mappings from full URIs to prefixes
    uri_to_prefix_mappings = [
        (r'<http://www\.wikidata\.org/prop/direct/([^>]+)>', r'wdt:\1'),
        (r'<http://www\.wikidata\.org/prop/statement/([^>]+)>', r'ps:\1'),
        (r'<http://www\.wikidata\.org/prop/qualifier/([^>]+)>', r'pq:\1'),
        (r'<http://www\.wikidata\.org/prop/reference/([^>]+)>', r'pr:\1'),
        (r'<http://www\.wikidata\.org/prop/novalue/([^>]+)>', r'wdno:\1'),
        (r'<http://www\.wikidata\.org/prop/([^>]+)>', r'p:\1'),  # This must come after more specific prop patterns
        (r'<http://www\.wikidata\.org/entity/([^>]+)>', r'wd:\1'),
        (r'<http://www\.wikidata\.org/wiki/Special:EntityData/([^>]+)>', r'wdata:\1'),
        (r'<http://www\.wikidata\.org/reference/([^>]+)>', r'wdref:\1'),
        (r'<http://www\.wikidata\.org/value/([^>]+)>', r'wdv:\1'),
        (r'<http://www\.wikidata\.org/wiki/([^>]+)>', r'wdwiki:\1'),
        (r'<http://www\.wikidata\.org/([^>]+)>', r'wd:\1'),
        (r'<http://www\.w3\.org/2000/01/rdf-schema#([^>]+)>', r'rdfs:\1'),
        (r'<http://www\.w3\.org/2001/XMLSchema#([^>]+)>', r'xsd:\1'),
        (r'<http://www\.w3\.org/2004/02/skos/core#([^>]+)>', r'skos:\1'),
        (r'<http://schema\.org/([^>]+)>', r'schema:\1'),
        (r'<http://wikiba\.se/ontology#([^>]+)>', r'wikibase:\1'),
        (r'<http://www\.w3\.org/ns/prov#([^>]+)>', r'prov:\1'),
        (r'<http://creativecommons\.org/ns#([^>]+)>', r'cc:\1'),
        (r'<http://www\.openarchives\.org/ore/terms/([^>]+)>', r'ore:\1'),
        (r'<http://www\.opengis\.net/ont/geosparql#([^>]+)>', r'geo:\1'),
        (r'<http://www\.w3\.org/1999/02/22-rdf-syntax-ns#([^>]+)>', r'rdf:\1'),
        (r'<http://www\.w3\.org/2002/07/owl#([^>]+)>', r'owl:\1'),
        (r'<http://www\.bigdata\.com/rdf#([^>]+)>', r'bd:\1'),
        (r'<http://www\.w3\.org/ns/lemon/ontolex#([^>]+)>', r'ontolex:\1'),
        (r'<http://purl\.org/dc/terms/([^>]+)>', r'dct:\1'),
    ]
    
    # Apply each mapping to the query
    converted_query = sparql_query
    for pattern, prefix in uri_to_prefix_mappings:
        converted_query = re.sub(pattern, prefix, converted_query)
        
    return converted_query

def process_json_file(input_file, output_file=None):
    """Process a JSON file containing SPARQL queries"""
    # If no output file specified, create one with '_modified' suffix
    if output_file is None:
        output_file = input_file.replace('.json', '_modified.json')
    
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Processing {len(data)} queries from {input_file}...")
    
    # Process each item
    # Track items to remove
    items_to_remove = []
    
    for item in data:
        if 'sparql' in item:
            if not item['sparql'].startswith('ASK'):
                item['sparql'] = remove_spaces_before_chars(item['sparql'])
                item['sparql'] = convert_sparql_to_prefix_notation(item['sparql'])
            else:
                items_to_remove.append(item)
    
    # Remove the items after iteration
    for item in items_to_remove:
        data.remove(item)
    
    # Write the modified data back to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Processed {len(data)} queries and saved to {output_file}")

# Example usage:
if __name__ == "__main__":
    # You can specify your file paths here or pass them as arguments
    files = [
        # "dataset/possible_uris/qald_10_converted_labels_possible_uris.json",
        "dataset/possible_uris/qald_9_plus_train_wikidata_converted_labels_noises_possible_uris.json", 
        "dataset/possible_uris/qald_9_plus_test_wikidata_converted_labels_noises_possible_uris.json"
    ]
    
    for file_path in files:
        try:
            process_json_file(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")