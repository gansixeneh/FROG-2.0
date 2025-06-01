import weaviate
from weaviate.connect import ConnectionParams

def list_all_collections():
    # Connect to Weaviate through ngrok using WeaviateClient
    try:
        client = weaviate.connect_to_local(
            host="192.168.0.221",
            port=8080,
            grpc_port=50052,
        )
        print("Connected to Weaviate")
        
        # Get all collections
        collection_names = client.collections.list_all()
        
        if collection_names:
            print("\nCollections found in Weaviate:")
            for i, collection_name in enumerate(collection_names, 1):
                collection = client.collections.get(collection_name)
                print(f"{i}. {collection_name}")
                
                # Get additional details about the collection
                try:
                    collection = client.collections.get(collection_name)
                    # Get count of objects in the collection
                    count = collection.aggregate.over_all().total_count
                    print(f"   - Count: {count}")
                except Exception as collection_error:
                    print(f"   - Could not get details: {collection_error}")
        else:
            print("No collections found in the Weaviate instance.")
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    list_all_collections()