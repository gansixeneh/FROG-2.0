import rdflib
from rdflib import RDF, Namespace

def clean_ttl_file():
    # Define file paths
    input_file = "GESISKG_resources_bib.ttl"
    output_file = "GESISKG_resources_bib_modified.ttl"
    
    # Define schema namespace
    SCHEMA = Namespace("https://schema.org/")
    
    # Create an RDF graph
    g = rdflib.Graph()
    
    # Parse the input TTL file
    print(f"Loading {input_file}...")
    g.parse(input_file, format="turtle")
    print(f"Loaded {len(g)} triples.")
    
    # Find all subjects that are of type DuplicateMetadata
    duplicate_entities = set()
    for s, p, o in g.triples((None, RDF.type, SCHEMA.DuplicateMetadata)):
        duplicate_entities.add(s)
    print(f"Found {len(duplicate_entities)} DuplicateMetadata entities.")
    
    # Find all subjects that are ScholarlyArticle but don't have schema:name
    scholarly_articles_without_name = set()
    
    # First, find all ScholarlyArticle entities
    scholarly_articles = set()
    for s, p, o in g.triples((None, RDF.type, SCHEMA.ScholarlyArticle)):
        scholarly_articles.add(s)
    
    print(f"Found {len(scholarly_articles)} ScholarlyArticle entities.")
    
    # Check which ScholarlyArticle entities don't have schema:name
    for article in scholarly_articles:
        has_name = False
        for s, p, o in g.triples((article, SCHEMA.name, None)):
            has_name = True
            break
        if not has_name:
            scholarly_articles_without_name.add(article)
    
    print(f"Found {len(scholarly_articles_without_name)} ScholarlyArticle entities without schema:name.")
    
    # Combine both sets of entities to remove
    entities_to_remove = duplicate_entities.union(scholarly_articles_without_name)
    print(f"Total entities to remove: {len(entities_to_remove)}")
    
    # Create a new graph without the unwanted entities
    new_graph = rdflib.Graph()
    
    # Copy namespaces from the original graph
    for prefix, namespace in g.namespaces():
        new_graph.bind(prefix, namespace)
    
    # Add all triples that don't have an unwanted entity as subject
    for s, p, o in g:
        if s not in entities_to_remove:
            new_graph.add((s, p, o))
    
    print(f"New graph has {len(new_graph)} triples (removed {len(g) - len(new_graph)}).")
    
    # Serialize the new graph to the output file
    new_graph.serialize(destination=output_file, format="turtle")
    print(f"Saved simplified graph to {output_file}.")

if __name__ == "__main__":
    clean_ttl_file()