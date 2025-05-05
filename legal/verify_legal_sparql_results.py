"""
verify_legal_sparql_results.py

This script validates that all SPARQL queries in legal_documents_dataset.json
return at least one row of results when executed against a Fuseki server.
"""

import json
import os
import sys
from datetime import datetime

# Import the SparqlExecutor from the existing module
from sparql import SparqlExecutor

def verify_sparql_results(input_json_path="legal_documents_dataset.json"):
    """
    Verifies all SPARQL queries in the input file return at least one row of results.
    
    Args:
        input_json_path (str): Path to the JSON file with SPARQL queries
        
    Returns:
        dict: Summary of validation results
    """
    print(f"Connecting to Fuseki server at http://localhost:3030/lex2kg...")
    
    # Initialize the SPARQL executor
    sparql_exec = SparqlExecutor()

    # Read the input JSON file
    print(f"Reading queries from {input_json_path}...")
    with open(input_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Initialize tracking variables
    total_queries = len(data)
    success_count = 0
    empty_results_count = 0
    error_count = 0
    failed_queries = []
    results_by_template = {}

    # Process each query
    print(f"Executing {total_queries} SPARQL queries...")
    for i, item in enumerate(data):
        query_id = item.get("id", f"query_{i+1}")
        question = item.get("question", "No question provided")
        sparql = item.get("sparql", "")
        template_id = item.get("templateId", "unknown")
        
        # Track template statistics
        if template_id not in results_by_template:
            results_by_template[template_id] = {
                "total": 0,
                "success": 0,
                "empty": 0,
                "error": 0
            }
        results_by_template[template_id]["total"] += 1

        print(f"Processing {query_id} ({i+1}/{total_queries}): Template: {template_id}")

        try:
            # Execute the SPARQL query
            query_results = sparql_exec.execute_query(sparql, return_format="dict")

            # Check if query returned at least one row
            if len(query_results) > 0:
                success_count += 1
                results_by_template[template_id]["success"] += 1
                print(f"  ✓ Success: {len(query_results)} results")
            else:
                empty_results_count += 1
                results_by_template[template_id]["empty"] += 1
                print(f"  ✗ No results")
                failed_queries.append({
                    "id": query_id,
                    "question": question,
                    "sparql": sparql,
                    "template_id": template_id,
                    "issue": "No results returned"
                })

        except Exception as e:
            # Handle errors in SPARQL execution
            error_count += 1
            results_by_template[template_id]["error"] += 1
            print(f"  ✗ Error: {str(e)}")
            failed_queries.append({
                "id": query_id,
                "question": question,
                "sparql": sparql,
                "template_id": template_id,
                "issue": f"Error: {str(e)}"
            })

    # Calculate overall success rate
    success_rate = (success_count / total_queries) * 100 if total_queries > 0 else 0

    # Print detailed summary
    print("\nVerification Summary:")
    print(f"Total queries: {total_queries}")
    print(f"Successful queries with results: {success_count} ({success_rate:.1f}%)")
    print(f"Queries with no results: {empty_results_count}")
    print(f"Failed queries (errors): {error_count}")
    
    # Save failed queries to a file
    if failed_queries:
        failed_queries_file = f"failed_legal_queries.json"
        with open(failed_queries_file, "w", encoding="utf-8") as f:
            json.dump(failed_queries, f, ensure_ascii=False, indent=2)
        print(f"\nFailed queries saved to {failed_queries_file}")
    
    # Print template success rates
    print("\nResults by template:")
    for template, stats in sorted(results_by_template.items(), 
                                 key=lambda x: x[1]["success"] / x[1]["total"] if x[1]["total"] > 0 else 0,
                                 reverse=True):
        success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {template}: {stats['success']}/{stats['total']} successful ({success_rate:.1f}%)")
    
    return {
        "total_queries": total_queries,
        "success_count": success_count,
        "empty_results_count": empty_results_count,
        "error_count": error_count,
        "success_rate": success_rate,
        "failed_queries": failed_queries
    }

def main():
    """Main function to run the verification"""
    # Check if input file exists
    if len(sys.argv) > 1:
        input_json_path = sys.argv[1]
    else:
        input_json_path = "legal_documents_dataset.json"

    if not os.path.exists(input_json_path):
        print(f"Error: Input JSON file '{input_json_path}' not found!")
        sys.exit(1)

    # Run the verification
    verify_sparql_results(input_json_path)

if __name__ == "__main__":
    main()