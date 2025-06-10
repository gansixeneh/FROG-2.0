import json
import requests
from urllib.parse import quote
import time

def read_json_file(filename):
    """Read a JSON file and return its contents."""
    with open(filename, 'r') as file:
        return json.load(file)

def execute_sparql_query(query):
    """Execute a SPARQL query against the Wikidata SPARQL endpoint."""
    endpoint_url = "https://query.wikidata.org/sparql"
    
    # URL encode the query
    query_encoded = quote(query)
    
    # Prepare headers and parameters
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'SPARQL-Tester/1.0 (https://example.org/; email@example.org)'
    }
    params = {
        'query': query,
        'format': 'json'
    }
    
    try:
        # Make the request
        response = requests.get(endpoint_url, headers=headers, params=params)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the JSON response
        result = response.json()
        
        # Check if the results are empty
        if 'results' in result and 'bindings' in result['results']:
            if len(result['results']['bindings']) == 0:
                return "Empty", None
            else:
                return "Success", result
        else:
            return "Empty", None
    
    except requests.exceptions.HTTPError as e:
        return f"HTTP Error: {e}", None
    except requests.exceptions.ConnectionError as e:
        return f"Connection Error: {e}", None
    except requests.exceptions.Timeout as e:
        return f"Timeout Error: {e}", None
    except requests.exceptions.RequestException as e:
        return f"Request Error: {e}", None
    except json.JSONDecodeError as e:
        return f"JSON Decode Error: {e}", None
    except Exception as e:
        return f"Error: {e}", None

def main():
    # Read the JSON file
    try:
        data = read_json_file("qald_9_plus_test_wikidata_converted.json")
    except Exception as e:
        print(f"Error reading file: {e}")
        return
    
    # Track statistics
    total_queries = len(data)
    successful_queries = 0
    empty_results = []
    error_queries = []
    
    # Process each query
    for i, item in enumerate(data):
        question = item.get("question", "No question provided")
        sparql = item.get("sparql", "")
        
        print(f"\nQuery {i+1}/{total_queries}: {question}")
        
        # Skip empty queries
        if not sparql:
            print("  SPARQL query is empty. Skipping...")
            error_queries.append((i+1, question, "Empty query"))
            continue
        
        # Execute the query
        print("  Executing query...")
        status, result = execute_sparql_query(sparql)
        
        # Process the result
        if status == "Success":
            successful_queries += 1
            print("  Result: SUCCESS")
        elif status == "Empty":
            empty_results.append((i+1, question))
            print("  Result: EMPTY (no results returned)")
        else:
            error_queries.append((i+1, question, status))
            print(f"  Result: ERROR - {status}")
        
        # Add a delay to avoid overwhelming the server
        time.sleep(1)
    
    # Print summary
    print("\n" + "="*80)
    print(f"SUMMARY: Processed {total_queries} queries")
    print(f"  Successful queries: {successful_queries}")
    print(f"  Empty results: {len(empty_results)}")
    print(f"  Errors: {len(error_queries)}")
    
    # Print details of empty results
    if empty_results:
        print("\nQueries with empty results:")
        for idx, question in empty_results:
            print(f"  {idx}. {question}")
    
    # Print details of errors
    if error_queries:
        print("\nQueries with errors:")
        for idx, question, error in error_queries:
            print(f"  {idx}. {question}")
            print(f"     Error: {error}")

if __name__ == "__main__":
    main()