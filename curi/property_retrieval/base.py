import pandas as pd
import weaviate
from sentence_transformers import SentenceTransformer
import re
from abc import ABC, abstractmethod


class BasePropertyRetrieval(ABC):
    """Base class for property retrieval systems using Weaviate"""
    
    def __init__(
        self,
        db_collection_name: str,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        is_local_client: bool = True,
        weaviate_host: str = "localhost",
        weaviate_port: int = 8080,
    ) -> None:
        """
        Initialize the base property retrieval system
        
        Args:
            db_collection_name (str): Name of the Weaviate collection
            embedding_model_name (str): Name of the embedding model
            is_local_client (bool): Whether to use local Weaviate client
            weaviate_host (str): Weaviate host
            weaviate_port (int): Weaviate port
        """
        self.db_collection_name = db_collection_name
        self.embedding_model_name = embedding_model_name
        self.is_local_client = is_local_client
        
        # Initialize Weaviate client
        if is_local_client:
            self.client = weaviate.Client(
                url=f"http://{weaviate_host}:{weaviate_port}",
                additional_headers={
                    "X-OpenAI-Api-Key": "fake-key"  # Required but not used for local
                }
            )
        else:
            # Add cloud configuration if needed
            raise NotImplementedError("Cloud Weaviate client not implemented yet")
        
        # Initialize embedding model
        self.model_embed = SentenceTransformer(embedding_model_name)
        
        # Initialize collection
        self._setup_collection()
        
    def _setup_collection(self):
        """Setup Weaviate collection"""
        # Check if collection exists
        try:
            self.collection = self.client.collections.get(self.db_collection_name)
            # Check if collection is empty
            result = self.collection.aggregate.over_all(total_count=True)
            self.is_collection_empty = result.total_count == 0
        except Exception as e:
            # Collection doesn't exist, create it
            print(f"Creating collection {self.db_collection_name}")
            self._create_collection()
            self.is_collection_empty = True
    
    def _create_collection(self):
        """Create Weaviate collection with appropriate schema"""
        collection_config = {
            "name": self.db_collection_name,
            "properties": [
                {
                    "name": "label",
                    "dataType": ["text"],
                },
                {
                    "name": "short",
                    "dataType": ["text"],
                },
                {
                    "name": "type",
                    "dataType": ["text"],
                },
                # Properties specific to properties (not entities)
                {
                    "name": "shortDomain",
                    "dataType": ["text"],
                },
                {
                    "name": "shortRange",
                    "dataType": ["text"],
                }
            ],
            "vectorizer": "none",  # We'll provide our own vectors
        }
        
        try:
            self.client.schema.create_class(collection_config)
            self.collection = self.client.collections.get(self.db_collection_name)
        except Exception as e:
            print(f"Error creating collection: {e}")
            # Try to get existing collection
            self.collection = self.client.collections.get(self.db_collection_name)
    
    def _search(self, q: str, type: str, k: int = 5) -> pd.DataFrame:
        """
        Search for entities or properties in Weaviate
        
        Args:
            q (str): Query string
            type (str): Type to search for ("entities" or "properties")
            k (int): Number of results to return
            
        Returns:
            pd.DataFrame: Search results with scores
        """
        # Generate embedding for query
        query_vector = self.model_embed.encode([q])[0].tolist()
        
        try:
            # Perform vector search with filtering
            result = self.collection.query.near_vector(
                near_vector=query_vector,
                limit=k,
                where={
                    "path": ["type"],
                    "operator": "Equal",
                    "valueText": type
                },
                return_metadata=["score"]
            )
            
            # Convert to DataFrame
            results = []
            for obj in result.objects:
                row = {
                    "label": obj.properties.get("label", ""),
                    "short": obj.properties.get("short", ""),
                    "type": obj.properties.get("type", ""),
                    "score": obj.metadata.score if obj.metadata.score else 0.0
                }
                
                # Add property-specific fields if they exist
                if "shortDomain" in obj.properties:
                    row["shortDomain"] = obj.properties.get("shortDomain")
                if "shortRange" in obj.properties:
                    row["shortRange"] = obj.properties.get("shortRange")
                    
                results.append(row)
            
            return pd.DataFrame(results)
            
        except Exception as e:
            print(f"Error searching Weaviate: {e}")
            return pd.DataFrame()
    
    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """
        Preprocess query into tokens
        
        Args:
            q (str): Query string
            
        Returns:
            list[str]: List of tokens
        """
        # Basic tokenization - split by spaces and remove punctuation
        tokens = re.findall(r'\b\w+\b', q.lower())
        return tokens

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """
        Generate n-grams from tokens
        
        Args:
            tokens (list[str]): List of tokens
            max_n (int): Maximum n-gram size
            
        Returns:
            list[str]: List of n-grams
        """
        ngrams = []
        
        # Generate unigrams, bigrams, and trigrams
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i + n])
                ngrams.append(ngram)
        
        return ngrams
    
    @abstractmethod
    def search_entities(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search for entities"""
        pass
    
    @abstractmethod
    def search_properties(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search for properties"""
        pass
