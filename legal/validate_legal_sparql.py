"""
SPARQL Query Validator and Executor for Legal Dataset

This script loads SPARQL queries from a JSON file, executes them against an RDF graph,
and saves the results to a new JSON file. It's specifically configured for the legal dataset.
"""

import json
import os
import sys
from rdflib import Graph, Namespace
import pandas as pd
from datetime import datetime

def validate_and_execute_sparql_queries(input_json_path, ttl_file_path, output_json_path=None):
    """
    Validates and executes SPARQL queries from a JSON file against an RDF graph.
    
    Args:
        input_json_path (str): Path to the input JSON file with SPARQL queries
        ttl_file_path (str): Path to the TTL file containing the RDF graph
        output_json_path (str, optional): Path to save the output JSON file. 
                                         If None, a default name will be used.
    
    Returns:
        dict: Summary of the validation and execution results
    """
    # Default output path if not specified
    if output_json_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json_path = f"legal_sparql_results_{timestamp}.json"
    
    print(f"Loading RDF graph from {ttl_file_path}...")
    # Load the RDF graph
    graph = Graph()
    graph.parse(ttl_file_path, format="turtle")
    print(f"Loaded graph with {len(graph)} triples")
    
    # Add namespace bindings specific to the legal dataset
    graph.bind('lex', Namespace("https://example.org/lex2kg/ontology/"))
    graph.bind('rdfs', Namespace("http://www.w3.org/2000/01/rdf-schema#"))
    graph.bind('xsd', Namespace("http://www.w3.org/2001/XMLSchema#"))
    
    # Read the input JSON file
    print(f"Reading queries from {input_json_path}...")
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Initialize results list
    results = []
    total_queries = len(data)
    success_count = 0
    empty_results_count = 0
    error_count = 0
    
    # Process each query
    print(f"Executing {total_queries} SPARQL queries...")
    for i, item in enumerate(data):
        query_id = item.get('id', f"query_{i+1}")
        question = item.get('question', 'No question provided')
        english_question = item.get('englishQuestion', 'No English question provided')
        sparql = item.get('sparql', '')
        
        print(f"Processing query {i+1}/{total_queries}: {query_id}")
        
        result_item = {
            'id': query_id,
            'question': question,
            'englishQuestion': english_question,
            'sparql': sparql,
            'category': item.get('category', ''),
            'complexity': item.get('complexity', ''),
            'templateId': item.get('templateId', '')
        }
        
        try:
            # Execute the SPARQL query
            query_results = graph.query(sparql)
            
            # Convert the results to a list of dictionaries
            result_list = []
            for row in query_results:
                row_dict = {}
                for i, var in enumerate(query_results.vars):
                    value = row[i]
                    if value is not None:
                        # Handle different types of RDF values
                        if hasattr(value, 'toPython'):
                            row_dict[str(var)] = value.toPython()
                        else:
                            row_dict[str(var)] = str(value)
                    else:
                        row_dict[str(var)] = None
                result_list.append(row_dict)
            
            # Add the results to the result item
            result_item['success'] = True
            result_item['results'] = result_list
            result_item['result_count'] = len(result_list)
            
            if len(result_list) > 0:
                success_count += 1
            else:
                empty_results_count += 1
                
        except Exception as e:
            # Handle errors in SPARQL execution
            result_item['success'] = False
            result_item['error'] = str(e)
            error_count += 1
        
        # Add to results list
        results.append(result_item)
    
    # Save the results to the output JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print("\nQuery Execution Summary:")
    print(f"Total queries: {total_queries}")
    print(f"Successful queries with results: {success_count}")
    print(f"Successful queries with empty results: {empty_results_count}")
    print(f"Failed queries: {error_count}")
    print(f"Results saved to {output_json_path}")
    
    return {
        'total_queries': total_queries,
        'success_count': success_count,
        'empty_results_count': empty_results_count,
        'error_count': error_count,
        'output_file': output_json_path
    }

def main():
    """Main function to run the validator and executor for legal dataset"""
    # Check if input files exist
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        input_json_path = 'legal_documents_dataset.json'
    
    ttl_file_path = 'data-lex2kg.ttl'
    
    if not os.path.exists(input_json_path):
        print(f"Error: Input JSON file '{input_json_path}' not found!")
        sys.exit(1)
        
    if not os.path.exists(ttl_file_path):
        print(f"Error: TTL file '{ttl_file_path}' not found!")
        sys.exit(1)
    
    # Run the validator and executor
    validate_and_execute_sparql_queries(input_json_path, ttl_file_path)

if __name__ == "__main__":
    main()