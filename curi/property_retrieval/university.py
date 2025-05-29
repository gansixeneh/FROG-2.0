import pandas as pd
from rdflib import Graph

from .base import BasePropertyRetrieval


class UniversityPropertyRetrieval(BasePropertyRetrieval):
    def __init__(
        self,
        turtle_file_path: str,
        get_entities_query: str,
        get_properties_query: str,
        embedding_model_name: str = "jinaai/jina-embeddings-v3",
        is_local_client: bool = True,
        weaviate_host: str = "localhost",
        weaviate_port: int = 8080,
    ) -> None:
        super().__init__(
            db_collection_name="university_property_db",
            embedding_model_name=embedding_model_name,
            is_local_client=is_local_client,
            weaviate_host=weaviate_host,
            weaviate_port=weaviate_port,
        )

        if self.is_collection_empty:
            print("Populating Weaviate with university course data...")
            self._populate_weaviate(turtle_file_path, get_entities_query, get_properties_query)

    def _populate_weaviate(self, turtle_file_path: str, get_entities_query: str, get_properties_query: str):
        """
        Populate Weaviate with entities and properties from the TTL file
        
        Args:
            turtle_file_path (str): Path to the TTL file
            get_entities_query (str): SPARQL query to get entities
            get_properties_query (str): SPARQL query to get properties
        """
        g = Graph().parse(turtle_file_path)
        
        # Execute queries to get entities and properties
        entity_response = g.query(get_entities_query)
        property_response = g.query(get_properties_query)
        
        # Convert to DataFrames
        df_entities = pd.DataFrame(entity_response.bindings)
        df_properties = pd.DataFrame(property_response.bindings)
        
        # Clean column names
        df_entities.columns = [str(col) for col in df_entities.columns]
        df_properties.columns = [str(col) for col in df_properties.columns]
        
        # Convert all values to strings
        for col in df_entities.columns:
            df_entities[col] = df_entities[col].apply(lambda x: str(x))
        
        for col in df_properties.columns:
            df_properties[col] = df_properties[col].apply(lambda x: str(x))
        
        print(f"Found {len(df_entities)} entities and {len(df_properties)} properties")
        
        # Generate embeddings
        print("Generating embeddings for entities...")
        emb_entities = self.model_embed.encode(
            df_entities["label"].tolist(), show_progress_bar=True
        )
        
        print("Generating embeddings for properties...")
        emb_properties = self.model_embed.encode(
            df_properties["label"].tolist(), show_progress_bar=True
        )
        
        # Prepare data for Weaviate
        university_df_vectors = {
            "entities": (df_entities, emb_entities),
            "properties": (df_properties, emb_properties),
        }
        
        # Batch insert into Weaviate
        print("Inserting data into Weaviate...")
        with self.collection.batch.dynamic() as batch:
            for key, (df, vector) in university_df_vectors.items():
                for i, row in df.iterrows():
                    properties_dict = {**row.to_dict(), "type": key}
                    
                    # Handle None values
                    for prop_key, prop_value in properties_dict.items():
                        if prop_value is None or str(prop_value).lower() == 'none':
                            properties_dict[prop_key] = ""
                    
                    batch.add_object(
                        properties=properties_dict,
                        vector=vector[i].tolist(),
                    )
        
        print("Data population completed!")

    def search_entities(self, q: str, k: int = 5) -> pd.DataFrame:
        """
        Search for entities
        
        Args:
            q (str): Query string
            k (int): Number of results to return
            
        Returns:
            pd.DataFrame: Search results
        """
        return self._search(q, type="entities", k=k)

    def search_properties(self, q: str, k: int = 5) -> pd.DataFrame:
        """
        Search for properties
        
        Args:
            q (str): Query string
            k (int): Number of results to return
            
        Returns:
            pd.DataFrame: Search results
        """
        return self._search(q, type="properties", k=k)

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.5,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """
        Get related entity and property candidates using n-grams and property candidates
        
        Args:
            q (str): Question string
            property_candidates (list[str]): List of property candidates
            threshold (float): Score threshold for relevance
            k (int): Number of results per search
            
        Returns:
            dict[str, list[str]]: Dictionary with 'entities' and 'properties' lists
        """
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, type, threshold=threshold):
            def format_result(x):
                if type == "properties":
                    # Get the full result for formatting
                    df_res = self._search(ngram, type=type, k=k)
                    if not df_res.empty:
                        record = df_res[df_res["short"] == x]
                        if not record.empty:
                            record_dict = record.iloc[0].to_dict()
                            domain = record_dict.get("shortDomain", "")
                            range_val = record_dict.get("shortRange", "")
                            
                            info = {}
                            if domain and domain != "":
                                info["domain"] = domain
                            if range_val and range_val != "":
                                info["range"] = range_val
                            
                            if info:
                                return f"{x}: {info}"
                            else:
                                return f"{x}: No domain and range"
                    return f"{x}: No domain and range"
                return x

            df_res = self._search(ngram, type=type, k=k)
            if df_res.empty:
                return type, []
            
            # Filter by threshold and format results
            filtered_df = df_res[df_res["score"] >= threshold]
            results = filtered_df["short"].apply(format_result).tolist()
            
            return type, results

        # Search using n-grams and property candidates
        search_terms = ngrams + property_candidates
        
        for term in search_terms:
            if len(term.strip()) >= 2:  # Only search meaningful terms
                for search_type in result.keys():
                    result_type, df_res = search(term, search_type)
                    if df_res:
                        result[result_type].extend(df_res)
                        # Remove duplicates while preserving order
                        result[result_type] = list(dict.fromkeys(result[result_type]))

        return result
