import json
import re

def extract_entities_and_properties(sparql_query):
    """
    Extract both entities and properties from a GESIS SPARQL query.
    - For entities: Extract full entity URIs enclosed in angle brackets
    - For properties: Extract properties with their prefixes (schema:, gesiskg:, etc.)
    """
    # Extract entity URIs (enclosed in angle brackets)
    entity_pattern = r'<([^>]+)>'
    entity_uris = set(re.findall(entity_pattern, sparql_query))
    
    # Extract property names with their prefixes (schema:name, gesiskg:libraryLocation)
    property_pattern = r'(\w+:\w+)'
    property_ids = set(re.findall(property_pattern, sparql_query))
    
    return entity_uris, property_ids

def filter_matches(entities_matches, properties_matches, entity_uris, property_ids):
    """Filter entities and properties matches based on what's used in the SPARQL query."""
    filtered_entities = [match for match in entities_matches if match['id'] in entity_uris]
    filtered_properties = [match for match in properties_matches if match['id'] in property_ids]
    return filtered_entities, filtered_properties

def process_json_file(input_file, output_file):
    """Process the JSON file and output filtered results."""
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Fix incomplete JSON if necessary
    if not content.strip().endswith(']'):
        content = content.strip() + ']'
    
    data = json.loads(content)
    
    results = []
    for item in data:
        # Extract entities and properties used in the SPARQL query
        entity_uris, property_ids = extract_entities_and_properties(item['sparql'])
        
        # Filter entities_matches and properties_matches
        filtered_entities, filtered_properties = filter_matches(
            item['entities_matches'],
            item['properties_matches'],
            entity_uris,
            property_ids
        )
        
        # Create filtered result
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