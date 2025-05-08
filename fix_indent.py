import json
import re
import os
import sys

def format_sparql_query(query):
    """
    Format a SPARQL query with proper indentation.
    Comprehensive handling of various SPARQL clauses.
    """
    # Clean up the query
    query = query.strip()
    
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
    lines = re.split(r'\s*\.\s+(?![^{]*})', content)
    
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
            after = clause + parts[1].strip()
            
            if before:
                formatted += f" {before}"
            formatted += f"\n{after}"
            
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

def process_json_file(data):
    """
    Process a data object containing SPARQL queries and return the processed data.
    """
    # Create a copy of the data to avoid modifying the original
    processed_data = data.copy()
    
    # Format each query
    for item in processed_data:
        if 'sparql' in item and item['sparql']:
            item['sparql'] = format_sparql_query(item['sparql'])
    
    return processed_data

def main():
    input_file = "dataset\possible_uris\qald_9_plus_test_wikidata_converted_labels_possible_uris.json"
    
    # Create output filename
    file_dir = os.path.dirname(input_file)
    file_name = os.path.basename(input_file)
    file_base, file_ext = os.path.splitext(file_name)
    output_file = os.path.join(file_dir, f"{file_base}_indented{file_ext}")
    
    print(f"Reading from: {input_file}")
    print(f"Writing to  : {output_file}")
    
    # Load the input file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Process SPARQL queries
    print("Indenting SPARQL queries...")
    indented_data = process_json_file(data)
    
    # Write the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(indented_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully processed {len(data)} queries")
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    main()