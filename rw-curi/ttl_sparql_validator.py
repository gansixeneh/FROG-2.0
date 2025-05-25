"""
SPARQL Query Validator for TTL File-Based Generator

This script loads SPARQL queries from a JSON file, executes them against a local TTL file using rdflib,
and saves the results to a new JSON file. Works with pattern-based generated queries.
"""

import json
import os
import sys
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal
import time


class TTLSparqlExecutor:
    """SPARQL executor for local TTL files using rdflib"""
    
    def __init__(self, ttl_file_path, prefixes=None):
        """
        Initialize the SPARQL executor for TTL file
        
        Args:
            ttl_file_path (str): Path to the TTL file
            prefixes (dict): Namespace prefixes
        """
        self.ttl_file_path = ttl_file_path
        self.graph = Graph()
        
        # Load the TTL file
        print(f"Loading TTL file: {ttl_file_path}")
        self.graph.parse(ttl_file_path, format='turtle')
        print(f"Loaded graph with {len(self.graph)} triples")
        
        # Set default prefixes
        if prefixes is None:
            self.prefixes = {
                'ns1': 'http://example.org/',
                'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                'xsd': 'http://www.w3.org/2001/XMLSchema#',
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
            }
        else:
            self.prefixes = prefixes
            
        # Bind namespaces to graph
        for prefix, uri in self.prefixes.items():
            self.graph.bind(prefix, Namespace(uri))
    
    def execute_query(self, sparql_query, return_format="dict"):
        """
        Execute SPARQL query against the TTL graph
        
        Args:
            sparql_query (str): SPARQL query
            return_format (str): Return format ('dict' or 'raw')
            
        Returns:
            list: Query results as list of dictionaries
        """
        try:
            # Execute query on the graph
            results = self.graph.query(sparql_query)
            
            if return_format == "dict":
                # Convert to list of dictionaries for easier processing
                result_list = []
                for row in results:
                    result_dict = {}
                    for i, var in enumerate(results.vars):
                        if row[i] is not None:
                            result_dict[str(var)] = str(row[i])
                    result_list.append(result_dict)
                return result_list
            else:
                return list(results)
                
        except Exception as e:
            raise Exception(f"SPARQL execution error: {str(e)}")


