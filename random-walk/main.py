import os
from dotenv import load_dotenv
import rdflib
import random
import json
import requests
import time
from rdflib import Graph, Namespace, URIRef, Literal, RDF

def generate_dataset_from_ttl(ttl_file, num_samples, min_properties, max_properties, 
                             min_variables, max_variables, gemini_api_key):
    """
    Generate a dataset of question-SPARQL pairs from a TTL file following the algorithm:
    1. Pick a random entity from KG and add to ContextPattern
    2. Set Counter_P to 0
    3. While Counter_P < P:
       a. Pick a random entity e from ContextPattern
       b. Expand e with random property p
       c. Add 1 to Counter_P
    4. Set V random entities in ContextPattern to distinct variables
    5. Generate natural language questions based on the pattern
    
    Args:
        ttl_file: Path to the TTL file
        num_samples: Number of question-SPARQL pairs to generate
        min_properties, max_properties: Range for number of properties to include
        min_variables, max_variables: Range for number of variables to include
        gemini_api_key: API key for the Gemini API
        
    Returns:
        List of dictionaries with keys 'question', 'sparql'
    """
    # Load the TTL file
    g = Graph()
    g.parse(ttl_file, format='ttl')
    
    # Define namespaces
    ns1 = Namespace("http://example.org/")
    rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
    xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    
    # Get all entities (subjects of triples)
    entities = set()
    for s, p, o in g:
        if isinstance(s, URIRef):
            entities.add(s)
    
    # Filter out meta-entities (ontology classes)
    meta_entities = {ns1.course, ns1.evaluation, ns1.course_category, ns1.research_lab, ns1.lab}
    filtered_entities = [e for e in entities if e not in meta_entities]
    
    if not filtered_entities:
        raise ValueError("No entities found in the TTL file after filtering.")
    
    dataset = []
    samples_generated = 0
    attempt_count = 0
    max_attempts = num_samples * 10  # Set a reasonable limit to prevent infinite loops
    
    while samples_generated < num_samples and attempt_count < max_attempts:
        attempt_count += 1
        print(f"Attempting sample {samples_generated + 1}/{num_samples} (attempt {attempt_count})")
        
        # For each sample, determine the number of properties and variables with weighted randomization
        # Create weights that favor lower values (e.g., for range 1-4, weights are [4,3,2,1])
        property_weights = [max_properties - i + 1 for i in range(min_properties, max_properties + 1)]
        variable_weights = [max_variables - i + 1 for i in range(min_variables, max_variables + 1)]
        
        # Use weighted choice for properties and variables
        num_properties = random.choices(
            range(min_properties, max_properties + 1), 
            weights=property_weights, 
            k=1
        )[0]
        
        num_variables = random.choices(
            range(min_variables, max_variables + 1), 
            weights=variable_weights, 
            k=1
        )[0]
        print(f"  Using {num_properties} properties and {num_variables} variables")
        
        # Step 1: Pick a random entity from KG and add to ContextPattern
        random_entity = random.choice(filtered_entities)
        entities_in_context = [random_entity]
        context_pattern = []
        
        # Step 2 & 3: Add properties until we reach the desired count
        counter_p = 0
        property_attempts = 100  # Prevent infinite loops within a single sample
        attempt = 0
        
        while counter_p < num_properties and attempt < property_attempts:
            attempt += 1
            
            # Step 3a: Pick a random entity e from ContextPattern
            entity = random.choice(entities_in_context)
            
            # Step 3b: Expand e with random property p
            # Get all properties for this entity
            properties = []
            for s, p, o in g.triples((entity, None, None)):
                # Skip metadata properties and rdf:type
                if p not in [rdfs.label, rdfs.domain, rdfs.range, rdfs.subPropertyOf, ns1.also_known_as, RDF.type]:
                    properties.append((p, o))
            
            if not properties:
                continue
            
            # Pick a random property
            prop, value = random.choice(properties)
            
            # Check if this triple is already in context_pattern
            if (entity, prop, value) in context_pattern:
                continue
            
            # Add the triple to context_pattern
            context_pattern.append((entity, prop, value))
            
            # Add the value to entities_in_context if it's an entity (URIRef)
            if isinstance(value, URIRef):
                entities_in_context.append(value)
            
            # Increment Counter_P
            counter_p += 1
        
        # If we couldn't generate any properties, skip this sample and try again
        if not context_pattern:
            print(f"  Skipping sample attempt - no valid properties found")
            continue
        
        if counter_p < num_properties:
            print(f"  Warning: Could only generate {counter_p} properties for sample {samples_generated + 1}")
        
        # Step 4: Set V random entities/literals in ContextPattern to distinct variables
        all_elements = []
        for s, p, o in context_pattern:
            all_elements.append(s)
            all_elements.append(o)
        
        # Remove duplicates
        all_elements = list(set(all_elements))
        
        # Remove non-entities and non-literals
        all_elements = [e for e in all_elements if isinstance(e, (URIRef, Literal))]
        
        # Ensure we have enough elements to create variables
        if len(all_elements) < 1:
            print(f"  Skipping sample attempt - not enough elements to create variables")
            continue
        
        # Randomly select elements to replace with variables
        num_vars_to_use = min(num_variables, len(all_elements))
        if num_vars_to_use < num_variables:
            print(f"  Warning: Could only use {num_vars_to_use} variables for sample {samples_generated + 1}")
        
        elements_to_replace = random.sample(all_elements, num_vars_to_use)
        
        # Create a mapping from elements to variables
        variable_mapping = {elem: f"?x{i+1}" for i, elem in enumerate(elements_to_replace)}
        
        # Replace entities with variables in the context_pattern
        query_pattern = []
        for s, p, o in context_pattern:
            new_s = variable_mapping.get(s, s)
            new_o = variable_mapping.get(o, o)
            query_pattern.append((new_s, p, new_o))
        
        # Step 5: Generate a natural language question based on the pattern
        # First get labels for all entities and properties
        label_mapping = {}
        for elem in all_elements + [p for _, p, _ in context_pattern]:
            if isinstance(elem, URIRef):
                for _, _, label in g.triples((elem, rdfs.label, None)):
                    label_mapping[elem] = str(label)
                    break
        
        # Create a description of the pattern for generating a question
        pattern_description = []
        for s, p, o in query_pattern:
            s_label = get_label_or_format(s, label_mapping)
            p_label = get_label_or_format(p, label_mapping)
            o_label = get_label_or_format(o, label_mapping)
            
            pattern_description.append(f"({s_label}, {p_label}, {o_label})")
        
        pattern_text = "\n".join(pattern_description)
        
        # Generate a natural language question using Gemini API
        question = generate_question_with_gemini(pattern_text, gemini_api_key)
        
        # Add a small delay to avoid rate limits
        time.sleep(1)
        
        # Generate SPARQL query
        sparql_query = generate_sparql_query(query_pattern, ns1, rdfs, xsd)
        
        dataset.append({
            "question": question,
            "sparql": sparql_query,
            "num_properties": counter_p,
            "num_variables": num_vars_to_use
        })
        
        # Increment the counter for successful samples
        samples_generated += 1
        print(f"  Successfully generated sample {samples_generated}/{num_samples}")
    
    if samples_generated < num_samples:
        print(f"Warning: Could only generate {samples_generated} samples after {max_attempts} attempts")
    
    return dataset

