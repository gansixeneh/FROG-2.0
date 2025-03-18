import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON

class QueryEngine:
    def __init__(self, endpoint="https://query.wikidata.org/sparql"):
        """
        Initialize the QueryEngine with a SPARQL endpoint.
        
        Parameters:
        -----------
        endpoint : str
            The SPARQL endpoint URL (default is Wikidata's endpoint)
        """
        self.endpoint = endpoint
        self.sparql = SPARQLWrapper(endpoint)
        self.sparql.setReturnFormat(JSON)
        
    def run_query(self, query):
        """
        Execute a SPARQL query and return results as a pandas DataFrame.
        
        Parameters:
        -----------
        query : str
            The SPARQL query to execute
            
        Returns:
        --------
        pandas.DataFrame
            The query results in a DataFrame format
        """
        try:
            # Set the query and execute it
            self.sparql.setQuery(query)
            results = self.sparql.query().convert()
            
            # Extract the results
            bindings = results['results']['bindings']
            
            # If no results, return empty DataFrame
            if not bindings:
                return pd.DataFrame()
            
            # Transform the results into a DataFrame
            df = pd.json_normalize(bindings)
            
            # Clean up column names by removing .value suffix
            clean_columns = {}
            for col in df.columns:
                if col.endswith('.value'):
                    clean_columns[col] = col[:-6]
            
            # Rename columns if needed
            if clean_columns:
                df = df.rename(columns=clean_columns)
                
            # Keep only value columns
            value_cols = [col for col in df.columns if not col.endswith('.type') and not col.endswith('.xml:lang')]
            df = df[value_cols]
            
            return df
        
        except Exception as e:
            print(f"Error executing query: {e}")
            return pd.DataFrame()
