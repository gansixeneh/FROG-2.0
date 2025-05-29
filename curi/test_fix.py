#!/usr/bin/env python3
"""
Simple test to verify the property_retrieval.py file is syntactically correct
and that the Weaviate query method signature is fixed.
"""

import sys
import os

def test_import():
    """Test if the property retrieval module can be imported"""
    try:
        from property_retrieval import UniversityPropertyRetrieval
        print("✓ Successfully imported UniversityPropertyRetrieval")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error during import: {e}")
        return False

def test_class_structure():
    """Test if the class has the expected methods"""
    try:
        from property_retrieval import UniversityPropertyRetrieval
        
        # Check if key methods exist
        expected_methods = [
            '__init__',
            'search_entities', 
            'search_properties',
            '_search',
            'get_related_candidates'
        ]
        
        for method in expected_methods:
            if hasattr(UniversityPropertyRetrieval, method):
                print(f"✓ Method {method} exists")
            else:
                print(f"✗ Method {method} missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking class structure: {e}")
        return False

def test_search_method_signature():
    """Test if the _search method uses the correct Weaviate query syntax"""
    try:
        import inspect
        from property_retrieval import UniversityPropertyRetrieval
        
        # Read the source code of the _search method
        source = inspect.getsource(UniversityPropertyRetrieval._search)
        
        # Check for the correct hybrid query syntax
        if "collection.query.hybrid(" in source:
            print("✓ Uses correct Weaviate hybrid query syntax")
            
            # Check for the specific parameters we're looking for
            if "query_properties=[\"label\"]" in source:
                print("✓ Uses correct query_properties parameter")
            if "return_metadata=weaviate.classes.query.MetadataQuery(score=True)" in source:
                print("✓ Uses correct return_metadata parameter")
            if "limit=k" in source:
                print("✓ Uses correct limit parameter")
                
            return True
        else:
            print("✗ Does not use correct Weaviate hybrid query syntax")
            return False
            
    except Exception as e:
        print(f"✗ Error checking search method: {e}")
        return False

def main():
    """Run all tests"""
    print("Testing property_retrieval.py implementation...")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Import
    print("\n1. Testing import...")
    if not test_import():
        all_passed = False
    
    # Test 2: Class structure
    print("\n2. Testing class structure...")
    if not test_class_structure():
        all_passed = False
    
    # Test 3: Search method signature
    print("\n3. Testing search method syntax...")
    if not test_search_method_signature():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed! The Weaviate query issue should be fixed.")
    else:
        print("✗ Some tests failed.")
    
    return all_passed

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
