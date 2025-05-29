import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams
import weaviate
import logging
from rdflib import Graph

# Configure logging
logger = logging.getLogger(__name__)

class UniversityPropertyRetrieval:
    """Class for managing University course properties and entities retrieval and search"""
    
    def __init__(
        self,
        turtle_file_path: str,
        get_entities_query: str,
        get_properties_query: str,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        is_local_client: bool = True,
        weaviate_host: str = "localhost",
        weaviate_port: int = 8080,
        weaviate_client=None
    ) -> None:
        self.turtle_file_path = turtle_file_path
        self.get_entities_query = get_entities_query
        self.get_properties_query = get_properties_query
        
        # Initialize the embedding model
        self.model_embed = SentenceTransformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Load and parse the turtle file
        self.graph = Graph()
        self.graph.parse(turtle_file_path, format='turtle')
        logger.info(f"Loaded RDF graph with {len(self.graph)} triples")
        
        # Extract entities and properties from the graph
        self.df_entities = self._extract_entities()
        self.df_properties = self._extract_properties()
        
        logger.info(f"Extracted {len(self.df_entities)} entities and {len(self.df_properties)} properties")
        
        # Connect to Weaviate
        if weaviate_client:
            self.client = weaviate_client
        else:
            try:
                if is_local_client:
                    self.client = weaviate.connect_to_local(
                        host=weaviate_host,
                        port=weaviate_port,
                        grpc_port=50052,
                    )
                else:
                    # For cloud or custom connections
                    self.client = weaviate.Client(f"http://{weaviate_host}:{weaviate_port}")
            except Exception as e:
                logger.error(f"Error connecting to Weaviate: {e}")
                raise e
        
        # Create/get collections
        self.entities_collection = self._setup_collection("university_entities_db", self.df_entities)
        self.properties_collection = self._setup_collection("university_properties_db", self.df_properties)

    def _extract_entities(self):
        """Extract entities from the RDF graph using the provided SPARQL query"""
        try:
            results = list(self.graph.query(self.get_entities_query))
            entities_data = []
            
            for result in results:
                label = str(result[0]) if result[0] else ""
                short = str(result[1]) if result[1] else ""
                
                if label or short:
                    entities_data.append({
                        'label': label,
                        'short': short
                    })
            
            df = pd.DataFrame(entities_data)
            logger.info(f"Extracted {len(df)} entities from RDF graph")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return pd.DataFrame(columns=['label', 'short'])

    def _extract_properties(self):
        """Extract properties from the RDF graph using the provided SPARQL query"""
        try:
            results = list(self.graph.query(self.get_properties_query))
            properties_data = []
            
            for result in results:
                label = str(result[0]) if result[0] else ""
                short = str(result[1]) if result[1] else ""
                short_domain = str(result[2]) if len(result) > 2 and result[2] else ""
                short_range = str(result[3]) if len(result) > 3 and result[3] else ""
                
                if label or short:
                    properties_data.append({
                        'label': label,
                        'short': short,
                        'shortDomain': short_domain,
                        'shortRange': short_range
                    })
            
            df = pd.DataFrame(properties_data)
            logger.info(f"Extracted {len(df)} properties from RDF graph")
            return df
            
        except Exception as e:
            logger.error(f"Error extracting properties: {e}")
            return pd.DataFrame(columns=['label', 'short', 'shortDomain', 'shortRange'])

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
        """Get related entity and property candidates for a query"""
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        # Search entities
        for ngram in ngrams + property_candidates:
            df_res = self.search_entities(ngram, k=k)
            if not df_res.empty:
                filtered_results = df_res[df_res["score"] >= threshold]["short"].tolist()
                if filtered_results:
                    result["entities"].extend(filtered_results)
                    result["entities"] = list(set(result["entities"]))

        # Search properties
        for ngram in ngrams + property_candidates:
            df_res = self.search_properties(ngram, k=k)
            if not df_res.empty:
                # Format properties with domain and range info
                for _, row in df_res[df_res["score"] >= threshold].iterrows():
                    short = row["short"]
                    domain = row.get("shortDomain", "")
                    range_val = row.get("shortRange", "")
                    
                    if domain and range_val:
                        formatted = f"{short}: {{'domain': '{domain}', 'range': '{range_val}'}}"
                    else:
                        formatted = f"{short}: No domain and range"
                    
                    result["properties"].append(formatted)
                
                result["properties"] = list(set(result["properties"]))

        result["entities"] = sorted(result["entities"])
        result["properties"] = sorted(result["properties"])

        return result

    def close(self):
        """Close the Weaviate client connection"""
        if hasattr(self.client, 'close'):
            self.client.close()
