#!/usr/bin/env python3
"""
Clear RDF Triple Extractor
Shows complete triples in an easy-to-read format
"""

from rdflib import Graph
from collections import defaultdict
import sys

def extract_and_display_triples(file_path):
    """Extract all properties and show complete triples for each"""
    
    # Parse the RDF file
    g = Graph()
    g.parse(file_path, format="turtle")
    
    print("🔍 RDF TRIPLE EXTRACTION RESULTS")
    print("=" * 80)
    print(f"📊 Total triples parsed: {len(g)}")
    
    # Group triples by property (predicate)
    property_triples = defaultdict(list)
    
    for subject, predicate, obj in g:
        triple = {
            'subject': str(subject),
            'predicate': str(predicate), 
            'object': str(obj)
        }
        property_triples[str(predicate)].append(triple)
    
    # Sort properties by frequency
    sorted_properties = sorted(property_triples.items(), 
                              key=lambda x: len(x[1]), 
                              reverse=True)
    
    print(f"🏷️  Found {len(property_triples)} unique properties\n")
    
    # Summary table
    print("PROPERTY SUMMARY:")
    print("-" * 80)
    print(f"{'#':<3} {'Property Name':<25} {'Count':<8} {'Full URI'}")
    print("-" * 80)
    
    for i, (prop_uri, triples) in enumerate(sorted_properties, 1):
        prop_name = prop_uri.split('/')[-1].split('#')[-1]
        print(f"{i:<3} {prop_name:<25} {len(triples):<8} {prop_uri}")
    
    print("\n" + "=" * 100)
    print("COMPLETE TRIPLES FOR EACH PROPERTY (UP TO 10 EXAMPLES)")
    print("=" * 100)
    
    # Show detailed triples for each property
    for i, (prop_uri, triples) in enumerate(sorted_properties, 1):
        prop_name = prop_uri.split('/')[-1].split('#')[-1]
        
        print(f"\n🏷️  PROPERTY #{i}: {prop_name}")
        print(f"   Full URI: {prop_uri}")
        print(f"   Total occurrences: {len(triples)}")
        print(f"\n   📋 COMPLETE TRIPLES (showing up to 10):")
        print("   " + "─" * 95)
        
        for j, triple in enumerate(triples[:3], 1):
            # Shorten URIs for readability
            subj_display = shorten_for_display(triple['subject'])
            obj_display = shorten_for_display(triple['object'])
            
            # Show the triple in multiple formats
            print(f"\n   TRIPLE #{j}:")
            print(f"   ┌─ Subject:   {subj_display}")
            print(f"   ├─ Predicate: {prop_name}")
            print(f"   └─ Object:    {obj_display}")
            
            # Show as RDF notation
            print(f"   📝 RDF: <{triple['subject']}> <{triple['predicate']}> <{triple['object']}> .")
            
            # Show as visual arrow
            print(f"   🔗 Visual: {shorten_for_display(triple['subject'], 30)} ──({prop_name})──> {shorten_for_display(triple['object'], 30)}")
            
            if j < len(triples[:3]):
                print("   " + "·" * 50)
    
    # Additional statistics
    print("\n" + "=" * 80)
    print("📊 STATISTICS")
    print("=" * 80)
    
    total_triples = sum(len(triples) for triples in property_triples.values())
    print(f"📈 Total triples: {total_triples}")
    print(f"🏷️  Unique properties: {len(property_triples)}")
    print(f"📊 Average triples per property: {total_triples/len(property_triples):.1f}")
    
    # Find most frequently used subjects
    subject_counts = defaultdict(int)
    for triples in property_triples.values():
        for triple in triples:
            subject_counts[triple['subject']] += 1
    
    print(f"\n🔗 Most connected subjects (entities with most properties):")
    top_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    for subj, count in top_subjects:
        print(f"   • {shorten_for_display(subj, 60)}: {count} properties")
    
    # Property type analysis
    lex2kg_props = sum(1 for prop in property_triples.keys() if 'lex2kg' in prop)
    standard_props = len(property_triples) - lex2kg_props
    
    print(f"\n📋 Property types:")
    print(f"   • lex2kg-specific properties: {lex2kg_props}")
    print(f"   • Standard RDF properties: {standard_props}")

def shorten_for_display(uri, max_length=50):
    """Shorten URI for better display"""
    if len(uri) <= max_length:
        return uri
    
    if uri.startswith('http'):
        if '#' in uri:
            parts = uri.split('#')
            if len(parts[-1]) < max_length - 10:
                return f"...#{parts[-1]}"
        elif '/' in uri:
            parts = uri.split('/')
            if len(parts[-1]) < max_length - 10:
                return f".../{parts[-1]}"
    
    return uri[:max_length-3] + "..."

def main():
    if len(sys.argv) != 2:
        print("Usage: python clear_triple_extractor.py <path_to_rdf_file>")
        print("\nExample: python clear_triple_extractor.py my_data.ttl")
        return
    
    file_path = sys.argv[1]
    
    try:
        extract_and_display_triples(file_path)
        print(f"\n✅ Triple extraction complete!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()