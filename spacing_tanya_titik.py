import json
import re

def remove_spaces_before_chars(sparql_query):
    """Remove spaces before ? and . in SPARQL queries"""
    # Remove spaces before ?
    modified_query = re.sub(r' \?', '?', sparql_query)
    # Remove spaces before .
    modified_query = re.sub(r' \.', '.', modified_query)
    return modified_query

def process_json_file(input_file, output_file=None):
    """Process a JSON file containing SPARQL queries"""
    # If no output file specified, create one with '_modified' suffix
    if output_file is None:
        output_file = input_file.replace('.json', '_modified.json')
    
    # Read the JSON file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process each item
    for item in data:
        if 'sparql' in item:
            item['sparql'] = remove_spaces_before_chars(item['sparql'])
    
    # Write the modified data back to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Processed {len(data)} queries and saved to {output_file}")

# Example usage:
if __name__ == "__main__":
    # You can specify your file paths here or pass them as arguments
    files = [
        "dataset/possible_uris/qald_10_converted_labels_possible_uris.json",
        "dataset/possible_uris/qald_9_plus_train_wikidata_converted_labels_possible_uris.json", 
        "dataset/possible_uris/qald_9_plus_test_wikidata_converted_labels_possible_uris.json"
    ]
    
    for file_path in files:
        try:
            process_json_file(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")