import json
import re
import requests
import time
from tqdm import tqdm

def extract_dbpedia_elements(sparql_query):
    """Extract DBpedia entities and ontology elements from a SPARQL query"""
    # Extract resources/entities
    entity_pattern = r'(res|dbr|dbc):([A-Za-z0-9_,.\(\)-]+)'
    
    # Extract ontology elements
    # Include all possible prefixes used in DBpedia queries
    ontology_pattern = r'(dbo|onto|rdf|rdfs|dct|xsd|yago|foaf|owl|skos):([A-Za-z0-9_]+)'
    
    # Extract properties
    property_pattern = r'(dbp|prop|p|ps|pq|dbpedia2):([A-Za-z0-9_]+)'
    
    entities = re.findall(entity_pattern, sparql_query)
    ontologies = re.findall(ontology_pattern, sparql_query)
    properties = re.findall(property_pattern, sparql_query)
    
    # Clean up entities
    cleaned_entities = []
    for prefix, name in entities:
        cleaned_entities.append(f"{prefix}:{name}")
    
    # Clean up ontologies
    cleaned_ontologies = []
    for prefix, name in ontologies:
        cleaned_ontologies.append(f"{prefix}:{name}")
    
    # Clean up properties
    cleaned_properties = []
    for prefix, name in properties:
        cleaned_properties.append(f"{prefix}:{name}")
    
    # Remove duplicates
    cleaned_entities = list(set(cleaned_entities))
    cleaned_ontologies = list(set(cleaned_ontologies))
    cleaned_properties = list(set(cleaned_properties))
    
    # Combine all ontology elements
    all_ontology_elements = cleaned_ontologies + cleaned_properties
    
    return cleaned_entities, all_ontology_elements

def get_entity_labels(entities):
    """Generate labels for DBpedia entities by cleaning up the resource name"""
    if not entities:
        return {}
    
    labels = {}
    
    for entity in entities:
        if ':' in entity:
            prefix, name = entity.split(':', 1)
            # Replace underscores with spaces and handle parentheses for better readability
            label = name.replace('_', ' ')
            labels[entity] = label
    
    return labels

