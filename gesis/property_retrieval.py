import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams
import weaviate
import logging
import os
from SPARQLWrapper import SPARQLWrapper, JSON
from kg_schema_extractor import gesis_entity_label, gesis_property_label

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
        is_local_client: bool = True,
        weaviate_host: str = "localhost",
        weaviate_port: int = 8080,
        weaviate_client=None,
        entities_csv_path: str = "data/gesis_entities.csv",
        properties_csv_path: str = "data/gesis_properties.csv"
    ) -> None:
        self.endpoint_url = endpoint_url
        self.entities_csv_path = entities_csv_path
        self.properties_csv_path = properties_csv_path
        
        # Initialize the embedding model
        self.model_embed = SentenceTransformer(embedding_model_name, trust_remote_code=True)
        self.stopwords = set(stopwords.words("english"))
        
        # Initialize SPARQL client (for fallback if CSV files not available)
        self.sparql_client = SPARQLWrapper(endpoint_url)
        self.sparql_client.setReturnFormat(JSON)
        
        # Load entities and properties from CSV files
        self.df_entities = self._load_entities()
        self.df_properties = self._load_properties()
        
        logger.info(f"Loaded {len(self.df_entities)} entities and {len(self.df_properties)} properties")
        
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
        self.entities_collection = self._setup_collection("gesis_entities_db", self.df_entities)
        self.properties_collection = self._setup_collection("gesis_properties_db", self.df_properties)

    def _load_entities(self):
        """Load entities from CSV file or fall back to SPARQL endpoint"""
        try:
            if os.path.exists(self.entities_csv_path):
                logger.info(f"Loading entities from {self.entities_csv_path}")
                return pd.read_csv(self.entities_csv_path)
            else:
                logger.warning(f"Entities CSV file {self.entities_csv_path} not found")
                logger.warning("Falling back to extracting entities from SPARQL endpoint")
                return self._extract_entities()
        except Exception as e:
            logger.error(f"Error loading entities from CSV: {e}")
            logger.warning("Falling back to extracting entities from SPARQL endpoint")
            return self._extract_entities()

    def _load_properties(self):
        """Load properties from CSV file or fall back to SPARQL endpoint"""
        try:
            if os.path.exists(self.properties_csv_path):
                logger.info(f"Loading properties from {self.properties_csv_path}")
                return pd.read_csv(self.properties_csv_path)
            else:
                logger.warning(f"Properties CSV file {self.properties_csv_path} not found")
                logger.warning("Falling back to extracting properties from SPARQL endpoint")
                return self._extract_properties()
        except Exception as e:
            logger.error(f"Error loading properties from CSV: {e}")
            logger.warning("Falling back to extracting properties from SPARQL endpoint")
            return self._extract_properties()

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
        """Extract entities from the SPARQL endpoint (fallback method)"""
        try:
            logger.info("Extracting entities from SPARQL endpoint...")
            results = self.execute_sparql_query(self.get_entities_query)
            logger.info("Results received from SPARQL endpoint")
            entities_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                for binding in results["results"]["bindings"]:
                    entity_uri = binding.get("entity", {}).get("value")
                    
                    if entity_uri:
                        # Try to get schema:name label first
                        label = self._get_entity_name(entity_uri)
                        if not label:
                            # Fallback to gesis_entity_label function
                            label = gesis_entity_label(entity_uri)
                        
                        # Generate short form using prefixes
                        short = self._shorten_uri(entity_uri)
                        
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
        """Extract properties from the SPARQL endpoint (fallback method)"""
        try:
            logger.info("Extracting properties from SPARQL endpoint...")
            results = self.execute_sparql_query(self.get_properties_query)
            logger.info("Results received from SPARQL endpoint")
            properties_data = []
            
            if results.get("results") and results["results"].get("bindings"):
                for binding in results["results"]["bindings"]:
                    property_uri = binding.get("property", {}).get("value")
                    
                    if property_uri:
                        # Try to get schema:name label first
                        label = self._get_property_name(property_uri)
                        if not label:
                            # Fallback to gesis_property_label function
                            label = gesis_property_label(property_uri)
                        
                        # Generate short form using prefixes
                        short = self._shorten_uri(property_uri)
                        
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

    def _get_entity_name(self, entity_uri):
        """Get the schema:name for an entity"""
        try:
            query = f"""
            PREFIX schema: <https://schema.org/>
            SELECT ?name WHERE {{
                <{entity_uri}> schema:name ?name .
            }}
            LIMIT 1
            """
            results = self.execute_sparql_query(query)
            
            if results.get("results") and results["results"].get("bindings"):
                name_binding = results["results"]["bindings"][0]
                return name_binding.get("name", {}).get("value")
            
            return None
        except Exception:
            return None

    def _get_property_name(self, property_uri):
        """Get the schema:name for a property"""
        try:
            query = f"""
            PREFIX schema: <https://schema.org/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?name WHERE {{
                {{
                    <{property_uri}> schema:name ?name .
                }} UNION {{
                    <{property_uri}> rdfs:label ?name .
                }}
            }}
            LIMIT 1
            """
            results = self.execute_sparql_query(query)
            
            if results.get("results") and results["results"].get("bindings"):
                name_binding = results["results"]["bindings"][0]
                return name_binding.get("name", {}).get("value")
            
            return None
        except Exception:
            return None

    def _shorten_uri(self, uri):
        """Shorten a URI using known prefixes"""
        prefixes = {
            "https://schema.org/": "schema:",
            "https://data.gesis.org/gesiskg/schema/": "gesiskg:",
            "https://data.gesis.org/gesiskg/": "gesis:",
            "https://rdf-vocabulary.ddialliance.org/discovery.html#": "disco:",
            "https://nfdi.fiz-karlsruhe.de/ontology/": "nfdicore:",
            "http://www.w3.org/2004/02/skos/core#": "skos:",
            "http://rdfs.org/ns/void#": "void:"
        }
        
        for namespace, prefix in prefixes.items():
            if uri.startswith(namespace):
                return prefix + uri[len(namespace):]
        
        return uri

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
            def format_result(x):
                return x  # No domain/range needed

            if search_type == "entities":
                df_res = self.search_entities(ngram, k=k)
            else:
                df_res = self.search_properties(ngram, k=k)
            
            if df_res.empty:
                return search_type, []
                
            result_list = (
                df_res[df_res["score"] >= threshold]["short"]
                .apply(format_result)
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