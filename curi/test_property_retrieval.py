#!/usr/bin/env python3
"""
Test script for the University Property Retrieval system
This demonstrates how to use the Weaviate-based property retrieval independently
"""

import sys
import os
from property_retrieval import UniversityPropertyRetrieval


def test_property_retrieval():
    """Test the University Property Retrieval system"""
    
    # Check if the TTL file exists
    ttl_file = 'final_result.ttl'
    if not os.path.exists(ttl_file):
        print(f"Error: {ttl_file} not found!")
        print("Please ensure the university course TTL file is in the current directory.")
        return
    
    print("Testing University Property Retrieval System")
    print("=" * 50)
    
    # Define SPARQL queries
    get_entities_query = """
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label
    (REPLACE(STR(?entity), "http://example.org/", "ns1:") AS ?short)
WHERE {
  { 
    ?entity ?predicate ?object. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  UNION
  { 
    ?subject ?predicate ?entity. 
    FILTER(isIRI(?entity) && STRSTARTS(STR(?entity), STR(ns1:)) && STRSTARTS(STR(?predicate), STR(ns1:)))
  }
  
  OPTIONAL {
    ?entity rdfs:label ?label.
  }
}
"""
    
    get_properties_query = """
PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT
    ?label 
    (REPLACE(STR(?property), "http://example.org/", "ns1:") AS ?short) 
    (REPLACE(REPLACE(STR(?domain), "http://example.org/", "ns1:"), "http://www.w3.org/2000/01/rdf-schema#", "rdfs:") AS ?shortDomain)
    (REPLACE(REPLACE(STR(?range), "http://example.org/", "ns1:"), "http://www.w3.org/2001/XMLSchema#", "xsd:") AS ?shortRange)
WHERE {
  ?subject ?property ?object.
  FILTER(STRSTARTS(STR(?property), STR(ns1:)))
  
  OPTIONAL {
    ?property rdfs:label ?label.
    ?property rdfs:domain ?domain.
    ?property rdfs:range ?range.
  }
}
"""
    
    try:
        # Initialize the property retrieval system
        print("Initializing University Property Retrieval...")
        retrieval = UniversityPropertyRetrieval(
            turtle_file_path=ttl_file,
            get_entities_query=get_entities_query,
            get_properties_query=get_properties_query,
            embedding_model_name="jinaai/jina-embeddings-v3",
            is_local_client=True,
            weaviate_host="localhost",
            weaviate_port=8080,
        )
        
        print("\n" + "=" * 50)
        print("TESTING ENTITY SEARCH")
        print("=" * 50)
        
        # Test entity search
        test_queries = [
            "machine learning",
            "database",
            "programming",
            "computer vision",
            "artificial intelligence"
        ]
        
        for query in test_queries:
            print(f"\nSearching entities for: '{query}'")
            results = retrieval.search_entities(query, k=3)
            print(f"Found {len(results)} results:")
            for _, row in results.iterrows():
                print(f"  - {row['label']} ({row['short']}) - Score: {row['score']:.3f}")
        
        print("\n" + "=" * 50)
        print("TESTING PROPERTY SEARCH")
        print("=" * 50)
        
        # Test property search
        property_queries = [
            "credits",
            "prerequisite",
            "evaluation",
            "research group",
            "category"
        ]
        
        for query in property_queries:
            print(f"\nSearching properties for: '{query}'")
            results = retrieval.search_properties(query, k=3)
            print(f"Found {len(results)} results:")
            for _, row in results.iterrows():
                domain = row.get('shortDomain', '')
                range_val = row.get('shortRange', '')
                domain_info = f" (Domain: {domain}, Range: {range_val})" if domain or range_val else ""
                print(f"  - {row['label']} ({row['short']}){domain_info} - Score: {row['score']:.3f}")
        
        print("\n" + "=" * 50)
        print("TESTING RELATED CANDIDATES")
        print("=" * 50)
        
        # Test get_related_candidates
        test_question = "What courses have 3 credits and use test as evaluation method?"
        print(f"\nQuestion: '{test_question}'")
        candidates = retrieval.get_related_candidates(test_question, threshold=0.4, k=5)
        
        print("\nRelated Entity Candidates:")
        for entity in candidates['entities'][:5]:
            print(f"  - {entity}")
        
        print("\nRelated Property Candidates:")
        for prop in candidates['properties'][:5]:
            print(f"  - {prop}")
        
        print("\n" + "=" * 50)
        print("SUCCESS: All tests completed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_property_retrieval()
