import json
import re
import random

def upper_case_sparql(sparql_query):
    """Convert SPARQL keywords to uppercase."""
    # Define a list of SPARQL keywords
    keywords = [
        "SELECT", "WHERE", "FILTER", "BIND", "UNION", "ORDER BY", "COUNT", "AS",
        "GROUP BY", "LIMIT", "OFFSET", "DISTINCT", "ASK"
    ]
    
    # Convert each keyword to uppercase
    for keyword in keywords:
        sparql_query = re.sub(r'\b' + keyword + r'\b', keyword.upper(), sparql_query, flags=re.IGNORECASE)
    
    return sparql_query

def replace_uri_with_prefix(sparql_query):
    """Replace URIs in the SPARQL query with a prefix."""
    # Replace the URI with a prefix
    sparql_query = re.sub(r'<https://example\.org/lex2kg/ontology/([^>]+)>', r'lex2kg-o:\1', sparql_query)
    return sparql_query

def remove_spaces_before_chars(sparql_query):
    """Remove spaces before ? and . in SPARQL queries"""
    # Remove spaces before ? that has one space before it
    modified_query = re.sub(r'(?<! ) \?', '?', sparql_query)
    # Remove spaces before .
    modified_query = re.sub(r'(?<! ) \.', '.', modified_query)
    
    return modified_query

def format_sparql_query(query):
    """
    Format a SPARQL query with proper indentation.
    Comprehensive handling of various SPARQL clauses.
    """
    # Clean up the query
    query = query.strip()
    
    # Fix common formatting issues
    query = re.sub(r'BYDESC', 'BY DESC', query, flags=re.IGNORECASE)
    
    # Format basic query structure
    if "WHERE" in query and "{" in query and "}" in query:
        # Split the query at WHERE
        before_where, after_where = query.split("WHERE", 1)
        before_where = before_where.strip()
        after_where = after_where.strip()
        
        # Handle the WHERE clause
        opening_brace_index = after_where.find("{")
        closing_brace_index = after_where.rfind("}")
        
        if opening_brace_index != -1 and closing_brace_index != -1:
            # Get the content inside braces
            content = after_where[opening_brace_index+1:closing_brace_index].strip()
            
            # Format the content with proper indentation
            indented_content = format_where_content(content)
            
            # Get any clauses after the closing brace
            after_clause = after_where[closing_brace_index+1:].strip()
            formatted_after = format_after_clauses(after_clause)
            
            # Build the formatted query
            formatted_query = f"{before_where}\nWHERE {{\n{indented_content}\n}}"
            
            # Add any remaining clauses
            if formatted_after:
                formatted_query += formatted_after
            
            return formatted_query
    
    # Special case for ASK queries
    if query.startswith("ASK") and "WHERE" in query:
        return format_ask_query(query)
    
    # If we can't format it well, return as is
    return query

def format_where_content(content):
    """
    Format the content inside a WHERE clause with proper indentation.
    Handles triple patterns, FILTER, BIND, UNION, etc.
    """
    # Handle empty content
    if not content:
        return ""
    
    formatted_lines = []
    
    # First handle special clauses like FILTER, BIND, UNION
    content = handle_special_clauses(content)
    
    # Split into lines, respecting special clauses
    lines = re.split(r'\s*\.\s*(?![^{]*})', content)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Add a period if it's missing
        if not (line.endswith(".") or line.endswith("}") or "FILTER" in line or "BIND" in line):
            line += " ."
            
        # Handle multiple predicates with the same subject (semicolons)
        if ";" in line:
            semicolon_parts = handle_semicolons(line)
            formatted_lines.extend(semicolon_parts)
        else:
            # Regular line
            formatted_lines.append("  " + line)
    
    return "\n".join(formatted_lines)

def handle_semicolons(line):
    """Handle lines with semicolons by properly indenting them."""
    result = []
    parts = line.split(";")
    
    # First part gets normal indentation
    result.append("  " + parts[0].strip() + " ;")
    
    # Middle parts get extra indentation
    for i in range(1, len(parts) - 1):
        part = parts[i].strip()
        if part:
            result.append("       " + part + " ;")
    
    # Last part gets extra indentation and proper ending
    last_part = parts[-1].strip()
    if last_part:
        # Check if it ends with a period
        if last_part.endswith("."):
            result.append("       " + last_part)
        else:
            result.append("       " + last_part + " .")
    
    return result

