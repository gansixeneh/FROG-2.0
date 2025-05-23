"""
Pattern-Based SPARQL Query Validator

This script validates the generated pattern-based SPARQL queries against the RDF graph
and provides detailed analysis of results and potential issues.
"""

import json
import os
import sys
from rdflib import Graph, Namespace
import pandas as pd
from collections import Counter, defaultdict
from datetime import datetime

def validate_pattern_based_queries(json_file, ttl_file, output_file=None):
    """
    Validate pattern-based SPARQL queries against RDF graph
    
    Args:
        json_file (str): Path to JSON file with generated queries
        ttl_file (str): Path to TTL file with RDF data
        output_file (str): Optional path to save validation results
        
    Returns:
        dict: Validation results and statistics
    """
    print(f"Loading RDF graph from {ttl_file}...")
    
    # Load RDF graph
    graph = Graph()
    graph.parse(ttl_file, format='turtle')
    
    # Bind namespaces
    graph.bind('ns1', Namespace('http://example.org/'))
    graph.bind('rdfs', Namespace('http://www.w3.org/2000/01/rdf-schema#'))
    
    print(f"Loaded graph with {len(graph)} triples")
    
    # Load queries
    print(f"Loading queries from {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        queries = json.load(f)
    
    print(f"Loaded {len(queries)} queries")
    
    # Initialize validation results
    results = []
    stats = {
        'total_queries': len(queries),
        'successful': 0,
        'empty_results': 0,
        'errors': 0,
        'by_complexity': defaultdict(lambda: {'total': 0, 'successful': 0, 'empty': 0, 'errors': 0}),
        'by_pattern_type': defaultdict(lambda: {'total': 0, 'successful': 0, 'empty': 0, 'errors': 0}),
        'result_counts': []
    }
    
    print("Validating queries...")
    
    # Process each query
    for i, query_item in enumerate(queries):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(queries)} ({i/len(queries)*100:.1f}%)")
        
        query_id = query_item.get('id', f'q{i}')
        sparql = query_item.get('sparql', '')
        complexity = query_item.get('complexity', 'unknown')
        pattern_type = query_item.get('pattern_type', 'unknown')
        
        # Update stats
        stats['by_complexity'][complexity]['total'] += 1
        stats['by_pattern_type'][pattern_type]['total'] += 1
        
        result_item = {
            'id': query_id,
            'sparql': sparql,
            'complexity': complexity,
            'pattern_type': pattern_type,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Execute query
            query_results = list(graph.query(sparql))
            result_count = len(query_results)
            
            # Convert results to serializable format
            processed_results = []
            for row in query_results:
                row_dict = {}
                for j, var in enumerate(graph.query(sparql).vars):
                    value = row[j]
                    if value is not None:
                        if hasattr(value, 'toPython'):
                            row_dict[str(var)] = value.toPython()
                        else:
                            row_dict[str(var)] = str(value)
                    else:
                        row_dict[str(var)] = None
                processed_results.append(row_dict)
            
            # Update result item
            result_item.update({
                'success': True,
                'result_count': result_count,
                'results': processed_results[:5],  # Store first 5 results only
                'has_more_results': result_count > 5
            })
            
            # Update statistics
            stats['successful'] += 1
            stats['by_complexity'][complexity]['successful'] += 1
            stats['by_pattern_type'][pattern_type]['successful'] += 1
            stats['result_counts'].append(result_count)
            
            if result_count == 0:
                stats['empty_results'] += 1
                stats['by_complexity'][complexity]['empty'] += 1
                stats['by_pattern_type'][pattern_type]['empty'] += 1
                
        except Exception as e:
            # Handle query errors
            result_item.update({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
            
            stats['errors'] += 1
            stats['by_complexity'][complexity]['errors'] += 1
            stats['by_pattern_type'][pattern_type]['errors'] += 1
        
        results.append(result_item)
    
    # Calculate additional statistics
    if stats['result_counts']:
        stats['avg_results'] = sum(stats['result_counts']) / len(stats['result_counts'])
        stats['max_results'] = max(stats['result_counts'])
        stats['min_results'] = min(stats['result_counts'])
        stats['total_results'] = sum(stats['result_counts'])
    else:
        stats['avg_results'] = 0
        stats['max_results'] = 0
        stats['min_results'] = 0
        stats['total_results'] = 0
    
    # Compile final results
    validation_results = {
        'metadata': {
            'ttl_file': ttl_file,
            'json_file': json_file,
            'validation_time': datetime.now().isoformat(),
            'total_triples': len(graph)
        },
        'statistics': stats,
        'query_results': results
    }
    
    # Save results if output file specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)
        print(f"Validation results saved to {output_file}")
    
    return validation_results

def print_validation_summary(validation_results):
    """Print a summary of validation results"""
    
    stats = validation_results['statistics']
    
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    print(f"Total queries tested: {stats['total_queries']}")
    print(f"Successful queries: {stats['successful']} ({stats['successful']/stats['total_queries']*100:.1f}%)")
    print(f"Queries with empty results: {stats['empty_results']} ({stats['empty_results']/stats['total_queries']*100:.1f}%)")
    print(f"Failed queries: {stats['errors']} ({stats['errors']/stats['total_queries']*100:.1f}%)")
    
    print(f"\nResult Statistics:")
    print(f"  Total results returned: {stats['total_results']}")
    print(f"  Average results per query: {stats['avg_results']:.2f}")
    print(f"  Max results from single query: {stats['max_results']}")
    print(f"  Min results from single query: {stats['min_results']}")
    
    print(f"\nBy Complexity:")
    for complexity in ['basic', 'intermediate', 'advanced']:
        if complexity in stats['by_complexity']:
            comp_stats = stats['by_complexity'][complexity]
            total = comp_stats['total']
            successful = comp_stats['successful']
            print(f"  {complexity}: {successful}/{total} successful ({successful/total*100:.1f}%)")
    
    print(f"\nTop Pattern Types by Success Rate:")
    pattern_success_rates = []
    for pattern_type, pattern_stats in stats['by_pattern_type'].items():
        if pattern_stats['total'] >= 5:  # Only show patterns with at least 5 queries
            success_rate = pattern_stats['successful'] / pattern_stats['total']
            pattern_success_rates.append((pattern_type, success_rate, pattern_stats['total']))
    
    # Sort by success rate
    pattern_success_rates.sort(key=lambda x: x[1], reverse=True)
    
    for pattern_type, success_rate, total in pattern_success_rates[:10]:
        print(f"  {pattern_type}: {success_rate*100:.1f}% ({total} queries)")

def show_sample_results(validation_results, num_samples=5):
    """Show sample query results"""
    
    query_results = validation_results['query_results']
    
    print(f"\n" + "="*60)
    print("SAMPLE QUERY RESULTS")
    print("="*60)
    
    # Show successful queries with results
    successful_with_results = [r for r in query_results if r['success'] and r['result_count'] > 0]
    
    if successful_with_results:
        print(f"\nSuccessful Queries with Results:")
        for i, result in enumerate(successful_with_results[:num_samples]):
            print(f"\n{i+1}. Query {result['id']} ({result['complexity']}, {result['pattern_type']})")
            print(f"   SPARQL: {result['sparql']}")
            print(f"   Results: {result['result_count']} found")
            if result['results']:
                print(f"   Sample result: {result['results'][0]}")
    
    # Show queries with errors
    error_queries = [r for r in query_results if not r['success']]
    
    if error_queries:
        print(f"\nQueries with Errors:")
        for i, result in enumerate(error_queries[:3]):  # Show first 3 errors
            print(f"\n{i+1}. Query {result['id']} ({result['complexity']}, {result['pattern_type']})")
            print(f"   SPARQL: {result['sparql']}")
            print(f"   Error: {result['error']}")

def main():
    """Main function to run validation"""
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = 'pattern_based_dataset.json'
    
    ttl_file = 'final_result.ttl'
    
    # Check if files exist
    if not os.path.exists(json_file):
        print(f"Error: JSON file '{json_file}' not found!")
        sys.exit(1)
    
    if not os.path.exists(ttl_file):
        print(f"Error: TTL file '{ttl_file}' not found!")
        sys.exit(1)
    
    # Run validation
    output_file = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    validation_results = validate_pattern_based_queries(json_file, ttl_file, output_file)
    
    # Print summary
    print_validation_summary(validation_results)
    
    # Show sample results
    show_sample_results(validation_results)
    
    print(f"\nDetailed results saved to: {output_file}")

if __name__ == "__main__":
    main()