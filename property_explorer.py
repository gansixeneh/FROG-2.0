#!/usr/bin/env python3
"""
SPARQL Property Explorer for Apache Jena
Retrieves all properties and random example triples from a SPARQL endpoint
"""

from SPARQLWrapper import SPARQLWrapper, JSON
import random
from typing import List, Dict, Tuple
import json


class SPARQLPropertyExplorer:
    def __init__(
        self, endpoint_url: str = "http://localhost:3030/modified-lex2kg/query"
    ):
        """
        Initialize the SPARQL wrapper with the given endpoint URL

        Args:
            endpoint_url (str): The SPARQL endpoint URL
        """
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)

    def get_all_properties(self) -> List[str]:
        """
        Retrieve all unique properties from the knowledge graph

        Returns:
            List[str]: List of property URIs
        """
        query = """
        SELECT DISTINCT ?property WHERE {
            ?subject ?property ?object .
        }
        ORDER BY ?property
        """

        self.sparql.setQuery(query)

        try:
            results = self.sparql.query().convert()
            properties = [
                result["property"]["value"] for result in results["results"]["bindings"]
            ]
            return properties
        except Exception as e:
            print(f"Error retrieving properties: {e}")
            return []

    def get_random_triples_for_property(
        self, property_uri: str, limit: int = 5
    ) -> List[Tuple[str, str, str]]:
        """
        Get random example triples for a given property

        Args:
            property_uri (str): The property URI to get examples for
            limit (int): Number of examples to retrieve

        Returns:
            List[Tuple[str, str, str]]: List of (subject, property, object) triples
        """
        # First get count of triples for this property
        count_query = f"""
        SELECT (COUNT(*) as ?count) WHERE {{
            ?subject <{property_uri}> ?object .
        }}
        """

        self.sparql.setQuery(count_query)

        try:
            count_results = self.sparql.query().convert()
            total_count = int(count_results["results"]["bindings"][0]["count"]["value"])

            if total_count == 0:
                return []

            # Calculate random offsets
            max_offset = max(0, total_count - limit)
            random_offset = random.randint(0, max_offset) if max_offset > 0 else 0

            # Query for random triples
            triples_query = f"""
            SELECT ?subject ?object WHERE {{
                ?subject <{property_uri}> ?object .
            }}
            LIMIT {limit}
            OFFSET {random_offset}
            """

            self.sparql.setQuery(triples_query)
            results = self.sparql.query().convert()

            triples = []
            for result in results["results"]["bindings"]:
                subject = result["subject"]["value"]
                object_value = result["object"]["value"]
                triples.append((subject, property_uri, object_value))

            return triples

        except Exception as e:
            print(f"Error retrieving triples for property {property_uri}: {e}")
            return []

    def explore_properties(
        self, max_properties: int = None
    ) -> Dict[str, List[Tuple[str, str, str]]]:
        """
        Main function to explore all properties and their example usages

        Args:
            max_properties (int): Limit the number of properties to explore (None for all)

        Returns:
            Dict[str, List[Tuple[str, str, str]]]: Dictionary mapping properties to example triples
        """
        print("Retrieving all properties...")
        properties = self.get_all_properties()

        if not properties:
            print("No properties found!")
            return {}

        print(f"Found {len(properties)} properties")

        if max_properties:
            properties = properties[:max_properties]
            print(f"Limiting to first {max_properties} properties")

        property_examples = {}

        for i, prop in enumerate(properties, 1):
            print(f"Processing property {i}/{len(properties)}: {prop}")
            examples = self.get_random_triples_for_property(prop, 5)
            property_examples[prop] = examples

        return property_examples

    def format_results(
        self, property_examples: Dict[str, List[Tuple[str, str, str]]]
    ) -> str:
        """
        Format the results in a readable way

        Args:
            property_examples: Dictionary of properties and their example triples

        Returns:
            str: Formatted string representation
        """
        output = []
        output.append("=" * 80)
        output.append("SPARQL PROPERTY EXPLORATION RESULTS")
        output.append("=" * 80)
        output.append(f"Total properties found: {len(property_examples)}")
        output.append("")

        for prop, examples in property_examples.items():
            output.append(f"Property: {prop}")
            output.append(f"Number of examples: {len(examples)}")

            if examples:
                output.append("Example triples:")
                for i, (subj, pred, obj) in enumerate(examples, 1):
                    # Truncate long URIs for readability
                    subj_short = subj.split("/")[-1] if "/" in subj else subj
                    obj_short = obj.split("/")[-1] if "/" in obj else obj

                    output.append(f"  {i}. {subj_short} -> {obj_short}")
                    output.append(f"     Full: <{subj}> <{pred}> <{obj}>")
            else:
                output.append("No examples found")

            output.append("-" * 60)
            output.append("")

        return "\n".join(output)


def main():
    """
    Main execution function
    """
    # Initialize the explorer
    explorer = SPARQLPropertyExplorer()

    # You can limit the number of properties for testing
    # Set to None to get all properties
    max_props = None  # Change this or set to None for all properties

    try:
        # Explore properties and get examples
        results = explorer.explore_properties(max_properties=max_props)

        # Format and display results
        formatted_output = explorer.format_results(results)
        print(formatted_output)

        # Optionally save to file
        with open(
            "sparql_property_exploration_results.txt", "w", encoding="utf-8"
        ) as f:
            f.write(formatted_output)
            print(f"\nResults saved to 'sparql_property_exploration_results.txt'")

        # Return results for programmatic use
        return results

    except Exception as e:
        print(f"Error during exploration: {e}")
        return {}


if __name__ == "__main__":
    results = main()
