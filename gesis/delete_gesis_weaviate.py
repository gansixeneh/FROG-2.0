import weaviate

def delete_gesis_entities_collection():
    # Connect to Weaviate
    try:
        client = weaviate.connect_to_local(
            host="localhost",
            port=8080,
            grpc_port=50052,
        )
        
        print("Connected to Weaviate")
        
        for db in ["gesis_entities_db", "gesis_properties_db"]:
            if client.collections.exists(db):
                print(f"Collection '{db}' found. Deleting...")
                
                # Delete the collection
                client.collections.delete(db)
                print(f"Collection '{db}' successfully deleted.")
            else:
                print(f"Collection '{db}' does not exist.")
        
        # Close the connection
        if hasattr(client, 'close'):
            client.close()
            
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    delete_gesis_entities_collection()