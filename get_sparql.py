import json
import os

def get_sparql_queries(json_file_path):
    """
    Reads a JSON file and extracts the 'sparql' attribute from each element.

    Args:
        json_file_path (str): Path to the JSON file.

    Returns:
        list: List of sparql query strings.
    """
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    sparql_queries = [{'sparql': item['sparql']} for item in data if 'sparql' in item]
    return sparql_queries

def save_sparqls_to_file(json_file_path):
    sparqls = get_sparql_queries(json_file_path)
    output_file = f"{json_file_path[:-5]}_sparql.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sparqls, f, ensure_ascii=False, indent=2)

# Example usage:
save_sparqls_to_file('rw-legal/pattern_based_dataset.json')