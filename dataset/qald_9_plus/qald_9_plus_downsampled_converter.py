import json
import re

def convert_json_format(input_data):
    """
    Convert from the first JSON format to the second JSON format,
    removing PREFIX declarations from SPARQL queries.
    """
    query_names = input_data["query_name"]
    wikidata_queries = input_data["wikidata_query_raw"]
    
    result = []
    
    # Iterate through all keys (ensuring they're sorted numerically)
    for key in sorted(query_names.keys(), key=int):
        if key not in wikidata_queries:
            continue
            
        question = query_names[key]
        sparql = wikidata_queries[key]
        
        # Remove PREFIX declarations
        sparql = re.sub(r'PREFIX\s+\w+:\s*<[^>]+>\s*', '', sparql)
        
        # Clean up any extra whitespace from removed prefixes
        sparql = sparql.strip()
        
        # Create the new format object
        result.append({
            "question": question,
            "sparql": sparql
        })
    
    return result

# Example usage:
# Load the input JSON from paste.txt
with open('qald_9_plus_downsampled_test_wikidata.json', 'r') as f:
    input_data = json.load(f)

# Convert to the new format
converted_data = convert_json_format(input_data)

# Save to a new file
with open('qald_9_plus_downsampled_test_wikidata_converted.json', 'w') as f:
    json.dump(converted_data, f, indent=2)

# Print first few results to verify
print("First 3 converted entries:")
for i, entry in enumerate(converted_data[:3]):
    print(f"\nEntry {i+1}:")
    print(f"Question: {entry['question']}")
    print(f"SPARQL: {entry['sparql']}")