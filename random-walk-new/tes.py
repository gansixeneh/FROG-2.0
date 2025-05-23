"""
Example usage of the Pattern-Based SPARQL Generator

This example demonstrates how to use the new pattern-based approach to generate
SPARQL queries with various complexity levels and connection patterns.
"""

import json
import os
import sys
from gen import PatternBasedSPARQLGenerator

def generate_pattern_based_dataset(ttl_file='final_result.ttl', output_size=200):
    """
    Generate a pattern-based dataset from the university course TTL file
    
    Args:
        ttl_file (str): Path to the TTL file
        output_size (int): Number of queries to generate
        
    Returns:
        list: Generated dataset
    """
    try:
        print(f"Generating pattern-based dataset from {ttl_file}")
        
        # Initialize the pattern-based generator
        generator = PatternBasedSPARQLGenerator(ttl_file)
        
        # You can customize the pattern weights if needed
        # generator.pattern_weights = {
        #     1: 0.4,  # 40% 1-property patterns
        #     2: 0.35, # 35% 2-property patterns  
        #     3: 0.25  # 25% 3-property patterns
        # }
        
        # Generate the dataset
        print(f"Generating {output_size} pattern-based queries...")
        dataset = generator.generate_dataset(size=output_size)
        
        # Export to both JSON and CSV
        json_output = 'pattern_based_university_dataset.json'
        csv_output = 'pattern_based_university_dataset.csv'
        
        generator.export_json(dataset, json_output)
        generator.export_csv(dataset, csv_output)
        
        print(f"Dataset exported to:")
        print(f"  - JSON: {json_output}")
        print(f"  - CSV: {csv_output}")
        
        # Show some statistics
        analyze_dataset(dataset)
        
        return dataset
        
    except Exception as e:
        print(f"Error generating pattern-based dataset: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_dataset(dataset):
    """Analyze the generated dataset and show statistics"""
    
    from collections import Counter
    
    print(f"\n=== Dataset Analysis ===")
    print(f"Total queries generated: {len(dataset)}")
    
    # Complexity distribution
    complexity_counts = Counter()
    pattern_type_counts = Counter()
    
    for item in dataset:
        complexity_counts[item['complexity']] += 1
        pattern_type_counts[item['pattern_type']] += 1
    
    print("\nComplexity Distribution:")
    for complexity in ['basic', 'intermediate', 'advanced']:
        count = complexity_counts[complexity]
        percentage = (count / len(dataset)) * 100
        print(f"  {complexity}: {count} ({percentage:.1f}%)")
    
    print("\nPattern Type Distribution:")
    for pattern_type, count in pattern_type_counts.most_common(10):
        percentage = (count / len(dataset)) * 100
        print(f"  {pattern_type}: {count} ({percentage:.1f}%)")
    
    # Show sample queries for each complexity
    print("\n=== Sample Queries ===")
    
    for complexity in ['basic', 'intermediate', 'advanced']:
        samples = [item for item in dataset if item['complexity'] == complexity][:3]
        print(f"\n{complexity.capitalize()} Queries:")
        
        for i, sample in enumerate(samples, 1):
            print(f"  {i}. {sample['id']} ({sample['pattern_type']})")
            print(f"     {sample['sparql']}")
            print()

def validate_generated_queries(dataset, ttl_file='final_result.ttl'):
    """
    Validate that the generated queries actually work against the TTL file
    
    Args:
        dataset (list): Generated dataset
        ttl_file (str): Path to TTL file
    """
    from rdflib import Graph
    
    print(f"\n=== Query Validation ===")
    print("Loading RDF graph for validation...")
    
    graph = Graph()
    graph.parse(ttl_file, format='turtle')
    
    print(f"Loaded graph with {len(graph)} triples")
    
    # Test a sample of queries
    sample_size = min(20, len(dataset))
    sample_queries = dataset[:sample_size]
    
    successful = 0
    empty_results = 0
    errors = 0
    
    print(f"Testing {sample_size} sample queries...")
    
    for item in sample_queries:
        try:
            results = list(graph.query(item['sparql']))
            if len(results) > 0:
                successful += 1
                print(f"  ✓ {item['id']}: {len(results)} results")
            else:
                empty_results += 1
                print(f"  ○ {item['id']}: No results")
        except Exception as e:
            errors += 1
            print(f"  ✗ {item['id']}: Error - {e}")
    
    print(f"\nValidation Summary:")
    print(f"  Successful queries: {successful}/{sample_size} ({successful/sample_size*100:.1f}%)")
    print(f"  Empty results: {empty_results}/{sample_size} ({empty_results/sample_size*100:.1f}%)")
    print(f"  Errors: {errors}/{sample_size} ({errors/sample_size*100:.1f}%)")

def demonstrate_pattern_types():
    """Show examples of different pattern types"""
    
    print("\n=== Pattern Type Examples ===")
    
    print("1-Property Patterns:")
    print("  • Subject Target: ?target ns1:has_credits 3 .")
    print("  • Object Target:  ns1:machine_learning ns1:has_credits ?target .")
    
    print("\n2-Property Patterns:")
    print("  • Middle Target: ns1:course1 ns1:has_prerequisite ?target . ?target ns1:has_credits 4 .")
    print("  • Branching:     ?target ns1:has_research_group ?hidden . ?hidden ns1:has_course ns1:course1 .")
    
    print("\n3-Property Patterns:")
    print("  • Linear End:    ns1:course1 ns1:has_prerequisite ?h1 . ?h1 ns1:has_category ?h2 . ?h2 ns1:has_credits ?target .")
    print("  • Linear Middle: ns1:course1 ns1:has_prerequisite ?h . ?h ns1:has_evaluation ?target . ?target ns1:has_code ns1:code1 .")
    print("  • Star:          ?hidden ns1:has_course ns1:course1 . ?hidden ns1:has_student ?h2 . ?hidden ns1:has_grade ?target .")

def main():
    """Main function to demonstrate the pattern-based generator"""
    
    # Check if TTL file exists
    ttl_file = 'final_result.ttl'
    if not os.path.exists(ttl_file):
        print(f"Error: {ttl_file} not found!")
        print("Please ensure the university course TTL file is in the current directory.")
        sys.exit(1)
    
    print("=== Pattern-Based SPARQL Generator Demo ===")
    
    # Show what patterns we can generate
    demonstrate_pattern_types()
    
    # Generate the dataset
    dataset = generate_pattern_based_dataset(ttl_file, output_size=300)
    
    if dataset:
        print("\nDataset generated successfully!")
        
        # Validate some queries
        validate_generated_queries(dataset, ttl_file)
        
        print("\n=== Next Steps ===")
        print("1. The generated queries are now ready for question generation using LLM")
        print("2. You can use the JSON file as input to an LLM to generate natural language questions")
        print("3. The pattern_type field helps the LLM understand what kind of question to generate")
        print("4. Example prompt: 'Generate a natural language question for this SPARQL query: [query]'")
        
    else:
        print("Failed to generate dataset!")

if __name__ == "__main__":
    main()