def handle_special_clauses(content):
    """
    Pre-process special clauses like FILTER, BIND, UNION.
    """
    # Handle FILTER clauses - ensure they're on their own line
    content = re.sub(r'([^.;])\s+FILTER', r'\1 .\nFILTER', content)
    
    # Handle BIND clauses - ensure they're on their own line
    content = re.sub(r'([^.;])\s+BIND', r'\1 .\nBIND', content)
    
    # Handle UNION clauses - ensure they're formatted properly
    content = re.sub(r'UNION\s*{', r'UNION {', content)
    
    # Handle nested braces in FILTER, UNION, etc.
    # This is a simplistic approach - a full parser would be more robust
    
    return content

def format_after_clauses(after_clause):
    """
    Format clauses that come after the main WHERE block,
    like GROUP BY, ORDER BY, LIMIT, OFFSET, etc.
    """
    if not after_clause:
        return ""
    
    formatted = ""
    
    # Handle common clauses
    clauses = ["GROUP BY", "ORDER BY", "LIMIT", "OFFSET", "HAVING"]
    
    for clause in clauses:
        if clause in after_clause:
            # Split by the clause
            parts = after_clause.split(clause)
            before = parts[0].strip()
            after = clause + ' ' + parts[1].strip()
            
            if before:
                formatted += f" {before}"
            formatted += f"\n{after}"
            
            print("After clause:", after_clause)
            print("Formatted:", formatted)
            
            # We've processed this clause
            return formatted
    
    # If no recognized clause, just add as is
    return f" {after_clause}"

def format_ask_query(query):
    """Special formatting for ASK queries."""
    # Split into ASK and WHERE parts
    parts = query.split("WHERE", 1)
    ask_part = parts[0].strip()
    where_part = "WHERE" + parts[1].strip()
    
    # Extract content inside braces
    opening_brace_index = where_part.find("{")
    closing_brace_index = where_part.rfind("}")
    
    if opening_brace_index != -1 and closing_brace_index != -1:
        # Get the content inside braces
        content = where_part[opening_brace_index+1:closing_brace_index].strip()
        
        # Format the content
        indented_content = format_where_content(content)
        
        # Build the formatted query
        return f"{ask_part}\nWHERE {{\n{indented_content}\n}}"
    
    # Fallback
    return query

def process_json(json_data):
    """Process the JSON data and add entity and property labels."""
    for item in json_data:
        if 'sparql' in item:
            item['sparql'] = upper_case_sparql(item['sparql'])
            item['sparql'] = replace_uri_with_prefix(item['sparql'])
            item['sparql'] = format_sparql_query(item['sparql'])
            item['sparql'] = remove_spaces_before_chars(item['sparql'])
    
    return json_data

# Main function to process the files
def main():
    # Load the JSON file
    with open('legal.json', 'r') as f:
        json_data = json.load(f)

    # Process the data
    result = process_json(json_data)
    
    # Handle more than 150 rows by randomly sampling
    if len(result) > 150:
        print(f"Dataset has {len(result)} rows. Randomly sampling 150 rows.")
        result = random.sample(result, 150)
    
    # Split into train (100) and test (50) sets
    random.shuffle(result)  # Shuffle to ensure random distribution
    
    train_data = result[:100]
    test_data = result[100:150]
    
    # Save training data
    train_file = 'legal_train.json'
    with open(train_file, 'w') as f:
        json.dump(train_data, f, indent=2)
    
    # Save test data
    test_file = 'legal_test.json'
    with open(test_file, 'w') as f:
        json.dump(test_data, f, indent=2)

    print(f"Processing complete.")
    print(f"Training data ({len(train_data)} rows) saved to {train_file}.")
    print(f"Test data ({len(test_data)} rows) saved to {test_file}.")

if __name__ == "__main__":
    main()