import json
import re

def extract_labels_from_ttl(ttl_content):
    """Extract resource IDs and their labels from the TTL file."""
    resource_labels = {}
    
    # Parse the TTL file line by line to extract resource labels
    lines = ttl_content.split('\n')
    current_resource = None
    
    for line in lines:
        line = line.strip()
        
        # Check if the line starts with a new resource definition
        resource_match = re.match(r'^ns1:(\w+)', line)
        if resource_match:
            current_resource = resource_match.group(1)
        
        # Check if the line contains a label
        label_match = re.search(r'rdfs:label\s+"([^"]+)"', line)
        if label_match and current_resource:
            resource_labels[current_resource] = label_match.group(1)
    
    return resource_labels

def extract_from_sparql(sparql_query, resource_labels):
    """Extract entities and properties from a SPARQL query and map to their labels."""
    # Extract URIs from the SPARQL query
    uris = re.findall(r'<http://example\.org/([^>]+)>', sparql_query)
    
    entity_labels = []
    property_labels = []
    
    for uri in uris:
        # Properties typically start with "has_" or are "also_known_as"
        if uri.startswith('has_') or uri == 'also_known_as':
            if uri in resource_labels and resource_labels[uri] not in property_labels:
                property_labels.append(resource_labels[uri])
        else:
            # Everything else is considered an entity
            if uri in resource_labels and resource_labels[uri] not in entity_labels:
                entity_labels.append(resource_labels[uri])
    
    return entity_labels, property_labels

def process_json(json_data, ttl_content):
    """Process the JSON data and add entity and property labels."""
    resource_labels = extract_labels_from_ttl(ttl_content)
    
    for item in json_data:
        if 'sparql' in item:
            entity_labels, property_labels = extract_from_sparql(item['sparql'], resource_labels)
            item['entity_labels'] = entity_labels
            item['property_labels'] = property_labels
    
    return json_data

# Main function to process the files
def main():
    # Load the JSON file
    with open('curi/enhanced_university_course_dataset.json', 'r') as f:
        json_data = json.load(f)

    # Load the TTL file
    with open('curi/final_result.ttl', 'r') as f:
        ttl_content = f.read()

    # Process the data
    result = process_json(json_data, ttl_content)

    # Save the result
    with open('curi/dataset_with_labels.json', 'w') as f:
        json.dump(result, f, indent=2)

    print("Processing complete. Result saved to 'enhanced_university_course_dataset_with_labels.json'.")

if __name__ == "__main__":
    main()