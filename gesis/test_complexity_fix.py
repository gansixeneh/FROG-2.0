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
        "entityExamples": [
            {
                "value": "schema:Author1", 
                "label": "Dr. Jane Smith", 
                "uri": "https://data.gesis.org/gesiskg/resource/author-001", 
                "type": "schema:Person"
            },
            {
                "value": "schema:Publication1", 
                "label": "Social Media Research Study", 
                "uri": "https://data.gesis.org/gesiskg/resource/publication-001", 
                "type": "schema:CreativeWork"
            }
        ],
        "schemaInfo": {
            "properties": []
        }
    }
    
    # Create generator
    generator = NL2SPARQLGenerator(config)
    
    # Test each complexity level separately
    print("Testing BASIC queries...")
    basic_dataset = generator.generate_dataset(
        size=10,
        complexity_distribution={"basic": 1.0, "intermediate": 0.0, "advanced": 0.0}
    )
    print(f"Generated {len(basic_dataset)} basic queries")
    if basic_dataset:
        print(f"Sample basic query: {basic_dataset[0]['question']}")
        print(f"Sample basic complexity: {basic_dataset[0]['complexity']}")
    
    print("\n" + "="*50 + "\n")
    
    print("Testing INTERMEDIATE queries...")
    intermediate_dataset = generator.generate_dataset(
        size=10,
        complexity_distribution={"basic": 0.0, "intermediate": 1.0, "advanced": 0.0}
    )
    print(f"Generated {len(intermediate_dataset)} intermediate queries")
    if intermediate_dataset:
        print(f"Sample intermediate query: {intermediate_dataset[0]['question']}")
        print(f"Sample intermediate complexity: {intermediate_dataset[0]['complexity']}")
        print(f"Sample intermediate SPARQL: {intermediate_dataset[0]['sparql']}")
    
    print("\n" + "="*50 + "\n")
    
    print("Testing ADVANCED queries...")
    advanced_dataset = generator.generate_dataset(
        size=10,
        complexity_distribution={"basic": 0.0, "intermediate": 0.0, "advanced": 1.0}
    )
    print(f"Generated {len(advanced_dataset)} advanced queries")
    if advanced_dataset:
        print(f"Sample advanced query: {advanced_dataset[0]['question']}")
        print(f"Sample advanced complexity: {advanced_dataset[0]['complexity']}")
        print(f"Sample advanced SPARQL: {advanced_dataset[0]['sparql']}")
    
    print("\n" + "="*50 + "\n")
    
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

if __name__ == "__main__":
    test_complexity_generation()
