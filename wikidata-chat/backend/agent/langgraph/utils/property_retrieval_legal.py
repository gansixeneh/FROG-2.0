# backend/agent/langgraph/utils/property_retrieval_legal.py
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

from .kg_schema_extractor import legal_entity_label, legal_property_label
from .singletons.model_singletons import get_sentence_transformer

# Configure logging
logger = logging.getLogger(__name__)

class LegalPropertyRetrieval:
    """Class for managing Legal document properties and entities retrieval and search"""
    
    # Define SPARQL queries for entities and properties
    get_entities_query = """
PREFIX lex2kg-o: <https://example.org/lex2kg/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?entity
WHERE {
  { 
    ?entity ?predicate ?object. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), "https://example.org/lex2kg/") && STRSTARTS(STR(?predicate), STR(lex2kg-o:)))
  }
  UNION
  { 
    ?subject ?predicate ?entity. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), "https://example.org/lex2kg/") && STRSTARTS(STR(?predicate), STR(lex2kg-o:)))
  }
}
"""
        
    get_properties_query = """
PREFIX lex2kg-o: <https://example.org/lex2kg/ontology/>

SELECT DISTINCT
    ?property
WHERE {
  ?subject ?property ?object.
  FILTER(STRSTARTS(STR(?property), STR(lex2kg-o:)))
}
"""
    
    def __init__(
        self,
        endpoint_url: str = "http://localhost:3030/modified-lex2kg/query",
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        weaviate_client=None
    ) -> None:
        self.endpoint_url = endpoint_url
        
        # Use the singleton instead of creating a new instance
        self.model_embed = get_sentence_transformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Initialize SPARQL client
        self.sparql_client = SPARQLWrapper(endpoint_url)
        self.sparql_client.setReturnFormat(JSON)
        
        # Extract entities and properties from the endpoint
        self.df_entities = self._extract_entities()
        self.df_properties = self._extract_properties()
        
        logger.info(f"Extracted {len(self.df_entities)} entities and {len(self.df_properties)} properties")
        
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
        
        # Create/get collections
        self.entities_collection = self._setup_collection("legal_entities_db", self.df_entities)
        self.properties_collection = self._setup_collection("legal_properties_db", self.df_properties)

    def execute_sparql_query(self, query):
        """Execute a SPARQL query against the configured endpoint"""
        try:
            self.sparql_client.setQuery(query)
            results = self.sparql_client.query().convert()
            return results
        except Exception as e:
            logger.error(f"Error executing SPARQL query: {e}")
            raise e

    def _extract_entities(self):
        """Extract entities from the SPARQL endpoint using the provided SPARQL query"""
        try:
            results = self.execute_sparql_query(self.get_entities_query)
            entities_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                for binding in results["results"]["bindings"]:
                    entity_uri = binding.get("entity", {}).get("value")
                    
                    if entity_uri:
                        # Generate label using legal_entity_label function
                        label = legal_entity_label(entity_uri)
                        # Generate short form (remove base URI)
                        if entity_uri.startswith("https://example.org/lex2kg/"):
                            short = "lex2kg:" + entity_uri.replace("https://example.org/lex2kg/", "")
                        else:
                            short = entity_uri
                        
                        entities_data.append({
                            'label': label,
                            'short': short,
                            'uri': entity_uri
                        })
            
            df = pd.DataFrame(entities_data)
            logger.info(f"Extracted {len(df)} entities from SPARQL endpoint")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return pd.DataFrame(columns=['label', 'short', 'uri'])

    def _extract_properties(self):
        """Extract properties from the SPARQL endpoint using the provided SPARQL query"""
        try:
            results = self.execute_sparql_query(self.get_properties_query)
            properties_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                for binding in results["results"]["bindings"]:
                    property_uri = binding.get("property", {}).get("value")
                    
                    if property_uri:
                        # Generate label using legal_property_label function
                        label = legal_property_label(property_uri)
                        # Generate short form (remove base ontology URI)
                        if property_uri.startswith("https://example.org/lex2kg/ontology/"):
                            short = "lex2kg-o:" + property_uri.replace("https://example.org/lex2kg/ontology/", "")
                        else:
                            short = property_uri
                        
                        properties_data.append({
                            'label': label,
                            'short': short,
                            'uri': property_uri
                        })
            
            df = pd.DataFrame(properties_data)
            logger.info(f"Extracted {len(df)} properties from SPARQL endpoint")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting properties: {e}")
            return pd.DataFrame(columns=['label', 'short', 'uri'])

    def _setup_collection(self, collection_name: str, df: pd.DataFrame):
        """Setup Weaviate collection for entities or properties"""
        if not self.client.collections.exists(collection_name):
            collection = self.client.collections.create(
                name=collection_name,
                vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
            )
            is_empty = True
        else:
            collection = self.client.collections.get(collection_name)
            is_empty = False
            
        # Initialize collection with data if empty
        if is_empty:
            self._initialize_collection(collection, df)
            
        return collection

    def _initialize_collection(self, collection, df: pd.DataFrame):
        """Initialize the vector collection with data"""
        logger.info(f"Initializing collection with {len(df)} items...")
        
        if len(df) == 0:
            logger.warning("No data to initialize collection")
            return
            
        # Generate embeddings for labels
        labels = df["label"].fillna("").tolist()
        embeddings = self.model_embed.encode(labels, show_progress_bar=True)

        # Use batch import
        with collection.batch.dynamic() as batch:
            for i, row in df.iterrows():
                batch.add_object(
                    properties=row.to_dict(),
                    vector=embeddings[i].tolist(),
                )
        logger.info("Collection initialized!")

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
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """Get related entity and property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type, threshold=threshold):
            if search_type == "entities":
                df_res = self.search_entities(ngram, k=k)
            else:
                df_res = self.search_properties(ngram, k=k)
            
            if df_res.empty:
                return search_type, []
                
            result_list = (
                df_res[df_res["score"] >= threshold]["short"]
                .tolist()
            )
            return search_type, result_list

        for ngram in ngrams + property_candidates:
            for search_type in result.keys():
                search_result_type, df_res = search(ngram, search_type)
                if df_res:
                    result[search_result_type].extend(df_res)
                    result[search_result_type] = list(set(result[search_result_type]))

        return result

    def close(self):
        """Close the Weaviate client connection"""
        if hasattr(self.client, 'close'):
            self.client.close()
