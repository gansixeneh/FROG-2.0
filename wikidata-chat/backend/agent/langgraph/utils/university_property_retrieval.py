# backend/agent/langgraph/utils/university_property_retrieval.py
import pandas as pd
import numpy as np
import os
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams
import weaviate
import logging

# Import our model singleton
from .singletons.model_singletons import get_sentence_transformer

# Configure logging
logger = logging.getLogger(__name__)

class UniversityPropertyRetrieval:
    """Class for managing university curriculum properties retrieval and search"""
    def __init__(
        self,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        weaviate_client=None
    ) -> None:
        # Use the singleton instead of creating a new instance
        self.model_embed = get_sentence_transformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Connect to local Weaviate or use provided client
        if weaviate_client:
            self.client = weaviate_client
        else:
            try:
                # Get Weaviate connection details from environment variables
                weaviate_host = os.environ.get("WEAVIATE_URL", "localhost")
                weaviate_http_port = int(os.environ.get("WEAVIATE_HTTP_PORT", 8080))
                weaviate_grpc_port = int(os.environ.get("WEAVIATE_GRPC_PORT", 50052))
                
                logger.info(f"Connecting to Weaviate at {weaviate_host}:{weaviate_http_port} (gRPC: {weaviate_grpc_port})")
                
                self.client = weaviate.connect_to_local(
                    host=weaviate_host,
                    port=weaviate_http_port,
                    grpc_port=weaviate_grpc_port,
                )
            except Exception as e:
                logger.error(f"Error connecting to Weaviate: {e}")
                raise e
        
        # Get collection for university properties
        db_collection_name = "university_properties_db"
        try:
            if not self.client.collections.exists(db_collection_name):
                logger.warning(f"Collection {db_collection_name} does not exist - creating an empty collection")
                # Create a minimal collection for testing
                self.collection = self.client.collections.create(
                    name=db_collection_name,
                    vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
                )
            else:
                self.collection = self.client.collections.get(db_collection_name)
        except Exception as e:
            logger.error(f"Error accessing collection {db_collection_name}: {e}")
            # Create a minimal collection object that we can use for testing
            self.collection = None

        # Get entity collection for university entities (assume it exists)
        try:
            self.entity_collection = self.client.collections.get("university_entities_db")
        except Exception as e:
            logger.warning(f"University entities collection not found: {e}")
            self.entity_collection = None
            
        logger.info(f"Initialized UniversityPropertyRetrieval with model: {embedding_model_name}")

    def _search(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search the vector database for similar properties"""
        try:
            query_vector = self.model_embed.encode([q])[0]
            response = self.collection.query.hybrid(
                query=q,
                query_properties=["label"],
                vector=query_vector,
                return_metadata=weaviate.classes.query.MetadataQuery(score=True),
                limit=k,
            )
            
            # Convert to dataframe
            df = pd.DataFrame(
                [{**o.properties, "score": o.metadata.score} for o in response.objects]
            )
            return df
        except Exception as e:
            logger.error(f"Error in property search: {e}")
            return pd.DataFrame()

    def _search_entities(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search the vector database for similar entities"""
        try:
            if not self.entity_collection:
                return pd.DataFrame()
                
            query_vector = self.model_embed.encode([q])[0]
            response = self.entity_collection.query.hybrid(
                query=q,
                query_properties=["label"],
                vector=query_vector,
                return_metadata=weaviate.classes.query.MetadataQuery(score=True),
                limit=k,
            )
            
            # Convert to dataframe
            df = pd.DataFrame(
                [{**o.properties, "score": o.metadata.score} for o in response.objects]
            )
            return df
        except Exception as e:
            logger.error(f"Error in entity search: {e}")
            return pd.DataFrame()

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """Tokenize and preprocess the input query"""
        tokenizer = RegexpTokenizer(r"\w+")
        tokenized = tokenizer.tokenize(q)
        return [tok.lower() for tok in tokenized if tok.lower() not in self.stopwords]

    def _generate_ngrams(self, tokens: list[str]) -> list[str]:
        """Generate n-grams from a list of tokens"""
        max_n = min(len(tokens), 3)
        result = []
        for n in range(1, max_n + 1):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        return result

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity and property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams_list = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        # Search for properties
        for ngram in ngrams_list + property_candidates:
            df_res = self._search(ngram, k=k)
            if not df_res.empty:
                # For university properties, use appropriate format
                df_res["idWithLabel"] = df_res.get("propertyId", df_res.get("label", "")) + " - " + df_res["label"]
                filtered_results = df_res[df_res["score"] >= threshold]["idWithLabel"].tolist()
                if filtered_results:
                    result["properties"].extend(filtered_results)
                    result["properties"] = list(set(result["properties"]))

        # Search for entities using the entity collection
        for ngram in ngrams_list + [q]:
            df_res = self._search_entities(ngram, k=k)
            if not df_res.empty:
                # For entities, extract relevant information
                for _, row in df_res[df_res["score"] >= threshold].iterrows():
                    entity_data = {
                        "uri": row.get("short", row.get("label", "")),
                        "label": row.get("label", ""),
                        "score": float(row["score"])
                    }
                    if entity_data not in result["entities"]:
                        result["entities"].append(entity_data)

        result["properties"] = sorted(result["properties"])
        result["entities"] = sorted(result["entities"], key=lambda x: x.get("score", 0), reverse=True)[:k]
        return result