"""
SPARQL Query Validator and Executor for Legal Knowledge Graph

This script loads SPARQL queries from a JSON file, executes them against the Legal KG Fuseki server,
and saves the results to a new JSON file. Works with pattern-based generated queries.
"""

import json
import os
import sys
from datetime import datetime
from SPARQLWrapper import SPARQLWrapper, JSON
import time


class LegalKGSparqlExecutor:
    """SPARQL executor specifically for Legal Knowledge Graph"""
    
    def __init__(self, endpoint_url="http://localhost:3030/modified-lex2kg/query", timeout=30):
        """
        Initialize the SPARQL executor for Legal KG endpoint
        
        Args:
            endpoint_url (str): URL of the Legal KG SPARQL endpoint
            timeout (int): Query timeout in seconds
        """
        self.endpoint_url = endpoint_url
        self.sparql = SPARQLWrapper(endpoint_url)
        self.sparql.setReturnFormat(JSON)
        self.sparql.setTimeout(timeout)
        
        # Legal KG-specific prefixes
        self.prefixes = {
            "lex2kg-o": "<https://example.org/lex2kg/ontology/>",
            "rdfs": "<https://www.w3.org/2000/01/rdf-schema#>",
            "xsd": "<http://www.w3.org/2001/XMLSchema#>",
            "rdf": "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>",
        }
    
    def _format_prefixes(self):
        """Format the prefixes for inclusion in SPARQL queries"""
        prefix_str = ""
        for prefix, uri in self.prefixes.items():
            prefix_str += f"PREFIX {prefix}: {uri}\n"
        return prefix_str
    
    def execute_query(self, sparql_query, return_format="dict"):
        """
        Execute SPARQL query against Legal KG endpoint
        
        Args:
            sparql_query (str): SPARQL query (with or without prefixes)
            return_format (str): Return format ('dict' or 'raw')
            
        Returns:
            list: Query results as list of dictionaries
        """
        try:
            # Add prefixes if not already present
            if "PREFIX" not in sparql_query.upper():
                full_query = f"{self._format_prefixes()}\n{sparql_query}"
            else:
                full_query = sparql_query
            
            self.sparql.setQuery(full_query)
            results = self.sparql.query().convert()
            
            if return_format == "dict":
                # Convert to list of dictionaries for easier processing
                result_list = []
                if results and "results" in results and "bindings" in results["results"]:
                    for binding in results["results"]["bindings"]:
                        result_dict = {}
                        for var, value in binding.items():
                            result_dict[var] = value["value"]
                        result_list.append(result_dict)
                return result_list
            else:
                return results
                
        except Exception as e:
            raise Exception(f"SPARQL execution error: {str(e)}")


