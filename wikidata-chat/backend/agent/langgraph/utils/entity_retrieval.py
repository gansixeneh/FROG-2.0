# backend/agent/langgraph/utils/entity_retrieval.py
import pandas as pd
import numpy as np
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

class UniversityEntityRetrieval:
    """Class for managing university entities retrieval and search via Weaviate"""
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
                self.client = weaviate.connect_to_local(
                    host="localhost",
                    port=8080,
                    grpc_port=50052,
                )
            except Exception as e:
                logger.error(f"Error connecting to local Weaviate: {e}")
                raise e
        
        # Get collection
        db_collection_name = "university_entities_db"
        if not self.client.collections.exists(db_collection_name):
            logger.error(f"Collection {db_collection_name} does not exist")
            raise ValueError(f"Collection {db_collection_name} does not exist")
        else:
            self.collection = self.client.collections.get(db_collection_name)
            
        logger.info(f"Initialized UniversityEntityRetrieval with model: {embedding_model_name}")

    def _search(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search the vector database for similar entities"""
        try:
            query_vector = self.model_embed.encode([q])[0]
            response = self.collection.query.hybrid(
                query=q,
                query_properties=["label", "description"],
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

    def get_related_entities(
        self,
        q: str,
        entity_candidates: list[str] = [],
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams_list = self._generate_ngrams(tokens)
        result = {"entities": []}

        # First, search for entity candidates if provided
        for entity in entity_candidates:
            df_res = self._search(entity, k=k)
            if not df_res.empty:
                df_res = df_res[df_res["score"] >= threshold]
                if not df_res.empty:
                    for _, row in df_res.iterrows():
                        entity_data = {
                            "uri": row.get("uri", ""),
                            "label": row.get("label", ""),
                            "description": row.get("description", ""),
                            "score": float(row["score"])
                        }
                        if entity_data not in result["entities"]:
                            result["entities"].append(entity_data)

        # Then search for n-grams if we don't have enough entities
        if len(result["entities"]) < k:
            for ngram in ngrams_list:
                df_res = self._search(ngram, k=k)
                if not df_res.empty:
                    df_res = df_res[df_res["score"] >= threshold]
                    if not df_res.empty:
                        for _, row in df_res.iterrows():
                            entity_data = {
                                "uri": row.get("uri", ""),
                                "label": row.get("label", ""),
                                "description": row.get("description", ""),
                                "score": float(row["score"])
                            }
                            if entity_data not in result["entities"]:
                                result["entities"].append(entity_data)
                                if len(result["entities"]) >= k:
                                    break
                if len(result["entities"]) >= k:
                    break

        # Sort entities by score
        result["entities"] = sorted(result["entities"], key=lambda x: x.get("score", 0), reverse=True)
        
        return result