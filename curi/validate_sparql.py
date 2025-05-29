"""
Enhanced SPARQL Query Validator and Results Analyzer

This script validates the generated SPARQL queries, executes them against the RDF graph,
and provides detailed analysis of the results, especially for complex queries.
"""

import json
import os
import sys
from rdflib import Graph, Namespace
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from collections import Counter

def validate_and_analyze_sparql_queries(input_json_path, ttl_file_path, output_json_path=None):
    """
    Validates, executes, and analyzes SPARQL queries from a JSON file against an RDF graph.
    
    Args:
        input_json_path (str): Path to the input JSON file with SPARQL queries
        ttl_file_path (str): Path to the TTL file containing the RDF graph
        output_json_path (str, optional): Path to save the output JSON file. 
                                         If None, a default name will be used.
    
    Returns:
        dict: Analysis results
    """
    # Default output path if not specified
    if output_json_path is None:
        output_json_path = f"curi.json"
    
    print(f"Loading RDF graph from {ttl_file_path}...")
    # Load the RDF graph
    graph = Graph()
    graph.parse(ttl_file_path, format="turtle")
    print(f"Loaded graph with {len(graph)} triples")
    
    # Add common namespace bindings
    graph.bind('ns1', Namespace("http://example.org/"))
    graph.bind('rdfs', Namespace("http://www.w3.org/2000/01/rdf-schema#"))
    graph.bind('xsd', Namespace("http://www.w3.org/2001/XMLSchema#"))
    
    # Read the input JSON file
    print(f"Reading queries from {input_json_path}...")
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Initialize results list
    results = []
    
    # Analysis counters
    stats = {
        'total_queries': len(data),
        'successful_queries': 0,
        'empty_results': 0,
        'errors': 0,
        'complexity': {'basic': 0, 'intermediate': 0, 'advanced': 0},
        'template_stats': Counter(),
        'result_counts': [],
    }
    
    # Process each query
    print(f"Executing {stats['total_queries']} SPARQL queries...")
    for i, item in enumerate(data):
        query_id = item.get('id', f"query_{i+1}")
        question = item.get('question', 'No question provided')
        sparql = item.get('sparql', '')
        complexity = item.get('complexity', 'unknown')
        template_id = item.get('templateId', 'unknown')
        
        print(f"Processing query {i+1}/{stats['total_queries']}: {query_id} ({complexity})")
        
        # Update complexity stats
        if complexity in stats['complexity']:
            stats['complexity'][complexity] += 1
            
        # Update template stats
        stats['template_stats'][template_id] += 1
        
        result_item = {
            'id': query_id,
            'question': question,
            'sparql': sparql,
            'category': item.get('category', ''),
            'complexity': complexity,
            'templateId': template_id
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
            
            # Update stats
            stats['successful_queries'] += 1
            stats['result_counts'].append(len(result_list))
            
            if len(result_list) == 0:
                stats['empty_results'] += 1
                
        except Exception as e:
            # Handle errors in SPARQL execution
            result_item['success'] = False
            result_item['error'] = str(e)
            stats['errors'] += 1
        
        # Add to results list
        results.append(result_item)
    
    # Save the results to the output JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Calculate additional statistics
    if stats['result_counts']:
        stats['avg_results'] = sum(stats['result_counts']) / len(stats['result_counts'])
        stats['max_results'] = max(stats['result_counts'])
        stats['min_results'] = min(stats['result_counts'])
    else:
        stats['avg_results'] = 0
        stats['max_results'] = 0
        stats['min_results'] = 0
    
    # Print summary
    print("\nQuery Execution Summary:")
    print(f"Total queries: {stats['total_queries']}")
    print(f"Successful queries: {stats['successful_queries']} ({stats['successful_queries']/stats['total_queries']*100:.1f}%)")
    print(f"Queries with empty results: {stats['empty_results']} ({stats['empty_results']/stats['total_queries']*100:.1f}%)")
    print(f"Failed queries: {stats['errors']} ({stats['errors']/stats['total_queries']*100:.1f}%)")
    print("\nComplexity breakdown:")
    for complexity, count in stats['complexity'].items():
        print(f"  - {complexity}: {count} ({count/stats['total_queries']*100:.1f}%)")
    print("\nResults statistics:")
    print(f"  - Average results per query: {stats['avg_results']:.2f}")
    print(f"  - Maximum results: {stats['max_results']}")
    print(f"  - Minimum results: {stats['min_results']}")
    print("\nMost common templates:")
    for template_id, count in stats['template_stats'].most_common(5):
        print(f"  - {template_id}: {count} queries")
    
    print(f"\nResults saved to {output_json_path}")
    
    return stats

def main():
    """Main function to run the validator and analyzer"""
    # Check if input files exist
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        input_json_path = 'curi.json'
    
    ttl_file_path = 'final_result.ttl'
    
    if not os.path.exists(input_json_path):
        print(f"Error: Input JSON file '{input_json_path}' not found!")
        sys.exit(1)
        
    if not os.path.exists(ttl_file_path):
        print(f"Error: TTL file '{ttl_file_path}' not found!")
        sys.exit(1)
    
    # Run the validator and analyzer
    validate_and_analyze_sparql_queries(input_json_path, ttl_file_path)

if __name__ == "__main__":
    main()