def get_label_or_format(term, label_mapping):
    """
    Get a human-readable label for a term, or format it appropriately.
    
    Args:
        term: The term to format (URIRef, Literal, or variable string)
        label_mapping: Dictionary mapping URIRefs to their labels
        
    Returns:
        A string representation of the term
    """
    if isinstance(term, str):
        return term  # It's already a variable or formatted
    elif isinstance(term, URIRef) and term in label_mapping:
        return label_mapping[term]
    elif isinstance(term, URIRef):
        # Extract the name from the URI and make it more readable
        return term.split('/')[-1].replace('_', ' ')
    elif isinstance(term, Literal):
        return str(term)
    else:
        return str(term)

def generate_question_with_gemini(pattern_text, api_key):
    """
    Generate a natural language question for the given pattern using the Gemini API.
    
    Args:
        pattern_text: A string describing the pattern
        api_key: The Gemini API key
        
    Returns:
        A natural language question
    """
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""Generate a natural language question in English based on the following RDF triples on a knowledge graph containing university courses:
{pattern_text}

The question should ask for the variables (starting with ?) in the triples. Make the question sound natural and cohesive. Only return the question without any explanation or preamble."""
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 100
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        return response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Return a simple question as fallback
        variables = [part for part in pattern_text.split() if part.startswith('?')]
        return f"What are the values of {', '.join(variables)}?"

def generate_sparql_query(query_pattern, ns1, rdfs, xsd):
    """
    Generate a SPARQL query for the given pattern.
    
    Args:
        query_pattern: List of (subject, predicate, object) triples
        ns1, rdfs, xsd: Namespace objects for formatting
        
    Returns:
        A SPARQL query string
    """
    # Get variables used in the pattern
    variables = set()
    for s, p, o in query_pattern:
        if isinstance(s, str) and s.startswith('?'):
            variables.add(s)
        if isinstance(o, str) and o.startswith('?'):
            variables.add(o)
    
    # Generate prefixes
    prefixes = """PREFIX ns1: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"""
    
    # Generate SELECT clause
    select_clause = "SELECT " + " ".join(sorted(variables)) + " WHERE {"
    
    # Generate WHERE clause
    where_clauses = []
    for s, p, o in query_pattern:
        s_str = format_term_for_sparql(s, ns1, rdfs, xsd)
        p_str = format_term_for_sparql(p, ns1, rdfs, xsd)
        o_str = format_term_for_sparql(o, ns1, rdfs, xsd)
        
        where_clauses.append(f"  {s_str} {p_str} {o_str} .")
    
    # Combine all parts
    query = f"{prefixes}\n{select_clause}\n" + "\n".join(where_clauses) + "\n}"
    
    return query

def format_term_for_sparql(term, ns1, rdfs, xsd):
    """
    Format a term (URIRef, Literal, or variable) for inclusion in a SPARQL query.
    
    Args:
        term: The term to format
        ns1, rdfs, xsd: Namespace objects for formatting
        
    Returns:
        A string representation of the term for SPARQL
    """
    if isinstance(term, str) and term.startswith('?'):
        return term
    elif isinstance(term, URIRef):
        ns1_str = str(ns1)
        rdfs_str = str(rdfs)
        xsd_str = str(xsd)
        
        if str(term).startswith(ns1_str):
            local_name = str(term)[len(ns1_str):]
            return f"ns1:{local_name}"
        elif str(term).startswith(rdfs_str):
            local_name = str(term)[len(rdfs_str):]
            return f"rdfs:{local_name}"
        elif str(term).startswith(xsd_str):
            local_name = str(term)[len(xsd_str):]
            return f"xsd:{local_name}"
        else:
            return f"<{term}>"
    elif isinstance(term, Literal):
        if term.datatype:
            datatype_str = format_term_for_sparql(term.datatype, ns1, rdfs, xsd)
            if str(term.datatype) == str(xsd.string):
                return f'"{term}"'
            else:
                return f'"{term}"^^{datatype_str}'
        elif term.language:
            return f'"{term}"@{term.language}'
        else:
            return f'"{term}"'
    else:
        return str(term)

def generate_statistics(dataset):
    """
    Generate statistics about the generated dataset.
    
    Args:
        dataset: List of dictionaries with keys 'question', 'sparql', 'num_properties', 'num_variables'
    
    Returns:
        A dictionary with various statistics
    """
    property_counts = [item['num_properties'] for item in dataset]
    variable_counts = [item['num_variables'] for item in dataset]
    
    stats = {
        "total_samples": len(dataset),
        "property_distribution": {
            "min": min(property_counts),
            "max": max(property_counts),
            "avg": sum(property_counts) / len(property_counts) if property_counts else 0,
            "counts": {i: property_counts.count(i) for i in range(min(property_counts), max(property_counts) + 1)}
        },
        "variable_distribution": {
            "min": min(variable_counts),
            "max": max(variable_counts),
            "avg": sum(variable_counts) / len(variable_counts) if variable_counts else 0,
            "counts": {i: variable_counts.count(i) for i in range(min(variable_counts), max(variable_counts) + 1)}
        }
    }
    
    return stats

if __name__ == "__main__":
    # Replace with your actual Gemini API key
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    # Increased number of samples
    num_samples = 15
    
    # Range for number of properties per pattern
    min_properties = 1
    max_properties = 4
    
    # Range for number of variables per pattern
    min_variables = 1
    max_variables = 4
    
    # Generate the dataset
    dataset = generate_dataset_from_ttl(
        'final_result.ttl', 
        num_samples, 
        min_properties, 
        max_properties, 
        min_variables, 
        max_variables, 
        gemini_api_key
    )
    
    # Generate and print statistics
    stats = generate_statistics(dataset)
    print("\nDataset Statistics:")
    print(f"Total samples: {stats['total_samples']}")
    print(f"Properties per sample: {stats['property_distribution']['min']}-{stats['property_distribution']['max']} (avg: {stats['property_distribution']['avg']:.2f})")
    print(f"Variables per sample: {stats['variable_distribution']['min']}-{stats['variable_distribution']['max']} (avg: {stats['variable_distribution']['avg']:.2f})")
    
    print("\nProperty distribution:")
    for count, occurrences in stats['property_distribution']['counts'].items():
        print(f"  {count} properties: {occurrences} samples ({occurrences/stats['total_samples']*100:.1f}%)")
    
    print("\nVariable distribution:")
    for count, occurrences in stats['variable_distribution']['counts'].items():
        print(f"  {count} variables: {occurrences} samples ({occurrences/stats['total_samples']*100:.1f}%)")
    
    # Save the dataset to a JSON file
    with open('question_sparql_pairs.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(dataset)} question-SPARQL pairs and saved to question_sparql_pairs.json")