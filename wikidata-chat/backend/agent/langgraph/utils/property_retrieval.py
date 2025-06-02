# backend/agent/langgraph/utils/property_retrieval.py
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
                self.client = weaviate.connect_to_local(
                    host="localhost",
                    port=8080,
                    grpc_port=50052,
                )
            except Exception as e:
                logger.error(f"Error connecting to local Weaviate: {e}")
                raise e
        
        # Get collection for university properties
        db_collection_name = "university_properties_db"
        if not self.client.collections.exists(db_collection_name):
            logger.error(f"Collection {db_collection_name} does not exist")
            raise ValueError(f"Collection {db_collection_name} does not exist")
        else:
            self.collection = self.client.collections.get(db_collection_name)
            
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
        threshold: float = 0.5,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams_list = self._generate_ngrams(tokens)
        result = {"properties": []}

        for ngram in ngrams_list + property_candidates:
            df_res = self._search(ngram, k=k)
            if not df_res.empty:
                # For university properties, use appropriate format
                df_res["idWithLabel"] = df_res.get("propertyId", df_res.get("label", "")) + " - " + df_res["label"]
                filtered_results = df_res[df_res["score"] >= threshold]["idWithLabel"].tolist()
                if filtered_results:
                    result["properties"].extend(filtered_results)
                    result["properties"] = list(set(result["properties"]))

        result["properties"] = sorted(result["properties"])
        return result

class WikidataPropertyRetrieval:
    """Class for managing Wikidata properties retrieval and search"""
    def __init__(
        self,
        df_properties: pd.DataFrame,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        weaviate_client=None
    ) -> None:
        self.df_properties = df_properties
        # Use the singleton instead of creating a new instance
        self.model_embed = get_sentence_transformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Create a dictionary for fast property ID to label lookups
        self.property_id_to_label = {}
        for _, row in df_properties.iterrows():
            prop_id = row.get('propertyId', '')
            label = row.get('label', '')
            if prop_id and label:
                self.property_id_to_label[prop_id] = label
        
        logger.info(f"Created property ID to label mapping with {len(self.property_id_to_label)} properties")
        
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
        
        # Create/get collection
        db_collection_name = "wikidata_property_db"
        if not self.client.collections.exists(db_collection_name):
            self.collection = self.client.collections.create(
                name=db_collection_name,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
            )
            self.is_collection_empty = True
        else:
            self.collection = self.client.collections.get(db_collection_name)
            self.is_collection_empty = False
            
        # Initialize collection with data if empty
        if self.is_collection_empty:
            self._initialize_collection()

    def _initialize_collection(self):
        """Initialize the vector collection with property data"""
        logger.info("Initializing Wikidata property collection...")
        emb_properties = self.model_embed.encode(
            self.df_properties["label"].tolist(), show_progress_bar=True
        )

        # Use the appropriate batch import method based on Weaviate version
        with self.collection.batch.dynamic() as batch:
            for i, row in self.df_properties.iterrows():
                batch.add_object(
                    properties=row.to_dict(),
                    vector=emb_properties[i].tolist(),
                )
        logger.info("Property collection initialized!")

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
        threshold: float = 0.5,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"properties": []}

        for ngram in ngrams + property_candidates:
            df_res = self._search(ngram, k=k)
            if not df_res.empty:
                df_res["idWithLabel"] = df_res["propertyId"] + " - " + df_res["label"]
                filtered_results = df_res[df_res["score"] >= threshold]["idWithLabel"].tolist()
                if filtered_results:
                    result["properties"].extend(filtered_results)
                    result["properties"] = list(set(result["properties"]))

        result["properties"] = sorted(result["properties"])

        return result
    """Class for managing Wikidata properties retrieval and search"""
    def __init__(
        self,
        df_properties: pd.DataFrame,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        weaviate_client=None
    ) -> None:
        self.df_properties = df_properties
        # Use the singleton instead of creating a new instance
        self.model_embed = get_sentence_transformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Create a dictionary for fast property ID to label lookups
        self.property_id_to_label = {}
        for _, row in df_properties.iterrows():
            prop_id = row.get('propertyId', '')
            label = row.get('label', '')
            if prop_id and label:
                self.property_id_to_label[prop_id] = label
        
        logger.info(f"Created property ID to label mapping with {len(self.property_id_to_label)} properties")
        
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
        
        # Create/get collection
        db_collection_name = "wikidata_property_db"
        if not self.client.collections.exists(db_collection_name):
            self.collection = self.client.collections.create(
                name=db_collection_name,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
            )
            self.is_collection_empty = True
        else:
            self.collection = self.client.collections.get(db_collection_name)
            self.is_collection_empty = False
            
        # Initialize collection with data if empty
        if self.is_collection_empty:
            self._initialize_collection()

    def _initialize_collection(self):
        """Initialize the vector collection with property data"""
        logger.info("Initializing Wikidata property collection...")
        emb_properties = self.model_embed.encode(
            self.df_properties["label"].tolist(), show_progress_bar=True
        )

        # Use the appropriate batch import method based on Weaviate version
        with self.collection.batch.dynamic() as batch:
            for i, row in self.df_properties.iterrows():
                batch.add_object(
                    properties=row.to_dict(),
                    vector=emb_properties[i].tolist(),
                )
        logger.info("Property collection initialized!")

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
        threshold: float = 0.5,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"properties": []}

        for ngram in ngrams + property_candidates:
            df_res = self._search(ngram, k=k)
            if not df_res.empty:
                df_res["idWithLabel"] = df_res["propertyId"] + " - " + df_res["label"]
                filtered_results = df_res[df_res["score"] >= threshold]["idWithLabel"].tolist()
                if filtered_results:
                    result["properties"].extend(filtered_results)
                    result["properties"] = list(set(result["properties"]))

        result["properties"] = sorted(result["properties"])

        return result