def validate_and_execute_sparql_queries(input_json_path, ttl_file_path, output_json_path=None):
    """
    Validates and executes SPARQL queries from a JSON file against a TTL file.

    Args:
        input_json_path (str): Path to the input JSON file with SPARQL queries
        ttl_file_path (str): Path to the TTL file
        output_json_path (str, optional): Path to save the output JSON file.
                                         If None, a default name will be used.

    Returns:
        dict: Summary of the validation and execution results
    """
    # Default output path if not specified
    if output_json_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json_path = f"ttl_sparql_results_{timestamp}.json"

    # Initialize the SPARQL executor
    try:
        sparql_exec = TTLSparqlExecutor(ttl_file_path)
    except Exception as e:
        print(f"Error loading TTL file: {e}")
        return None

    # Read the input JSON file
    print(f"Reading queries from {input_json_path}...")
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Initialize results list
    results = []
    total_queries = len(data)
    success_count = 0
    empty_results_count = 0
    error_count = 0
    
    # Track query execution times
    execution_times = []

    # Process each query
    print(f"Executing {total_queries} SPARQL queries...")
    for i, item in enumerate(data):
        query_id = item.get("id", f"query_{i+1}")
        sparql = item.get("sparql", "")
        
        # Handle both formats: pattern-based generator and traditional question-based
        question = item.get("question", "Pattern-based generated query")
        english_question = item.get("englishQuestion", question)
        pattern_type = item.get("pattern_type", "")
        complexity = item.get("complexity", "")
        category = item.get("category", pattern_type)
        template_id = item.get("templateId", pattern_type)

        print(f"Processing query {i+1}/{total_queries}: {query_id} ({pattern_type})")

        result_item = {
            "id": query_id,
            "question": question,
            "englishQuestion": english_question,
            "sparql": sparql,
            "pattern_type": pattern_type,
            "category": category,
            "complexity": complexity,
            "templateId": template_id,
        }

        try:
            # Measure execution time
            start_time = time.time()
            
            # Execute the SPARQL query
            query_results = sparql_exec.execute_query(sparql, return_format="dict")
            
            end_time = time.time()
            execution_time = end_time - start_time
            execution_times.append(execution_time)

            # Add the results to the result item
            result_item["success"] = True
            result_item["results"] = query_results
            result_item["result_count"] = len(query_results)
            result_item["execution_time_seconds"] = round(execution_time, 3)

            if len(query_results) > 0:
                success_count += 1
                print(f"  ✓ Success: {len(query_results)} results ({execution_time:.3f}s)")
            else:
                empty_results_count += 1
                print(f"  ⚠ Success but empty results ({execution_time:.3f}s)")

        except Exception as e:
            # Handle errors in SPARQL execution
            result_item["success"] = False
            result_item["error"] = str(e)
            result_item["execution_time_seconds"] = None
            error_count += 1
            print(f"  ✗ Error: {str(e)}")

        # Add to results list
        results.append(result_item)

    # Calculate statistics
    avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
    
    # Prepare summary statistics
    summary = {
        "validation_timestamp": datetime.now().isoformat(),
        "ttl_file": ttl_file_path,
        "total_triples": len(sparql_exec.graph),
        "total_queries": total_queries,
        "successful_queries_with_results": success_count,
        "successful_queries_empty_results": empty_results_count,
        "failed_queries": error_count,
        "success_rate_percent": round((success_count + empty_results_count) / total_queries * 100, 2),
        "average_execution_time_seconds": round(avg_execution_time, 3),
        "total_execution_time_seconds": round(sum(execution_times), 3)
    }

    # Prepare final output
    output_data = {
        "summary": summary,
        "query_results": results
    }

    # Save the results to the output JSON file
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print("TTL FILE - SPARQL Query Execution Summary:")
    print("="*70)
    print(f"TTL file: {ttl_file_path}")
    print(f"Total triples in graph: {len(sparql_exec.graph)}")
    print(f"Total queries processed: {total_queries}")
    print(f"Successful queries with results: {success_count}")
    print(f"Successful queries with empty results: {empty_results_count}")
    print(f"Failed queries: {error_count}")
    print(f"Overall success rate: {summary['success_rate_percent']}%")
    print(f"Average execution time: {avg_execution_time:.3f} seconds")
    print(f"Total execution time: {sum(execution_times):.3f} seconds")
    print(f"Results saved to: {output_json_path}")
    print("="*70)

    # Print breakdown by complexity/pattern type
    if any(r.get("pattern_type") for r in results):
        complexity_stats = {}
        pattern_stats = {}
        
        for result in results:
            complexity = result.get("complexity", "unknown")
            pattern = result.get("pattern_type", "unknown")
            
            if complexity not in complexity_stats:
                complexity_stats[complexity] = {"total": 0, "success": 0}
            if pattern not in pattern_stats:
                pattern_stats[pattern] = {"total": 0, "success": 0}
                
            complexity_stats[complexity]["total"] += 1
            pattern_stats[pattern]["total"] += 1
            
            if result["success"] and result["result_count"] > 0:
                complexity_stats[complexity]["success"] += 1
                pattern_stats[pattern]["success"] += 1
        
        print("\nBreakdown by Complexity:")
        for complexity, stats in complexity_stats.items():
            success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  {complexity}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")
        
        print("\nTop 5 Pattern Types by Success:")
        sorted_patterns = sorted(pattern_stats.items(), 
                               key=lambda x: x[1]["success"], reverse=True)[:5]
        for pattern, stats in sorted_patterns:
            success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            print(f"  {pattern}: {stats['success']}/{stats['total']} ({success_rate:.1f}%)")

    return summary


