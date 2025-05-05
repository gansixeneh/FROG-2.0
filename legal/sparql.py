"""
SPARQL Query Executor for Legal Dataset
This script provides functionality to execute SPARQL queries against the Fuseki server endpoint.
"""

import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from tabulate import tabulate  # For nice table output


class SparqlExecutor:
    """A class to execute SPARQL queries against the Fuseki server."""

    def __init__(self):
        """Initialize the SPARQL executor with the Fuseki endpoint."""
        self.endpoint = SPARQLWrapper("http://localhost:3030/lex2kg")
        self.endpoint.setReturnFormat(JSON)

    def execute_query(self, query, return_format="pandas"):
        """
        Execute a SPARQL query and return results.

        Args:
            query (str): SPARQL query to execute
            return_format (str): Format to return results in ("pandas", "dict", or "raw")

        Returns:
            Results in the specified format
        """
        self.endpoint.setQuery(query)
        results = self.endpoint.query().convert()
        return self._format_results(results, return_format)

    def _format_results(self, results, return_format):
        """Format results from endpoint query."""
        if return_format == "raw":
            return results

        # Extract bindings from SPARQL JSON results
        if "results" in results and "bindings" in results["results"]:
            bindings = results["results"]["bindings"]

            # Convert to list of dictionaries
            result_list = []
            for binding in bindings:
                row_dict = {}
                for var, value in binding.items():
                    if value["type"] == "uri":
                        row_dict[var] = value["value"]
                    elif value["type"] == "literal":
                        row_dict[var] = value["value"]
                    else:
                        row_dict[var] = value["value"]
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
                print(tabulate(results, headers="keys", tablefmt="psql"))
                print(f"Total results: {len(results)}")
            else:
                print("No results found.")
        elif isinstance(results, list):
            if results:
                import json

                print(json.dumps(results, indent=2))
                print(f"Total results: {len(results)}")
            else:
                print("No results found.")
        else:
            print(results)


# Example usage
def main():
    sparql_exec = SparqlExecutor()

    # Example SPARQL query
    query = """
    SELECT ?s ?p ?o 
    WHERE { 
        ?s ?p ?o 
    } 
    LIMIT 10
    """

    # Execute the query and display results
    print("\nExecuting SPARQL query on Fuseki server...")
    results = sparql_exec.execute_query(query)
    sparql_exec.display_results(results)


if __name__ == "__main__":
    main()
