#!/usr/bin/env python3

"""
Test script to verify that intermediate and advanced queries are being generated properly
"""

import json
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from nl2sparql_generator import NL2SPARQLGenerator

def test_complexity_generation():
    """Test that all complexity levels are being generated"""
    
    # Simple configuration for testing
    config = {
        "prefixes": {
            "schema": "https://schema.org/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        },
        "entityExamples": [],
        "schemaInfo": {"properties": []}
    }
    
    # Create generator
    generator = NL2SPARQLGenerator(config)
    
    print("Testing MIXED complexity distribution...")
    mixed_dataset = generator.generate_dataset(
        size=30,
        complexity_distribution={"basic": 0.4, "intermediate": 0.4, "advanced": 0.2}
    )
    
    # Count actual distribution
    complexity_counts = {"basic": 0, "intermediate": 0, "advanced": 0}
    for item in mixed_dataset:
        complexity_counts[item["complexity"]] += 1
    
    print(f"Generated {len(mixed_dataset)} total queries")
    print("Actual complexity distribution:")
    for complexity, count in complexity_counts.items():
        percentage = (count / len(mixed_dataset)) * 100 if mixed_dataset else 0
        print(f"  {complexity}: {count} ({percentage:.1f}%)")
    
    # Show examples of each complexity
    for complexity in ["basic", "intermediate", "advanced"]:
        examples = [item for item in mixed_dataset if item["complexity"] == complexity]
        if examples:
            print(f"\nSample {complexity} query:")
            print(f"  Question: {examples[0]['question']}")
            print(f"  Template: {examples[0]['templateId']}")
            if complexity != "basic":
                print(f"  SPARQL: {examples[0]['sparql'][:100]}...")

if __name__ == "__main__":
    test_complexity_generation()