def analyze_ttl_results(results_json_path):
    """
    Analyze the results of TTL query execution for insights
    
    Args:
        results_json_path (str): Path to the results JSON file
    """
    with open(results_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    results = data["query_results"]
    
    print("\n" + "="*70)
    print("DETAILED TTL RESULTS ANALYSIS:")
    print("="*70)
    
    # Find queries with most results
    results_with_data = [r for r in results if r["success"] and r["result_count"] > 0]
    if results_with_data:
        top_results = sorted(results_with_data, key=lambda x: x["result_count"], reverse=True)[:5]
        print("\nQueries with Most Results:")
        for i, result in enumerate(top_results, 1):
            print(f"  {i}. {result['id']} ({result['pattern_type']}): {result['result_count']} results")
            # Show first few results if available
            if result.get("results") and len(result["results"]) > 0:
                sample_result = result["results"][0]
                print(f"     Sample result: {sample_result}")
    
    # Find fastest queries
    successful_queries = [r for r in results if r["success"] and r["execution_time_seconds"] is not None]
    if successful_queries:
        fastest_queries = sorted(successful_queries, key=lambda x: x["execution_time_seconds"])[:5]
        print("\nFastest Successful Queries:")
        for i, result in enumerate(fastest_queries, 1):
            print(f"  {i}. {result['id']}: {result['execution_time_seconds']}s")
    
    # Find most common errors
    failed_queries = [r for r in results if not r["success"]]
    if failed_queries:
        error_types = {}
        for result in failed_queries:
            error = result.get("error", "Unknown error")
            # Simplify error message
            simplified_error = error.split(":")[0] if ":" in error else error
            error_types[simplified_error] = error_types.get(simplified_error, 0) + 1
        
        print("\nMost Common Error Types:")
        sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
        for error, count in sorted_errors:
            print(f"  {error}: {count} occurrences")
    
    # TTL-specific analysis
    print("\nTTL Graph Analysis:")
    
    # Count queries by pattern complexity
    complexity_performance = {}
    for result in results:
        complexity = result.get("complexity", "unknown")
        if complexity not in complexity_performance:
            complexity_performance[complexity] = {
                "total": 0, 
                "with_results": 0, 
                "avg_results": 0,
                "total_results": 0
            }
        
        complexity_performance[complexity]["total"] += 1
        if result["success"] and result["result_count"] > 0:
            complexity_performance[complexity]["with_results"] += 1
            complexity_performance[complexity]["total_results"] += result["result_count"]
    
    # Calculate averages
    for complexity, stats in complexity_performance.items():
        if stats["with_results"] > 0:
            stats["avg_results"] = stats["total_results"] / stats["with_results"]
    
    print("\nPattern Complexity Performance:")
    for complexity, stats in complexity_performance.items():
        print(f"  {complexity}:")
        print(f"    Total queries: {stats['total']}")
        print(f"    Queries with results: {stats['with_results']}")
        print(f"    Average results per successful query: {stats['avg_results']:.1f}")
    
    # Analyze result sizes
    if results_with_data:
        result_sizes = [r["result_count"] for r in results_with_data]
        avg_results = sum(result_sizes) / len(result_sizes)
        max_results = max(result_sizes)
        min_results = min(result_sizes)
        
        print(f"\nResult Set Statistics:")
        print(f"  Average results per successful query: {avg_results:.1f}")
        print(f"  Maximum results in a single query: {max_results}")
        print(f"  Minimum results in a successful query: {min_results}")
        
        # Categorize by result size
        small_queries = len([r for r in result_sizes if r <= 5])
        medium_queries = len([r for r in result_sizes if 5 < r <= 20])
        large_queries = len([r for r in result_sizes if r > 20])
        
        print(f"\nResult Size Distribution:")
        print(f"  Small (1-5 results): {small_queries} queries")
        print(f"  Medium (6-20 results): {medium_queries} queries") 
        print(f"  Large (20+ results): {large_queries} queries")
    
    # Pattern type effectiveness
    pattern_effectiveness = {}
    for result in results_with_data:
        pattern_base = result.get("pattern_type", "unknown").split("_v")[0]
        if pattern_base not in pattern_effectiveness:
            pattern_effectiveness[pattern_base] = {
                "count": 0,
                "total_results": 0,
                "avg_results": 0
            }
        pattern_effectiveness[pattern_base]["count"] += 1
        pattern_effectiveness[pattern_base]["total_results"] += result["result_count"]
    
    # Calculate averages for pattern effectiveness
    for pattern, stats in pattern_effectiveness.items():
        if stats["count"] > 0:
            stats["avg_results"] = stats["total_results"] / stats["count"]
    
    print("\nMost Effective Pattern Types:")
    sorted_patterns = sorted(pattern_effectiveness.items(), 
                           key=lambda x: x[1]["avg_results"], reverse=True)[:5]
    for pattern, stats in sorted_patterns:
        print(f"  {pattern}: {stats['count']} queries, avg {stats['avg_results']:.1f} results")


def main():
    """Main function to run the validator for TTL file-based dataset"""
    # Check for TTL file
    ttl_file_candidates = [
        "final_result.ttl",
        "data.ttl",
        "knowledge_graph.ttl",
        "output.ttl"
    ]
    
    ttl_file_path = None
    for candidate in ttl_file_candidates:
        if os.path.exists(candidate):
            ttl_file_path = candidate
            break
    
    if ttl_file_path is None:
        print("Error: No TTL file found!")
        print("Please ensure one of these files exists:")
        for candidate in ttl_file_candidates:
            print(f"  - {candidate}")
        sys.exit(1)
    
    # Check if input file exists
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        # Try common pattern-based generator output files for TTL
        possible_files = [
            "pattern_based_dataset.json",
            "ttl_pattern_based_dataset.json",
            "rdflib_dataset.json"
        ]
        
        input_json_path = None
        for file_path in possible_files:
            if os.path.exists(file_path):
                input_json_path = file_path
                break
        
        if input_json_path is None:
            print("Error: No input JSON file found!")
            print("Please provide a path to your generated SPARQL queries JSON file.")
            print("Usage: python ttl_sparql_validator.py <input_file.json>")
            print("\nLooking for files like:")
            for file_name in possible_files:
                print(f"  - {file_name}")
            sys.exit(1)

    if not os.path.exists(input_json_path):
        print(f"Error: Input JSON file '{input_json_path}' not found!")
        sys.exit(1)

    print(f"Found input file: {input_json_path}")
    print(f"Found TTL file: {ttl_file_path}")
    
    # Run the validator and executor
    summary = validate_and_execute_sparql_queries(input_json_path, ttl_file_path)
    
    if summary:
        # Ask if user wants detailed analysis
        response = input("\nWould you like to see detailed TTL results analysis? (y/n): ")
        if response.lower() in ['y', 'yes']:
            # Construct output filename from timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ttl_sparql_results_{timestamp}.json"
            
            analyze_ttl_results(output_file)


if __name__ == "__main__":
    main()