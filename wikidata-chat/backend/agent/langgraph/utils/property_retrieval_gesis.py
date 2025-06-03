# backend/agent/langgraph/utils/property_retrieval_gesis.py
import logging
import os
import weaviate
from SPARQLWrapper import SPARQLWrapper, JSON
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

from .kg_schema_extractor import gesis_entity_label, gesis_property_label
from .singletons.model_singletons import get_sentence_transformer

# Configure logging
logger = logging.getLogger(__name__)

class GesisPropertyRetrieval:
    """Class for managing GESIS knowledge graph properties and entities retrieval and search"""
    
    # Define SPARQL queries as fallbacks when CSV files are not available
    get_entities_query = """
PREFIX schema: <https://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/>
PREFIX disco: <https://rdf-vocabulary.ddialliance.org/discovery.html#>
PREFIX nfdicore: <https://nfdi.fiz-karlsruhe.de/ontology/>

SELECT DISTINCT ?entity
WHERE {
  { 
    ?entity ?predicate ?object. 
    FILTER(isIRI(?entity))
  }
  UNION
  { 
    ?subject ?predicate ?entity. 
    FILTER(isIRI(?entity))
  }
}
"""        
    get_properties_query = """
PREFIX schema: <https://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/>
PREFIX disco: <https://rdf-vocabulary.ddialliance.org/discovery.html#>
PREFIX nfdicore: <https://nfdi.fiz-karlsruhe.de/ontology/>

SELECT DISTINCT ?property
WHERE {
  ?subject ?property ?object.
  FILTER(
    STRSTARTS(STR(?property), "https://schema.org/") ||
    STRSTARTS(STR(?property), "https://data.gesis.org/gesiskg/schema/") ||
    STRSTARTS(STR(?property), "https://rdf-vocabulary.ddialliance.org/") ||
    STRSTARTS(STR(?property), "https://nfdi.fiz-karlsruhe.de/")
  )
}
"""    
    def __init__(
        self,
        endpoint_url: str = "http://localhost:3030/gesis/query",
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        weaviate_client=None,
        entities_csv_path: str = None,
        properties_csv_path: str = None
    ) -> None:
        self.endpoint_url = endpoint_url
        self.entities_csv_path = entities_csv_path
        self.properties_csv_path = properties_csv_path
        
        # Use the singleton instead of creating a new instance
        self.model_embed = get_sentence_transformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Initialize SPARQL client (for fallback if needed)
        self.sparql_client = SPARQLWrapper(endpoint_url)
        self.sparql_client.setReturnFormat(JSON)
        
        logger.info(f"Initialized GesisPropertyRetrieval for endpoint: {endpoint_url}")
        
        # Connect to Weaviate
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
        
        # Get collections (assume data is already loaded)
        self.entities_collection = self.client.collections.get("gesis_entities_db")
        self.properties_collection = self.client.collections.get("gesis_properties_db")

    def execute_sparql_query(self, query):
        """Execute a SPARQL query against the configured endpoint"""
        try:
            self.sparql_client.setQuery(query)
            results = self.sparql_client.query().convert()
            return results
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            raise e

    def search_entities(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search entities using hybrid search"""
        return self._search(self.entities_collection, q, k)

    def search_properties(self, q: str, k: int = 5) -> pd.DataFrame:
        """Search properties using hybrid search"""
        return self._search(self.properties_collection, q, k)
    def _search(self, collection, q: str, k: int = 5) -> pd.DataFrame:
        """Search the vector collection for similar items"""
        try:
            query_vector = self.model_embed.encode([q])[0]
            response = collection.query.hybrid(
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
            logger.error(f"Error in search: {e}")
            return pd.DataFrame()

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """Tokenize and preprocess the input query using NLTK RegexpTokenizer"""
        tok_pattern = r"\w+"
        tokenizer = RegexpTokenizer(tok_pattern)
        tokenized = tokenizer.tokenize(q)
        result = []
        for tok in tokenized:
            tok = tok.lower()
            if tok not in self.stopwords:
                result.append(tok)
        return result
    def _generate_ngrams(self, tokens: list[str]) -> list[str]:
        """Generate n-grams from a list of tokens using NLTK"""
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
        threshold: float = 0.65,  # Default threshold for properties in GESIS is 0.65
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity and property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}
        
        # Search for properties with threshold 0.65
        property_threshold = 0.65
        for ngram in ngrams + property_candidates:
            df_res = self.search_properties(ngram, k=k)
            if not df_res.empty:
                # Format properties like curriculum with idWithLabel
                for _, row in df_res[df_res["score"] >= property_threshold].iterrows():
                    # Create idWithLabel format like curriculum
                    id_with_label = f"{row['short']} - {row['label']}"
                    if id_with_label not in result["properties"]:
                        result["properties"].append(id_with_label)

        # Search for entities with threshold 0.7
        entity_threshold = 0.7
        for ngram in ngrams + [q]:
            df_res = self.search_entities(ngram, k=k)
            if not df_res.empty:
                # Format entities
                for _, row in df_res[df_res["score"] >= entity_threshold].iterrows():
                    entity_data = {
                        "uri": row.get("short", row.get("uri", "")),
                        "label": row.get("label", ""),
                        "score": float(row["score"])
                    }
                    if entity_data not in result["entities"]:
                        result["entities"].append(entity_data)
        
        # Sort the results
        result["properties"] = sorted(result["properties"])
        result["entities"] = sorted(result["entities"], key=lambda x: x.get("score", 0), reverse=True)[:k]
        return result

    def close(self):
        """Close the Weaviate client connection"""
        if hasattr(self.client, 'close'):
            self.client.close()