def validate_and_execute_sparql_queries(input_json_path, output_json_path=None):
    """
    Validates and executes SPARQL queries from a JSON file against the Legal KG Fuseki server.

    Args:
        input_json_path (str): Path to the input JSON file with SPARQL queries
        output_json_path (str, optional): Path to save the output JSON file.
                                         If None, a default name will be used.

    Returns:
        dict: Summary of the validation and execution results
    """
    # Default output path if not specified
    if output_json_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_json_path = f"legal_kg_sparql_results_{timestamp}.json"

    print(f"Connecting to Legal KG Fuseki server at http://localhost:3030/modified-lex2kg...")
    # Initialize the SPARQL executor
    sparql_exec = LegalKGSparqlExecutor()

    # Test connection with a simple query
    try:
        test_result = sparql_exec.execute_query("SELECT (COUNT(*) AS ?count) WHERE { ?s ?p ?o . }")
        total_triples = test_result[0]["count"] if test_result else 0
        print(f"Successfully connected! Legal knowledge graph contains {total_triples} triples.")
    except Exception as e:
        print(f"Error connecting to Legal KG endpoint: {e}")
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
        
        # Small delay to avoid overwhelming the server
        time.sleep(0.1)

    # Calculate statistics
    avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
    
    # Prepare summary statistics
    summary = {
        "validation_timestamp": datetime.now().isoformat(),
        "endpoint": "http://localhost:3030/modified-lex2kg/query",
        "knowledge_graph": "Legal Knowledge Graph (lex2kg)",
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
    print("LEGAL KNOWLEDGE GRAPH - SPARQL Query Execution Summary:")
    print("="*70)
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
    if pattern_type:
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


def analyze_legal_kg_results(results_json_path):
    """
    Analyze the results of Legal KG query execution for insights
    
    Args:
        results_json_path (str): Path to the results JSON file
    """
    with open(results_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    results = data["query_results"]
    
    print("\n" + "="*70)
    print("DETAILED LEGAL KG RESULTS ANALYSIS:")
    print("="*70)
    
    # Find queries with most results
    results_with_data = [r for r in results if r["success"] and r["result_count"] > 0]
    if results_with_data:
        top_results = sorted(results_with_data, key=lambda x: x["result_count"], reverse=True)[:5]
        print("\nQueries with Most Results:")
        for i, result in enumerate(top_results, 1):
            print(f"  {i}. {result['id']} ({result['pattern_type']}): {result['result_count']} results")
    
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
    
    # Legal KG specific analysis
    print("\nLegal KG Specific Analysis:")
    
    # Count queries by legal property types (if identifiable from pattern types)
    legal_property_patterns = {}
    for result in results_with_data:
        pattern = result.get("pattern_type", "")
        if "prop" in pattern:
            base_pattern = pattern.split("_v")[0] if "_v" in pattern else pattern
            legal_property_patterns[base_pattern] = legal_property_patterns.get(base_pattern, 0) + 1
    
    if legal_property_patterns:
        print("\nMost Successful Legal Property Patterns:")
        sorted_legal = sorted(legal_property_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        for pattern, count in sorted_legal:
            print(f"  {pattern}: {count} successful queries")
    
    # Analyze result sizes for legal entities
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
        small_queries = len([r for r in result_sizes if r <= 10])
        medium_queries = len([r for r in result_sizes if 10 < r <= 100])
        large_queries = len([r for r in result_sizes if r > 100])
        
        print(f"\nResult Size Distribution:")
        print(f"  Small (1-10 results): {small_queries} queries")
        print(f"  Medium (11-100 results): {medium_queries} queries") 
        print(f"  Large (100+ results): {large_queries} queries")


def main():
    """Main function to run the validator and executor for Legal KG dataset"""
    # Check if input file exists
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        # Try common pattern-based generator output files for legal KG
        possible_files = [
            "pattern_based_dataset.json",
            "legal_pattern_based_dataset.json",
            "legal_kg_dataset.json",
            "lex2kg_dataset.json"
        ]
        
        input_json_path = None
        for file_path in possible_files:
            if os.path.exists(file_path):
                input_json_path = file_path
                break
        
        if input_json_path is None:
            print("Error: No input JSON file found!")
            print("Please provide a path to your generated Legal KG SPARQL queries JSON file.")
            print("Usage: python legal_sparql_validator.py <input_file.json>")
            print("\nLooking for files like:")
            for file_name in possible_files:
                print(f"  - {file_name}")
            sys.exit(1)

    if not os.path.exists(input_json_path):
        print(f"Error: Input JSON file '{input_json_path}' not found!")
        sys.exit(1)

    print(f"Found input file: {input_json_path}")
    
    # Run the validator and executor
    summary = validate_and_execute_sparql_queries(input_json_path)
    
    if summary:
        # Ask if user wants detailed analysis
        response = input("\nWould you like to see detailed Legal KG results analysis? (y/n): ")
        if response.lower() in ['y', 'yes']:
            output_file = None
            for key, value in summary.items():
                if key.endswith('_file') or 'output' in key:
                    output_file = value
                    break
            
            if not output_file:
                # Reconstruct output filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = f"legal_kg_sparql_results_{timestamp}.json"
            
            analyze_legal_kg_results(output_file)


if __name__ == "__main__":
    main()