def categorize_ontology_elements(ontology_elements):
    """Categorize DBpedia ontology elements as classes, object properties, or data properties"""
    # DBpedia SPARQL endpoint
    endpoint = "https://dbpedia.org/sparql"
    
    classes = []
    obj_properties = []
    data_properties = []
    
    # Prefix to URI mapping for DBpedia
    prefix_to_uri = {
        'dbo': 'http://dbpedia.org/ontology/',
        'onto': 'http://dbpedia.org/ontology/',
        'yago': 'http://dbpedia.org/class/yago/',
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'foaf': 'http://xmlns.com/foaf/0.1/',
        'owl': 'http://www.w3.org/2002/07/owl#',
        'xsd': 'http://www.w3.org/2001/XMLSchema#',
        'skos': 'http://www.w3.org/2004/02/skos/core#',
        'dct': 'http://purl.org/dc/terms/',
        'dbp': 'http://dbpedia.org/property/',
        'prop': 'http://dbpedia.org/property/',
        'p': 'http://www.wikidata.org/prop/',
        'ps': 'http://www.wikidata.org/prop/statement/',
        'pq': 'http://www.wikidata.org/prop/qualifier/',
        'dbpedia2': 'http://dbpedia.org/property/'
    }
    
    for element in tqdm(ontology_elements, desc="Categorizing ontology elements"):
        if ':' not in element:
            continue
            
        prefix, name = element.split(':', 1)
        
        # Skip if prefix not in our mapping
        if prefix not in prefix_to_uri:
            continue
            
        uri = prefix_to_uri[prefix] + name
        
        # SPARQL query to check type
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?type WHERE {{
          <{uri}> rdf:type ?type .
          FILTER(?type IN (owl:Class, owl:ObjectProperty, owl:DatatypeProperty))
        }}
        LIMIT 1
        """
        
        try:
            headers = {'Accept': 'application/json'}
            response = requests.get(endpoint, params={'query': query, 'format': 'json'}, headers=headers)
            
            if response.status_code == 200:
                results = response.json().get('results', {}).get('bindings', [])
                if results:
                    type_uri = results[0]['type']['value']
                    if 'Class' in type_uri:
                        classes.append(element)
                    elif 'ObjectProperty' in type_uri:
                        obj_properties.append(element)
                    elif 'DatatypeProperty' in type_uri:
                        data_properties.append(element)
                else:
                    # Apply heuristics based on naming conventions and prefixes
                    if prefix in ['dbo', 'onto', 'yago', 'owl', 'skos'] and name[0].isupper():
                        classes.append(element)
                    elif prefix in ['rdf', 'rdfs', 'dct'] and name in ['type', 'subClassOf', 'label', 'subPropertyOf', 'domain', 'range', 'subject']:
                        obj_properties.append(element)
                    elif prefix in ['dbp', 'prop', 'p', 'ps', 'pq', 'dbpedia2']:
                        data_properties.append(element)
                    elif prefix in ['dbo', 'onto', 'foaf']:
                        obj_properties.append(element)
            else:
                # Apply the same heuristics for failure cases
                if prefix in ['dbo', 'onto', 'yago', 'owl', 'skos'] and name[0].isupper():
                    classes.append(element)
                elif prefix in ['rdf', 'rdfs', 'dct'] and name in ['type', 'subClassOf', 'label', 'subPropertyOf', 'domain', 'range', 'subject']:
                    obj_properties.append(element)
                elif prefix in ['dbp', 'prop', 'p', 'ps', 'pq', 'dbpedia2']:
                    data_properties.append(element)
                elif prefix in ['dbo', 'onto', 'foaf']:
                    obj_properties.append(element)
                    
            # Be nice to the DBpedia endpoint with a small delay
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error checking type for {element}: {str(e)}")
            # Apply heuristics for exception cases
            if prefix in ['dbo', 'onto', 'yago', 'owl', 'skos'] and name[0].isupper():
                classes.append(element)
            elif prefix in ['rdf', 'rdfs', 'dct'] and name in ['type', 'subClassOf', 'label', 'subPropertyOf', 'domain', 'range', 'subject']:
                obj_properties.append(element)
            elif prefix in ['dbp', 'prop', 'p', 'ps', 'pq', 'dbpedia2']:
                data_properties.append(element)
            elif prefix in ['dbo', 'onto', 'foaf']:
                obj_properties.append(element)
    
    return classes, obj_properties, data_properties

def get_ontology_labels(ontology_elements):
    """Generate labels for DBpedia ontology elements"""
    if not ontology_elements:
        return {}
    
    labels = {}
    
    for element in ontology_elements:
        if ':' in element:
            prefix, name = element.split(':', 1)
            # Replace underscores with spaces for better readability
            label = name.replace('_', ' ')
            labels[element] = label
    
    return labels

def main():
    input_files = [
        "dataset/qald_9_plus/qald_9_plus_train_dbpedia_converted_prefix.json",
        "dataset/qald_9_plus/qald_9_plus_test_dbpedia_converted_prefix.json"
    ]
    
    for input_file in input_files:
        filename = input_file.split("/")[-1].split(".")[0]
        filename = filename.strip("_prefix")
        output_file = f"dataset/labels/{filename}_labels.json"
        
        # Load the input file
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Process each question-SPARQL pair
        results = []
        all_entities = []
        all_ontology_elements = []
        
        print(f"Extracting entities and ontology elements from SPARQL queries in {input_file}...")
        for item in tqdm(data):
            question = item.get("question", "")
            sparql = item.get("sparql", "")
            
            entities, ontology_elements = extract_dbpedia_elements(sparql)
            
            # Collect all unique elements for batch processing
            all_entities.extend(entities)
            all_ontology_elements.extend(ontology_elements)
            
            results.append({
                "question": question,
                "entities": entities,
                "ontology_elements": ontology_elements,
                "sparql": sparql
            })
        
        # Remove duplicates
        all_entities = list(set(all_entities))
        all_ontology_elements = list(set(all_ontology_elements))
        
        print(f"Found {len(all_entities)} unique entities and {len(all_ontology_elements)} unique ontology elements")
        
        # Get entity labels
        print("Generating entity labels...")
        entity_labels = get_entity_labels(all_entities)
        
        # Categorize ontology elements
        print("Categorizing ontology elements by their RDF type...")
        classes, obj_properties, data_properties = categorize_ontology_elements(all_ontology_elements)
        
        # Get labels for ontology elements
        print("Generating ontology labels...")
        class_labels = get_ontology_labels(classes)
        obj_property_labels = get_ontology_labels(obj_properties)
        data_property_labels = get_ontology_labels(data_properties)
        
        # Create final output
        final_results = []
        for item in results:
            entity_label_list = [entity_labels.get(entity, entity) for entity in item["entities"]]
            
            # Filter ontology elements for this specific query
            query_classes = [c for c in classes if c in item["ontology_elements"]]
            query_obj_properties = [p for p in obj_properties if p in item["ontology_elements"]]
            query_data_properties = [p for p in data_properties if p in item["ontology_elements"]]
            
            class_label_list = [class_labels.get(c, c) for c in query_classes]
            obj_property_label_list = [obj_property_labels.get(p, p) for p in query_obj_properties]
            data_property_label_list = [data_property_labels.get(p, p) for p in query_data_properties]
            
            final_results.append({
                "question": item["question"],
                "entities": entity_label_list,
                "ontology": {
                    "classes": class_label_list,
                    "obj properties": obj_property_label_list,
                    "data properties": data_property_label_list
                },
                "sparql": item["sparql"]
            })
        
        # Write the output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=2, ensure_ascii=False)
        
        print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()