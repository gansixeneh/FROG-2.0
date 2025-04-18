import json
import re
import requests
import time
from tqdm import tqdm

def extract_entities_and_properties(sparql_query):
    """Extract Wikidata entity IDs and property IDs from a SPARQL query"""
    # Extract entities (wd:Q... or http://www.wikidata.org/entity/Q...)
    entity_pattern = r'wd:Q\d+|<http://www\.wikidata\.org/entity/Q\d+>'
    # Extract properties (wdt:P..., p:P..., ps:P..., pq:P... or URL forms)
    property_pattern = r'wdt:P\d+|p:P\d+|ps:P\d+|pq:P\d+|<http://www\.wikidata\.org/prop/direct/P\d+>|<http://www\.wikidata\.org/prop/P\d+>|<http://www\.wikidata\.org/prop/statement/P\d+>|<http://www\.wikidata\.org/prop/qualifier/P\d+>'
    
    entities = re.findall(entity_pattern, sparql_query)
    properties = re.findall(property_pattern, sparql_query)
    
    # Clean up entities (extract just the Q numbers)
    cleaned_entities = []
    for entity in entities:
        if entity.startswith('wd:'):
            cleaned_entities.append(entity[3:])  # Remove 'wd:'
        else:
            # Extract Q number from URL
            match = re.search(r'Q\d+', entity)
            if match:
                cleaned_entities.append(match.group(0))
    
    # Clean up properties (extract just the P numbers)
    cleaned_properties = []
    for prop in properties:
        if prop.startswith('wdt:'):
            cleaned_properties.append(prop[4:])  # Remove 'wdt:'
        elif prop.startswith('p:'):
            cleaned_properties.append(prop[2:])  # Remove 'p:'
        elif prop.startswith('ps:'):
            cleaned_properties.append(prop[3:])  # Remove 'ps:'
        elif prop.startswith('pq:'):
            cleaned_properties.append(prop[3:])  # Remove 'pq:'
        else:
            # Extract P number from URL
            match = re.search(r'P\d+', prop)
            if match:
                cleaned_properties.append(match.group(0))
    
    # Remove duplicates
    cleaned_entities = list(set(cleaned_entities))
    cleaned_properties = list(set(cleaned_properties))
    
    return cleaned_entities, cleaned_properties

def get_wikidata_labels(ids):
    """Fetch labels for Wikidata IDs using the Wikidata API"""
    if not ids:
        return {}
    
    labels = {}
    batch_size = 50  # Process in batches to avoid API limits
    
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i+batch_size]
        pipe_separated_ids = "|".join(batch)
        
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbgetentities",
            "ids": pipe_separated_ids,
            "props": "labels",
            "languages": "en",
            "format": "json"
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if "entities" in data:
                for entity_id, entity_data in data["entities"].items():
                    if "labels" in entity_data and "en" in entity_data["labels"]:
                        labels[entity_id] = entity_data["labels"]["en"]["value"]
                    else:
                        # Use ID if no label is available
                        labels[entity_id] = entity_id
            
            # Be nice to the Wikidata API with a small delay
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error fetching labels for batch {i//batch_size + 1}: {e}")
            # Use IDs as fallback for failures
            for entity_id in batch:
                if entity_id not in labels:
                    labels[entity_id] = entity_id
    
    return labels

def main():
    input_file = "dataset\qald_10\qald_10_converted.json"
    file_name = input_file.split("\\")[-1].split(".")[0]
    output_file = f"dataset\\labels\\{file_name}_labels.json"
    
    # Load the input file
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Process each question-SPARQL pair
    results = []
    all_entities = []
    all_properties = []
    
    print("Extracting entities and properties from SPARQL queries...")
    for item in tqdm(data):
        question = item.get("question", "")
        sparql = item.get("sparql", "")
        
        entities, properties = extract_entities_and_properties(sparql)
        
        # Collect all unique IDs for batch processing
        all_entities.extend(entities)
        all_properties.extend(properties)
        
        results.append({
            "question": question,
            "entity_ids": entities,
            "property_ids": properties
        })
    
    # Remove duplicates
    all_entities = list(set(all_entities))
    all_properties = list(set(all_properties))
    
    print(f"Found {len(all_entities)} unique entities and {len(all_properties)} unique properties")
    
    # Fetch labels from Wikidata
    print("Fetching entity labels from Wikidata...")
    entity_labels = get_wikidata_labels(all_entities)
    
    print("Fetching property labels from Wikidata...")
    property_labels = get_wikidata_labels(all_properties)
    
    # Create final output
    final_results = []
    for item in results:
        entity_label_list = [entity_labels.get(entity_id, entity_id) for entity_id in item["entity_ids"]]
        property_label_list = [property_labels.get(prop_id, prop_id) for prop_id in item["property_ids"]]
        
        final_results.append({
            "question": item["question"],
            "entities": entity_label_list,
            "properties": property_label_list
        })
    
    # Write the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()