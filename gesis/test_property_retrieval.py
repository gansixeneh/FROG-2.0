from property_retrieval import GesisPropertyRetrieval  # Import your class

def count_embeddings():
    # Initialize the GesisPropertyRetrieval class
    # Use the same parameters as in your main application
    retriever = GesisPropertyRetrieval(
        endpoint_url="http://localhost:3030/gesis/query",  # Adjust if needed
        is_local_client=True,
        weaviate_host="localhost",
        weaviate_port=8080
    )
    
    # Get counts from original DataFrames
    original_entities_count = len(retriever.df_entities)
    original_properties_count = len(retriever.df_properties)
    
    # Get counts from Weaviate collections
    entities_in_weaviate = retriever.entities_collection.aggregate.over_all().total_count
    properties_in_weaviate = retriever.properties_collection.aggregate.over_all().total_count
    
    print(f"=== Embedding Storage Verification ===")
    print(f"Entities:")
    print(f"  - Original count: {original_entities_count}")
    print(f"  - Stored in Weaviate: {entities_in_weaviate}")
    print(f"  - All stored: {'✓' if original_entities_count == entities_in_weaviate else '✗'}")
    print()
    print(f"Properties:")
    print(f"  - Original count: {original_properties_count}")
    print(f"  - Stored in Weaviate: {properties_in_weaviate}")
    print(f"  - All stored: {'✓' if original_properties_count == properties_in_weaviate else '✗'}")
    
    # Close the Weaviate client connection
    retriever.close()

if __name__ == "__main__":
    count_embeddings()