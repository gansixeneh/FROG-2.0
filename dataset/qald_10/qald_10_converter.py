import json
import re

def convert_qald_format(input_file, output_file):
    # Load the QALD-10 JSON data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create the new format
    result = []
    
    for question_item in data['questions']:
        # Get the English question
        english_question = ""
        for q in question_item['question']:
            if q['language'] == 'en':
                english_question = q['string']
                break
        
        # Get the SPARQL query
        sparql_query = question_item['query']['sparql']
        
        # Remove prefixes from SPARQL query
        if sparql_query:
            # Pattern to match PREFIX declarations
            prefix_pattern = r'PREFIX\s+[^>]+>\s+'
            # Remove all PREFIX declarations
            sparql_query = re.sub(prefix_pattern, '', sparql_query)
        
        # Add to result
        result.append({
            "question": english_question,
            "sparql": sparql_query
        })
    
    # Write the result to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Conversion complete. Output saved to {output_file}")

# Example usage
input_file = "qald_10.json"
output_file = "qald_10_converted.json"
convert_qald_format(input_file, output_file)
