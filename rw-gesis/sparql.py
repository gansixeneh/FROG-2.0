# gesis/sparql.py
"""
SPARQL Query Executor for GESIS Knowledge Graph
This script provides functionality to execute SPARQL queries against the Fuseki server endpoint.
"""

import pandas as pd
from SPARQLWrapper import SPARQLWrapper, JSON
from tabulate import tabulate  # For nice table output


class SparqlExecutor:
    """A class to execute SPARQL queries against the Fuseki server."""

    def __init__(self, endpoint_url="http://localhost:3030/gesis"):
        """Initialize the SPARQL executor with the Fuseki endpoint."""
        self.endpoint = SPARQLWrapper(endpoint_url)
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
        query = "PREFIX schema: <https://schema.org/>\nPREFIX gesiskg: <https://data.gesis.org/gesiskg/schema/> \n" + query.strip()
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