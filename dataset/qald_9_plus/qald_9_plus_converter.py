import json
import sys
import re

def convert_qald9_plus(input_file, output_file):
    """
    Converts QALD-9 Plus dataset format to the simplified format,
    with PREFIX declarations removed from SPARQL queries.
    
    Args:
        input_file (str): Path to the input JSON file (QALD-9 Plus format)
        output_file (str): Path to save the output JSON file
    """
    try:
        # Load the input JSON data
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate input structure
        if not data or 'questions' not in data or not isinstance(data['questions'], list):
            raise ValueError("Invalid input data structure. Expected 'questions' array.")
        
        # Transform the data
        transformed_data = []
        
        for item in data['questions']:
            # Find English question
            english_question = None
            for q in item.get('question', []):
                if q.get('language') == 'en':
                    english_question = q.get('string')
                    break
            
            if not english_question:
                print(f"Warning: Skipping item with ID {item.get('id')}: No English question found")
                continue
            
            # Extract SPARQL query
            sparql_query = item.get('query', {}).get('sparql')
            if not sparql_query:
                print(f"Warning: Skipping item with ID {item.get('id')}: No SPARQL query found")
                continue
            
            # Remove PREFIX declarations
            clean_sparql = remove_prefixes(sparql_query)
            
            # Add to transformed data
            transformed_item = {
                "question": english_question,
                "sparql": clean_sparql
            }
            transformed_data.append(transformed_item)
        
        # Write the transformed data to output file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(transformed_data, f, indent=2, ensure_ascii=False)
        
        print(f"Conversion completed. Processed {len(transformed_data)} questions.")
        return transformed_data
    
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        raise

def remove_prefixes(sparql_query):
    """
    Removes PREFIX declarations from a SPARQL query.
    
    Args:
        sparql_query (str): SPARQL query with PREFIX declarations
    
    Returns:
        str: SPARQL query without PREFIX declarations
    """
    # Regex to match PREFIX declarations
    prefix_pattern = re.compile(r'PREFIX\s+[^:]+:\s*<[^>]+>\s*', re.IGNORECASE)
    
    # Remove all PREFIX declarations
    clean_sparql = prefix_pattern.sub('', sparql_query).strip()
    
    return clean_sparql

def main():
    if len(sys.argv) != 3:
        print("Usage: python qald_converter.py <input_file.json> <output_file.json>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    convert_qald9_plus(input_file, output_file)

if __name__ == "__main__":
    main()