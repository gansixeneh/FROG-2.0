import weaviate
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import uuid
import time
import os

from query_engine import QueryEngine


class EntityPropertyRetrieval:
    def __init__(
        self,
        weaviate_url,
        weaviate_api_key,
        model_name="jina-embeddings-v3",
        batch_size=100,
        data_dir="data",
    ):
        """
        Initialize the EntityPropertyRetrieval class with Weaviate.io connection.

        Parameters:
        -----------
        weaviate_url : str
            URL of your Weaviate.io cluster
        weaviate_api_key : str
            API key for Weaviate.io
        model_name : str
            Name of the sentence transformer model to use for embeddings
        batch_size : int
            Batch size for adding data to Weaviate
        data_dir : str
            Directory to store CSV files
        """
        # Connect to Weaviate.io
        self.client = weaviate.Client(
            url=weaviate_url,
            auth_client_secret=weaviate.AuthApiKey(api_key=weaviate_api_key),
        )
        self.model = SentenceTransformer(model_name)
        self.batch_size = batch_size
        self.query_engine = QueryEngine()  # Assuming QueryEngine is defined elsewhere

        # Set up data directory and file paths
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.entities_csv_path = os.path.join(self.data_dir, "wikidata_entities.csv")
        self.properties_csv_path = os.path.join(
            self.data_dir, "wikidata_properties.csv"
        )

        # Create schema if it doesn't exist and load data if needed
        self._create_schema_if_not_exists()

        # Check if data needs to be loaded
        entity_count = self._get_entity_count()
        property_count = self._get_property_count()

        if entity_count == 0:
            self.load_entities_if_needed()
        else:
            print(
                f"Found {entity_count} entities in Weaviate. Skipping entity loading."
            )

        if property_count == 0:
            self.load_properties_if_needed()
        else:
            print(
                f"Found {property_count} properties in Weaviate. Skipping property loading."
            )

    def _create_schema_if_not_exists(self):
        """Create Wikidata entity and property schemas in Weaviate if they don't exist."""
        schema = self.client.schema.get()
        classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []

        # Create Entity class if it doesn't exist
        if "WikidataEntity" not in classes:
            entity_class = {
                "class": "WikidataEntity",
                "description": "Wikidata entities with embeddings",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "entity_id",
                        "dataType": ["string"],
                        "description": "Wikidata entity ID (Q...)",
                    },
                    {
                        "name": "label",
                        "dataType": ["string"],
                        "description": "Entity label",
                    },
                    {
                        "name": "description",
                        "dataType": ["string"],
                        "description": "Entity description",
                    },
                ],
            }
            self.client.schema.create_class(entity_class)
            print("Created WikidataEntity class in Weaviate")

        # Create Property class if it doesn't exist
        if "WikidataProperty" not in classes:
            property_class = {
                "class": "WikidataProperty",
                "description": "Wikidata properties with embeddings",
                "vectorizer": "none",  # We'll provide our own vectors
                "properties": [
                    {
                        "name": "property_id",
                        "dataType": ["string"],
                        "description": "Wikidata property ID (P...)",
                    },
                    {
                        "name": "label",
                        "dataType": ["string"],
                        "description": "Property label",
                    },
                    {
                        "name": "description",
                        "dataType": ["string"],
                        "description": "Property description",
                    },
                ],
            }
            self.client.schema.create_class(property_class)
            print("Created WikidataProperty class in Weaviate")

    def _get_entity_count(self):
        """Get the count of entities in Weaviate."""
        try:
            result = (
                self.client.query.aggregate("WikidataEntity").with_meta_count().do()
            )
            return result["data"]["Aggregate"]["WikidataEntity"][0]["meta"]["count"]
        except Exception as e:
            print(f"Error getting entity count: {e}")
            return 0

    def _get_property_count(self):
        """Get the count of properties in Weaviate."""
        try:
            result = (
                self.client.query.aggregate("WikidataProperty").with_meta_count().do()
            )
            return result["data"]["Aggregate"]["WikidataProperty"][0]["meta"]["count"]
        except Exception as e:
            print(f"Error getting property count: {e}")
            return 0

    def _csv_exists(self, file_path):
        """Check if a CSV file exists and is not empty."""
        return os.path.isfile(file_path) and os.path.getsize(file_path) > 0

    def _query_and_save_entities(self, batch_limit=1000):
        """Query Wikidata for entities and save to CSV file."""
        print("Querying Wikidata for entities...")

        all_entities = []
        offset = 0
        total_fetched = 0

        while True:
            # Query to get entities with labels and descriptions in batches
            query = f"""
            SELECT ?entity ?entityLabel ?entityDescription
            WHERE {{
              ?entity wdt:P31 ?instance .
              SERVICE wikibase:label {{ 
                bd:serviceParam wikibase:language "en" . 
                ?entity rdfs:label ?entityLabel .
                ?entity schema:description ?entityDescription .
              }}
            }}
            LIMIT {batch_limit}
            OFFSET {offset}
            """

            # Get entities from Wikidata
            df = self.query_engine.run_query(query)
            if df.empty:
                print(
                    f"No more entities found or reached API limit. Total fetched: {total_fetched}"
                )
                break

            # Clean entity IDs to extract Q numbers
            df["entity_id"] = df["entity"].str.extract(r"(Q\d+)")

            # Add to our collection
            all_entities.append(df[["entity_id", "entityLabel", "entityDescription"]])

            total_fetched += len(df)
            print(f"Fetched batch of {len(df)} entities. Total so far: {total_fetched}")

            # Increment offset for next batch
            offset += batch_limit

            # Add a delay between batches to avoid rate limiting
            time.sleep(2)

        # Combine all batches and save to CSV
        if all_entities:
            final_df = pd.concat(all_entities)
            final_df.rename(
                columns={"entityLabel": "label", "entityDescription": "description"},
                inplace=True,
            )
            final_df.to_csv(self.entities_csv_path, index=False)
            print(f"Saved {len(final_df)} entities to {self.entities_csv_path}")
            return final_df
        else:
            print("No entities were fetched from Wikidata.")
            return pd.DataFrame(columns=["entity_id", "label", "description"])

    def _query_and_save_properties(self, batch_limit=1000):
        """Query Wikidata for properties and save to CSV file."""
        print("Querying Wikidata for properties...")

        all_properties = []
        offset = 0
        total_fetched = 0

        while True:
            # Query to get properties with labels and descriptions in batches
            query = f"""
            SELECT ?property ?propertyLabel ?propertyDescription
            WHERE {{
              ?property a wikibase:Property .
              SERVICE wikibase:label {{ 
                bd:serviceParam wikibase:language "en" . 
                ?property rdfs:label ?propertyLabel .
                ?property schema:description ?propertyDescription .
              }}
            }}
            LIMIT {batch_limit}
            OFFSET {offset}
            """

            # Get properties from Wikidata
            df = self.query_engine.run_query(query)
            if df.empty:
                print(
                    f"No more properties found or reached API limit. Total fetched: {total_fetched}"
                )
                break

            # Clean property IDs to extract P numbers
            df["property_id"] = df["property"].str.extract(r"(P\d+)")

            # Add to our collection
            all_properties.append(
                df[["property_id", "propertyLabel", "propertyDescription"]]
            )

            total_fetched += len(df)
            print(
                f"Fetched batch of {len(df)} properties. Total so far: {total_fetched}"
            )

            # Increment offset for next batch
            offset += batch_limit

            # Add a delay between batches to avoid rate limiting
            time.sleep(2)

        # Combine all batches and save to CSV
        if all_properties:
            final_df = pd.concat(all_properties)
            final_df.rename(
                columns={
                    "propertyLabel": "label",
                    "propertyDescription": "description",
                },
                inplace=True,
            )
            final_df.to_csv(self.properties_csv_path, index=False)
            print(f"Saved {len(final_df)} properties to {self.properties_csv_path}")
            return final_df
        else:
            print("No properties were fetched from Wikidata.")
            return pd.DataFrame(columns=["property_id", "label", "description"])

    def _load_entities_to_weaviate(self, df):
        """Load entities from DataFrame to Weaviate."""
        print(f"Loading {len(df)} entities to Weaviate...")

        with self.client.batch as batch:
            batch.batch_size = self.batch_size

            for i, row in tqdm(
                df.iterrows(), total=len(df), desc="Adding entities to Weaviate"
            ):
                # Skip if missing data
                if pd.isna(row["label"]) or pd.isna(row["entity_id"]):
                    continue

                # Create text for embedding
                text = f"{row['label']}"
                if not pd.isna(row["description"]):
                    text += f": {row['description']}"

                # Generate embedding
                embedding = self.model.encode(text)

                # Add to Weaviate
                entity_object = {
                    "entity_id": row["entity_id"],
                    "label": row["label"],
                    "description": (
                        row["description"] if not pd.isna(row["description"]) else ""
                    ),
                }

                batch.add_data_object(
                    data_object=entity_object,
                    class_name="WikidataEntity",
                    uuid=uuid.uuid5(uuid.NAMESPACE_DNS, row["entity_id"]),
                    vector=embedding,
                )

                # Small delay to prevent overloading
                if i % 100 == 0:
                    time.sleep(0.1)

    def _load_properties_to_weaviate(self, df):
        """Load properties from DataFrame to Weaviate."""
        print(f"Loading {len(df)} properties to Weaviate...")

        with self.client.batch as batch:
            batch.batch_size = self.batch_size

            for i, row in tqdm(
                df.iterrows(), total=len(df), desc="Adding properties to Weaviate"
            ):
                # Skip if missing data
                if pd.isna(row["label"]) or pd.isna(row["property_id"]):
                    continue

                # Create text for embedding
                text = f"{row['label']}"
                if not pd.isna(row["description"]):
                    text += f": {row['description']}"

                # Generate embedding
                embedding = self.model.encode(text)

                # Add to Weaviate
                property_object = {
                    "property_id": row["property_id"],
                    "label": row["label"],
                    "description": (
                        row["description"] if not pd.isna(row["description"]) else ""
                    ),
                }

                batch.add_data_object(
                    data_object=property_object,
                    class_name="WikidataProperty",
                    uuid=uuid.uuid5(uuid.NAMESPACE_DNS, row["property_id"]),
                    vector=embedding,
                )

                # Small delay to prevent overloading
                if i % 100 == 0:
                    time.sleep(0.1)

    def load_entities_if_needed(self, batch_limit=1000):
        """
        Load Wikidata entities into Weaviate, using CSV cache if available.

        Parameters:
        -----------
        batch_limit : int
            Number of entities to fetch in each batch from Wikidata
        """
        if self._csv_exists(self.entities_csv_path):
            print(f"Loading entities from existing CSV file: {self.entities_csv_path}")
            df = pd.read_csv(self.entities_csv_path)
            self._load_entities_to_weaviate(df)
        else:
            print("No cached entity data found. Querying Wikidata...")
            df = self._query_and_save_entities(batch_limit)
            self._load_entities_to_weaviate(df)

    def load_properties_if_needed(self, batch_limit=1000):
        """
        Load Wikidata properties into Weaviate, using CSV cache if available.

        Parameters:
        -----------
        batch_limit : int
            Number of properties to fetch in each batch from Wikidata
        """
        if self._csv_exists(self.properties_csv_path):
            print(
                f"Loading properties from existing CSV file: {self.properties_csv_path}"
            )
            df = pd.read_csv(self.properties_csv_path)
            self._load_properties_to_weaviate(df)
        else:
            print("No cached property data found. Querying Wikidata...")
            df = self._query_and_save_properties(batch_limit)
            self._load_properties_to_weaviate(df)

    def search_entities(self, query_text, limit=10):
        """
        Search for Wikidata entities based on text query.

        Parameters:
        -----------
        query_text : str
            Text to search for
        limit : int
            Maximum number of results to return

        Returns:
        --------
        pandas.DataFrame
            Top matching entities
        """
        # Generate embedding for query
        query_embedding = self.model.encode(query_text)

        # Search Weaviate
        result = (
            self.client.query.get(
                "WikidataEntity", ["entity_id", "label", "description"]
            )
            .with_near_vector({"vector": query_embedding})
            .with_limit(limit)
            .do()
        )

        # Convert to DataFrame
        if (
            "data" in result
            and "Get" in result["data"]
            and "WikidataEntity" in result["data"]["Get"]
        ):
            entities = result["data"]["Get"]["WikidataEntity"]
            if entities:
                return pd.DataFrame(entities)

        return pd.DataFrame(columns=["entity_id", "label", "description"])

    def search_properties(self, query_text, limit=10):
        """
        Search for Wikidata properties based on text query.

        Parameters:
        -----------
        query_text : str
            Text to search for
        limit : int
            Maximum number of results to return

        Returns:
        --------
        pandas.DataFrame
            Top matching properties
        """
        # Generate embedding for query
        query_embedding = self.model.encode(query_text)

        # Search Weaviate
        result = (
            self.client.query.get(
                "WikidataProperty", ["property_id", "label", "description"]
            )
            .with_near_vector({"vector": query_embedding})
            .with_limit(limit)
            .do()
        )

        # Convert to DataFrame
        if (
            "data" in result
            and "Get" in result["data"]
            and "WikidataProperty" in result["data"]["Get"]
        ):
            properties = result["data"]["Get"]["WikidataProperty"]
            if properties:
                return pd.DataFrame(properties)

        return pd.DataFrame(columns=["property_id", "label", "description"])


if __name__ == "__main__":
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    # Initialize the retrieval system with Weaviate.io credentials from environment variables
    retriever = EntityPropertyRetrieval(
        weaviate_url=os.getenv(
            "WEAVIATE_URL"
        ),  # e.g., "https://your-cluster-id.weaviate.cloud"
        weaviate_api_key=os.getenv("WEAVIATE_API_KEY"),  # Your Weaviate.io API key
    )

    # The initialization will automatically load entities and properties if needed

    # Search for entities
    entity_results = retriever.search_entities(
        "scientist who developed theory of relativity"
    )
    print("Top entity matches:")
    print(entity_results)

    # Search for properties
    property_results = retriever.search_properties("date of birth")
    print("\nTop property matches:")
    print(property_results)
