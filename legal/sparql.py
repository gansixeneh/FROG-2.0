"""
SPARQL Query Executor for Legal Dataset
This script provides functionality to execute SPARQL queries against an RDF dataset.
It supports both local RDF files and remote SPARQL endpoints.
"""

import rdflib
from rdflib import Graph, Namespace
from SPARQLWrapper import SPARQLWrapper, JSON
import json
import pandas as pd
from tabulate import tabulate  # For nice table output (pip install tabulate)
import os


class SparqlExecutor:
    """A class to execute SPARQL queries against various RDF sources."""
    
    def __init__(self, source=None, source_format="turtle"):
        """
        Initialize the SPARQL executor.
        
        Args:
            source (str): Path to RDF file or URL of SPARQL endpoint
            source_format (str): Format of the RDF file (e.g., "turtle", "xml", "n3")
        """
        self.source = source
        self.source_format = source_format
        self.graph = None
        self.endpoint = None
        
        # Initialize based on source type
        if source:
            if source.startswith(('http://', 'https://')):
                # It's a remote endpoint
                self.endpoint = SPARQLWrapper(source)
                self.endpoint.setReturnFormat(JSON)
            else:
                # It's a local file
                if os.path.exists(source):
                    self.graph = Graph()
                    self.graph.parse(source, format=source_format)
                else:
                    raise FileNotFoundError(f"RDF file not found: {source}")
    
    def load_rdf_string(self, rdf_content, format="turtle"):
        """
        Load RDF data from a string.
        
        Args:
            rdf_content (str): RDF data as string
            format (str): Format of the RDF data
        """
        self.graph = Graph()
        self.graph.parse(data=rdf_content, format=format)
        return self
    
    def execute_query(self, query, return_format="pandas"):
        """
        Execute a SPARQL query and return results.
        
        Args:
            query (str): SPARQL query to execute
            return_format (str): Format to return results in ("pandas", "dict", or "raw")
            
        Returns:
            Results in the specified format
        """
        if self.graph:
            # Execute against local graph
            results = self.graph.query(query)
            return self._format_results(results, return_format)
        elif self.endpoint:
            # Execute against remote endpoint
            self.endpoint.setQuery(query)
            results = self.endpoint.query().convert()
            return self._format_remote_results(results, return_format)
        else:
            raise ValueError("No RDF graph or SPARQL endpoint available. Please initialize with a source or load data.")
    
    def _format_results(self, results, return_format):
        """Format results from local graph query."""
        if return_format == "raw":
            return results
        
        # Convert to a list of dictionaries
        result_list = []
        for row in results:
            row_dict = {}
            for i, var in enumerate(results.vars):
                value = row[i]
                if value is not None:
                    # Handle different types of RDF values
                    if hasattr(value, 'toPython'):
                        row_dict[var] = value.toPython()
                    else:
                        row_dict[var] = str(value)
                else:
                    row_dict[var] = None
            result_list.append(row_dict)
        
        if return_format == "dict":
            return result_list
        
        # Convert to pandas DataFrame
        if result_list:
            return pd.DataFrame(result_list)
        return pd.DataFrame()
    
    def _format_remote_results(self, results, return_format):
        """Format results from remote endpoint query."""
        if return_format == "raw":
            return results
        
        # Extract bindings from SPARQL JSON results
        if 'results' in results and 'bindings' in results['results']:
            bindings = results['results']['bindings']
            
            # Convert to list of dictionaries
            result_list = []
            for binding in bindings:
                row_dict = {}
                for var, value in binding.items():
                    if value['type'] == 'uri':
                        row_dict[var] = value['value']
                    elif value['type'] == 'literal':
                        row_dict[var] = value['value']
                    else:
                        row_dict[var] = value['value']
                result_list.append(row_dict)
            
            if return_format == "dict":
                return result_list
            
            # Convert to pandas DataFrame
            if result_list:
                return pd.DataFrame(result_list)
            return pd.DataFrame()
        
        return results  # Return as is if structure is unexpected
    
    def display_results(self, results):
        """
        Display query results in a readable format.
        
        Args:
            results: Query results (DataFrame or list of dicts)
        """
        if isinstance(results, pd.DataFrame):
            if not results.empty:
                print(tabulate(results, headers='keys', tablefmt='psql'))
                print(f"Total results: {len(results)}")
            else:
                print("No results found.")
        elif isinstance(results, list):
            if results:
                print(json.dumps(results, indent=2))
                print(f"Total results: {len(results)}")
            else:
                print("No results found.")
        else:
            print(results)


# Example usage
def main():
    # Example 1: Using a local TTL file (like your legal dataset)
    legal_ttl_file = "data-lex2kg.ttl"  # Replace with your file path
    
    # Check if the file exists, if not, use example data for demonstration
    if not os.path.exists(legal_ttl_file):
        print(f"File {legal_ttl_file} not found. Using example data for demonstration.")
        # Example with university course data (replace with your legal data structure)
        sparql_exec = SparqlExecutor()
        example_ttl = """
        @prefix ex: <http://example.org/> .
        @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
        @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        
        ex:LegalCase1 rdf:type ex:Case ;
            ex:caseNumber "2021-123-ABC" ;
            ex:title "Smith v. Jones" ;
            ex:filedDate "2021-05-10" ;
            ex:jurisdiction ex:FederalCourt ;
            ex:hasPlaintiff ex:Smith ;
            ex:hasDefendant ex:Jones .
            
        ex:LegalCase2 rdf:type ex:Case ;
            ex:caseNumber "2021-456-DEF" ;
            ex:title "Brown v. State" ;
            ex:filedDate "2021-06-15" ;
            ex:jurisdiction ex:StateCourt ;
            ex:hasPlaintiff ex:Brown ;
            ex:hasDefendant ex:StateOfCalifornia .
            
        ex:LegalCase3 rdf:type ex:Case ;
            ex:caseNumber "2021-789-GHI" ;
            ex:title "United States v. Garcia" ;
            ex:filedDate "2021-07-20" ;
            ex:jurisdiction ex:FederalCourt ;
            ex:hasPlaintiff ex:UnitedStates ;
            ex:hasDefendant ex:Garcia .
        """
        sparql_exec.load_rdf_string(example_ttl)
    else:
        sparql_exec = SparqlExecutor(legal_ttl_file)
    
    # Example SPARQL query (adapt for your legal dataset schema)
    query = """
    select ?type where { <https://example.org/lex2kg/uu/2020/12> lex:jenisPeraturan ?type.}
    """
    
    # Execute the query and display results
    print("\nExecuting SPARQL query on local file...")
    results = sparql_exec.execute_query(query)
    sparql_exec.display_results(results)
    
    # Example 2: Using a remote SPARQL endpoint (if available)
    # Uncomment and modify if you have a legal dataset SPARQL endpoint
    """
    endpoint_url = "http://example.org/sparql"  # Replace with your endpoint URL
    remote_exec = SparqlExecutor(endpoint_url)
    
    # Example SPARQL query for remote endpoint
    remote_query = '''
    SELECT ?case ?title WHERE {
        ?case a <http://example.org/Case> .
        ?case <http://example.org/title> ?title .
    }
    LIMIT 10
    '''
    
    print("\nExecuting SPARQL query on remote endpoint...")
    remote_results = remote_exec.execute_query(remote_query)
    remote_exec.display_results(remote_results)
    """


if __name__ == "__main__":
    main()