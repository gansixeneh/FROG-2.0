import pandas as pd
import requests
from tqdm import tqdm
import time
from query_engine import QueryEngine

class EntityPropertyRetrieval:
    def __init__(self):
        """
        Initialize the EntityPropertyRetrieval class to search Wikidata entities and properties.
        Uses the Wikidata API directly without local storage.
        """
        self.query_engine = QueryEngine()  # For SPARQL queries if needed
        self.wikidata_api_url = "https://www.wikidata.org/w/api.php"
        
    def search_entities(self, query_text, limit=10):
        """
        Search for Wikidata entities based on text query using Wikidata API.

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
        try:
            # Prepare API parameters
            params = {
                'action': 'wbsearchentities',
                'search': query_text,
                'language': 'en',
                'format': 'json',
                'limit': limit
            }
            
            # Make API request
            response = requests.get(self.wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract entity information
            results = []
            for entity in data.get('search', []):
                results.append({
                    'entity_id': entity.get('id', ''),
                    'label': entity.get('label', ''),
                    'description': entity.get('description', '')
                })
                
            return pd.DataFrame(results)
            
        except Exception as e:
            print(f"Error searching entities: {e}")
            return pd.DataFrame(columns=["entity_id", "label", "description"])

    def search_properties(self, query_text, limit=10):
        """
        Search for Wikidata properties based on text query using Wikidata API.

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
        try:
            # Prepare API parameters
            params = {
                'action': 'wbsearchentities',
                'search': query_text,
                'type': 'property',
                'language': 'en',
                'format': 'json',
                'limit': limit
            }
            
            # Make API request
            response = requests.get(self.wikidata_api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Extract property information
            results = []
            for prop in data.get('search', []):
                results.append({
                    'property_id': prop.get('id', ''),
                    'label': prop.get('label', ''),
                    'description': prop.get('description', '')
                })
                
            return pd.DataFrame(results)
            
        except Exception as e:
            print(f"Error searching properties: {e}")
            return pd.DataFrame(columns=["property_id", "label", "description"])

    def get_entity_details(self, entity_id):
        """
        Get detailed information about a specific entity.
        
        Parameters:
        -----------
        entity_id : str
            Wikidata entity ID (Q number)
            
        Returns:
        --------
        dict
            Entity details
        """
        try:
            params = {
                'action': 'wbgetentities',
                'ids': entity_id,
                'languages': 'en',
                'format': 'json'
            }
            
            response = requests.get(self.wikidata_api_url, params=params)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error getting entity details: {e}")
            return {}

if __name__ == "__main__":
    # Initialize the retrieval system
    retriever = EntityPropertyRetrieval()

    # Search for entities
    entity_results = retriever.search_entities("lebron james")
    print("Top entity matches:")
    print(entity_results)

    # Search for properties
    property_results = retriever.search_properties("date of birth")
    print("\nTop property matches:")
    print(property_results)