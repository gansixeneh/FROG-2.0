from property_retrieval import GesisPropertyRetrieval


property_retrieval = GesisPropertyRetrieval(
    endpoint_url="http://localhost:3030/gesis" + "/query",  # Add /query for SPARQL endpoint
    embedding_model_name="jinaai/jina-embeddings-v3",
    is_local_client=True,
    weaviate_host="localhost",
    weaviate_port=8080
)