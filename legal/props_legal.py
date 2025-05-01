import rdflib
from rdflib import Graph
from collections import Counter

def extract_properties(ttl_file_path):
    """
    Extract all properties (predicates) from an RDF knowledge graph.
    
    Args:
        ttl_file_path: Path to the TTL file
        
    Returns:
        dict: Information about each property
    """
    # Create and parse the RDF graph
    g = Graph()
    print(f"Parsing {ttl_file_path}...")
    g.parse(ttl_file_path, format="turtle")
    print("Parsing complete!")
    
    # Get all unique predicates
    predicates = set(g.predicates())
    print(f"Found {len(predicates)} unique properties")
    
    # Count usage of each predicate
    predicate_usage = Counter()
    for s, p, o in g:
        predicate_usage[p] += 1
    
    # Properties information
    properties = {}
    for predicate in predicates:
        pred_uri = str(predicate)
        properties[pred_uri] = {
            'usage_count': predicate_usage[predicate],
            'examples': []
        }
        
        # Get sample triples for each property (limit to 5)
        sample_count = 0
        for s, p, o in g.triples((None, predicate, None)):
            if sample_count < 5:
                if isinstance(o, rdflib.Literal):
                    obj_value = o.toPython()
                    # Convert dates to string to avoid JSON serialization issues
                    if hasattr(obj_value, 'isoformat'):
                        obj_value = obj_value.isoformat()
                else:
                    obj_value = str(o)
                
                properties[pred_uri]['examples'].append({
                    'subject': str(s),
                    'object': obj_value
                })
                sample_count += 1
    
    return properties

def print_property_summary(properties):
    """Print a summary of the extracted properties"""
    print("\nTop 20 properties by usage:")
    sorted_props = sorted(properties.items(), key=lambda x: x[1]['usage_count'], reverse=True)
    
    for i, (prop_uri, data) in enumerate(sorted_props[:20], 1):
        print(f"{i}. {prop_uri}: used {data['usage_count']} times")
    
    # Get namespaces used
    namespaces = set()
    for prop_uri in properties.keys():
        if '#' in prop_uri:
            namespace = prop_uri.split('#')[0] + '#'
        elif '/' in prop_uri:
            parts = prop_uri.split('/')
            namespace = '/'.join(parts[:-1]) + '/'
        else:
            namespace = "unknown"
        namespaces.add(namespace)
    
    print("\nNamespaces used:")
    for namespace in sorted(namespaces):
        print(f"  {namespace}")

def main():
    # Path to your TTL file
    ttl_file_path = "data-lex2kg.ttl"  # Update this to your actual file path
    
    # Extract properties
    properties = extract_properties(ttl_file_path)
    
    # Print summary information
    print_property_summary(properties)
    
    # Save to JSON file
    import json
    with open("legal_kg_properties.json", "w", encoding="utf-8") as f:
        json.dump(properties, f, ensure_ascii=False, indent=2)
    print("\nProperty data saved to legal_kg_properties.json")
    
    return properties

if __name__ == "__main__":
    main()