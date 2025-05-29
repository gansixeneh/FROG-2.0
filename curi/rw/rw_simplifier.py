import json
import re

def extract_namespaced_identifiers(sparql_query):
    """Extract all ns1: prefixed identifiers from a SPARQL query."""
    pattern = r'ns1:[a-zA-Z_][a-zA-Z0-9_]*'
    return set(re.findall(pattern, sparql_query))

def filter_matches(matches_list, used_identifiers):
    """Filter matches list to only include items whose id is in used_identifiers."""
    return [match for match in matches_list if match['id'] in used_identifiers]

def process_json_file(file_path):
    """Process the JSON file and output filtered results."""
    
    # Read the JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    results = []
    
    for item in data:
        # Extract identifiers used in the SPARQL query
        used_identifiers = extract_namespaced_identifiers(item['sparql'])
        
        # Filter entities_matches and properties_matches
        filtered_entities = filter_matches(item['entities_matches'], used_identifiers)
        filtered_properties = filter_matches(item['properties_matches'], used_identifiers)
        
        # Create filtered result
        filtered_item = {
            'id': item['id'],
            'sparql': item['sparql'],
            'entities_matches': filtered_entities,
            'properties_matches': filtered_properties
        }
        
        results.append(filtered_item)
    
    return results

def main():
    # Process the file (replace 'paste.txt' with your actual file path)
    file_path = 'curi_pattern_based.json'
    
    filtered_data = process_json_file(file_path)
    
    # Output the filtered results
    output_file = 'curi_pb_filter.json'
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(filtered_data, outfile, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()