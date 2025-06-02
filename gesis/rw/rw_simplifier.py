import json
import re

def extract_entities_and_properties(sparql_query):
    """
    Extract both entities and properties from a SPARQL query.
    - For properties: Extract the property names with lex2kg-o: prefix
    - For entities: Extract full entity URIs
    """
    # Extract property names (with lex2kg-o: prefix)
    property_pattern = r'lex2kg-o:([a-zA-Z_][a-zA-Z0-9_]*)'
    property_names = set(re.findall(property_pattern, sparql_query))
    
    # Extract full entity URIs (typically in angle brackets)
    entity_pattern = r'<(https://example\.org/lex2kg/[^>]+)>'
    entity_uris = set(re.findall(entity_pattern, sparql_query))
    
    return entity_uris, property_names

def filter_matches(entities_matches, properties_matches, entity_uris, property_names):
    """Filter entities and properties matches based on what's used in the SPARQL query."""
    filtered_entities = [match for match in entities_matches if match['id'] in entity_uris]
    
    filtered_properties = []
    for match in properties_matches:
        if match['label'] in property_names:
            # Create a copy of the match and modify the id to use lex2kg-o: prefix
            modified_match = match.copy()
            modified_match['id'] = f"lex2kg-o:{match['label']}"
            filtered_properties.append(modified_match)
            
    return filtered_entities, filtered_properties

def process_json_file(input_file, output_file):
    """Process the JSON file and output filtered results."""
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    results = []
    for item in data:
        # Extract entities and properties used in the SPARQL query
        entity_uris, property_names = extract_entities_and_properties(item['sparql'])
        
        # Filter entities_matches and properties_matches
        filtered_entities, filtered_properties = filter_matches(
            item['entities_matches'],
            item['properties_matches'],
            entity_uris,
            property_names
        )
        
        # Create filtered result without entities and properties attributes
        filtered_item = {
            'id': item['id'],
            'sparql': item['sparql'],
            'entities_matches': filtered_entities,
            'properties_matches': filtered_properties
        }
        results.append(filtered_item)
    
    # Output the filtered results
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(results, outfile, indent=2, ensure_ascii=False)
    
    print(f"Processed data saved to {output_file}")

def main():
    # Process the file
    input_file = 'gesis_rw.json'
    output_file = 'gesis_filter.json'
    process_json_file(input_file, output_file)

if __name__ == "__main__":
    main()