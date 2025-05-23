import os
from dotenv import load_dotenv
import rdflib
import random
import json
import requests
import re
import time
from datetime import datetime
from rdflib import Graph, Namespace, URIRef, Literal, RDF

def format_property_label(property_uri):
    """Format a property URI into a readable label"""
    if not isinstance(property_uri, URIRef):
        return str(property_uri)
        
    p_name = str(property_uri).split('/')[-1]
    
    # Map property names to more readable labels
    property_mapping = {
        "has_course_code": "has course code",
        "has_credits": "has credits",
        "has_evaluation_method": "has evaluation method",
        "has_prerequisite_course": "has prerequisite course",
        "has_research_group": "has research group",
        "has_course_category": "has course category",
        "has_minimum_credits": "has minimum credits",
        "also_known_as": "is also known as"
    }
    
    # First check if it's in our mapping
    if p_name in property_mapping:
        return property_mapping[p_name]
    
    # Otherwise, format it by replacing underscores with spaces
    return p_name.replace('_', ' ')

def get_human_readable_label(g, term, label_cache=None):
    """Get a human-readable label for a term"""
    if label_cache is None:
        label_cache = {}
        
    if isinstance(term, str):
        return term  # It's already a variable
    elif isinstance(term, URIRef):
        # Check if label is in cache
        if term in label_cache:
            return label_cache[term]
            
        # Check for rdfs:label
        rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
        labels = list(g.objects(term, rdfs.label))
        if labels:
            label = str(labels[0])
            label_cache[term] = label
            return label
            
        # If no label found, return the last part of the URI
        uri_str = str(term)
        label = uri_str.split('/')[-1].replace('_', ' ')
        label_cache[term] = label
        return label
    elif isinstance(term, Literal):
        str_value = str(term)
        if len(str_value) > 50:
            return str_value[:47] + "..."
        return str_value
    else:
        return str(term)

def create_variable_name(entity, index, g):
    """Create a meaningful variable name based on entity type"""
    if isinstance(entity, URIRef):
        uri_str = str(entity)
        
        # Default variable name
        var_name = f"?var{index+1}"
        
        # Check if it's a course
        if "course" in uri_str.lower() or g.value(entity, RDF.type) == URIRef("http://example.org/course"):
            var_name = f"?course{index+1}"
        # Check if it's an evaluation method
        elif "evaluation" in uri_str.lower() or g.value(entity, RDF.type) == URIRef("http://example.org/evaluation"):
            var_name = f"?evaluation{index+1}"
        # Check if it's a research lab/group
        elif "lab" in uri_str.lower() or "research" in uri_str.lower() or g.value(entity, RDF.type) == URIRef("http://example.org/research_lab"):
            var_name = f"?research_group{index+1}"
        # Check if it's a course category
        elif "category" in uri_str.lower() or g.value(entity, RDF.type) == URIRef("http://example.org/course_category"):
            var_name = f"?category{index+1}"
    else:
        # For literals or other values
        var_name = f"?value{index+1}"
    
    return var_name

def identify_query_structure(triples):
    """
    Identify the structure of the query (path, tree, etc.) and nodes in sequence.
    Returns the structure type and a list of nodes in sequential order if possible.
    """
    if not triples:
        return "empty", []
        
    # For a single triple
    if len(triples) == 1:
        s, p, o = triples[0]
        return "path", [s, o]
        
    # Try to identify a path structure
    node_connections = {}
    # Count connections for each node
    for s, p, o in triples:
        if s not in node_connections:
            node_connections[s] = []
        if o not in node_connections:
            node_connections[o] = []
            
        node_connections[s].append(o)
        node_connections[o].append(s)
    
    # Find endpoints (nodes with only one connection)
    endpoints = [node for node, connections in node_connections.items() 
                 if len(set(connections)) == 1]
    
    # If we have exactly 2 endpoints, we might have a path
    if len(endpoints) == 2:
        # Try to reconstruct the path
        path = [endpoints[0]]
        current = endpoints[0]
        
        while len(path) < len(node_connections):
            # Get connections for current node
            connections = set(node_connections[current])
            # Remove the previous node in the path (if any)
            if len(path) > 1:
                connections.discard(path[-2])
                
            # If there are no more connections or more than one, it's not a simple path
            if len(connections) != 1:
                return "complex", []
                
            # Add the next node to the path
            next_node = list(connections)[0]
            path.append(next_node)
            current = next_node
            
            # If we reached the other endpoint, we're done
            if current == endpoints[1]:
                break
        
        # Verify that we've included all nodes
        if set(path) == set(node_connections.keys()):
            return "path", path
    
    # If not a path, categorize as "complex" for now
    return "complex", []

def create_path_based_variable_mapping(g, path, num_variables):
    """
    Create a strategic variable mapping based on the identified path structure.
    Ensures that variables are chosen to create a coherent query without redundant triples.
    """
    if len(path) < num_variables:
        # Can't have more variables than nodes
        num_variables = len(path)
    
    # For paths, we want to select variables strategically
    if len(path) == 2:  # 1-hop path (A-B)
        # Choose either A or B to be the variable
        entity_to_replace = random.choice(path)
        return {entity_to_replace: create_variable_name(entity_to_replace, 0, g)}
        
    elif len(path) == 3:  # 2-hop path (A-B-C)
        # Must have 2 variables - either A,B or B,C to avoid redundancy
        if num_variables == 2:
            if random.choice([True, False]):
                # Choose A and B
                return {
                    path[0]: create_variable_name(path[0], 0, g),
                    path[1]: create_variable_name(path[1], 1, g)
                }
            else:
                # Choose B and C
                return {
                    path[1]: create_variable_name(path[1], 0, g),
                    path[2]: create_variable_name(path[2], 1, g)
                }
        else:
            # If we want only 1 variable (which might not be ideal), choose B
            return {path[1]: create_variable_name(path[1], 0, g)}
            
    elif len(path) == 4:  # 3-hop path (A-B-C-D)
        if num_variables == 3:
            # Choose 3 variables - either A,B,C or B,C,D
            if random.choice([True, False]):
                return {
                    path[0]: create_variable_name(path[0], 0, g),
                    path[1]: create_variable_name(path[1], 1, g),
                    path[2]: create_variable_name(path[2], 2, g)
                }
            else:
                return {
                    path[1]: create_variable_name(path[1], 0, g),
                    path[2]: create_variable_name(path[2], 1, g),
                    path[3]: create_variable_name(path[3], 2, g)
                }
        elif num_variables == 2:
            # Choose B and C to avoid redundancy
            return {
                path[1]: create_variable_name(path[1], 0, g),
                path[2]: create_variable_name(path[2], 1, g)
            }
    
    # For more complex cases, select variables strategically
    # Score entities based on their position and connectivity
    scores = {}
    for i, entity in enumerate(path):
        # Entities in the middle of the path are more important
        position_score = 1 - abs(i - (len(path)-1)/2) / (len(path)-1)
        scores[entity] = position_score
    
    # Sort entities by score
    sorted_entities = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    # Select the top entities based on num_variables
    mapping = {}
    for i, (entity, _) in enumerate(sorted_entities[:num_variables]):
        mapping[entity] = create_variable_name(entity, i, g)
    
    return mapping

def find_next_entity_for_path(g, current_path, used_entities, max_path_length):
    """
    Find the next entity to extend the path, ensuring we're building a meaningful path structure.
    Returns a tuple of (next_entity, connecting_predicate, is_subject) where is_subject indicates 
    if the next entity is in subject position with respect to the last entity in the path.
    """
    if not current_path or len(current_path) >= max_path_length:
        return None, None, None
    
    last_entity = current_path[-1]
    
    # Try to find outgoing connections (where last_entity is the subject)
    outgoing_connections = []
    for s, p, o in g.triples((last_entity, None, None)):
        if o not in used_entities and o != last_entity and isinstance(o, URIRef):
            # Avoid metadata predicates
            if p not in [rdflib.RDFS.label, rdflib.RDFS.domain, rdflib.RDFS.range, 
                         rdflib.RDFS.subPropertyOf, rdflib.RDF.type]:
                outgoing_connections.append((o, p, True))
    
    # Try to find incoming connections (where last_entity is the object)
    incoming_connections = []
    for s, p, o in g.triples((None, None, last_entity)):
        if s not in used_entities and s != last_entity and isinstance(s, URIRef):
            # Avoid metadata predicates
            if p not in [rdflib.RDFS.label, rdflib.RDFS.domain, rdflib.RDFS.range, 
                         rdflib.RDFS.subPropertyOf, rdflib.RDF.type]:
                incoming_connections.append((s, p, False))
    
    # Combine all possibilities
    all_connections = outgoing_connections + incoming_connections
    
    if not all_connections:
        return None, None, None
    
    # Select a connection with preference for building a meaningful path
    # Score connections based on their properties
    scored_connections = []
    for entity, pred, is_subject in all_connections:
        score = 0
        
        # Prefer connections that continue the topic of the path
        predicate_name = str(pred).split('/')[-1]
        if any(topic in predicate_name for topic in ['prerequisite', 'course', 'credits', 'evaluation']):
            score += 5
        
        # Prefer entities that are courses if the path is about courses
        if 'course' in str(entity).lower() or g.value(entity, RDF.type) == URIRef("http://example.org/course"):
            score += 3
        
        scored_connections.append((entity, pred, is_subject, score))
    
    # Sort by score and use weighted random selection
    scored_connections.sort(key=lambda x: x[3], reverse=True)
    weights = [max(0.1, conn[3]) for conn in scored_connections]
    total_weight = sum(weights)
    weights = [w/total_weight for w in weights]
    
    selected_conn = random.choices(scored_connections, weights=weights, k=1)[0]
    return selected_conn[0], selected_conn[1], selected_conn[2]

def build_path_pattern(g, start_predicate, max_hops):
    """
    Build a coherent path pattern starting with a selected predicate.
    Returns a tuple of (pattern, path_entities) where pattern is a list of triples
    and path_entities is a list of entities in sequential order.
    """
    # Find all triples with this predicate
    triples_with_predicate = list(g.triples((None, start_predicate, None)))
    if not triples_with_predicate:
        return [], []
    
    # Pick a random triple with this predicate
    initial_triple = random.choice(triples_with_predicate)
    subject, predicate, object_ = initial_triple
    
    # Initialize the pattern and path
    pattern = [initial_triple]
    
    # Determine which direction to extend the path
    if random.choice([True, False]) or not isinstance(subject, URIRef):
        # Extend from object
        path = [subject, object_]
        current = object_
    else:
        # Extend from subject
        path = [object_, subject]
        current = subject
    
    used_entities = set(path)
    
    # Extend the path up to max_hops
    while len(pattern) < max_hops:
        next_entity, connecting_pred, is_subject = find_next_entity_for_path(
            g, path, used_entities, max_hops + 1)
        
        if next_entity is None:
            break
        
        # Add the new triple to the pattern
        if is_subject:
            pattern.append((current, connecting_pred, next_entity))
            path.append(next_entity)
        else:
            pattern.append((next_entity, connecting_pred, current))
            path = [next_entity] + path
        
        used_entities.add(next_entity)
        current = next_entity
    
    return pattern, path

def determine_optimal_variable_count(path_length):
    """
    Determine the optimal number of variables based on path length.
    Following the improved logic:
    - 1-hop: 1 variable
    - 2-hop: 2 variables
    - 3-hop: 2 or 3 variables
    """
    if path_length == 2:  # 1-hop (A-B)
        return 1
    elif path_length == 3:  # 2-hop (A-B-C)
        return 2
    elif path_length == 4:  # 3-hop (A-B-C-D)
        return random.choice([2, 3])
    else:
        return min(path_length - 1, 3)  # Fallback

def create_detailed_pattern_description(query_pattern, g, label_cache=None):
    """Create a detailed description of the pattern"""
    if label_cache is None:
        label_cache = {}
        
    pattern_description = []
    for s, p, o in query_pattern:
        s_label = get_human_readable_label(g, s, label_cache)
        p_label = format_property_label(p)
        o_label = get_human_readable_label(g, o, label_cache)
        
        pattern_description.append(f"({s_label}, {p_label}, {o_label})")
    
    return "\n".join(pattern_description)

def extract_entity_info_from_pattern(g, query_pattern, variable_mapping):
    """Extract entity information from pattern for template filling"""
    # Extract key information from entities
    entity_info = {}
    label_cache = {}
    
    # Get labels for all entities in the pattern
    for s, p, o in query_pattern:
        if isinstance(s, URIRef):
            get_human_readable_label(g, s, label_cache)
        if isinstance(o, URIRef):
            get_human_readable_label(g, o, label_cache)
    
    # Analyze the pattern for specific entity types
    for entity, var_name in variable_mapping.items():
        if isinstance(entity, URIRef):
            # Extract information about courses
            if g.value(entity, RDF.type) == URIRef("http://example.org/course") or any(g.triples((entity, URIRef("http://example.org/has_course_code"), None))):
                entity_info["course_name"] = get_human_readable_label(g, entity, label_cache)
                
                # Get course code
                course_codes = list(g.objects(entity, URIRef("http://example.org/has_course_code")))
                if course_codes:
                    entity_info["course_code"] = str(course_codes[0])
                
                # Get credits
                credits = list(g.objects(entity, URIRef("http://example.org/has_credits")))
                if credits:
                    entity_info["credits"] = str(credits[0])
                    
                # Get prerequisites
                prereqs = list(g.objects(entity, URIRef("http://example.org/has_prerequisite_course")))
                if prereqs:
                    entity_info["has_prereq"] = True
                    if len(prereqs) == 1:
                        entity_info["prereq_name"] = get_human_readable_label(g, prereqs[0], label_cache)
            
            # Extract information about evaluation methods
            elif g.value(entity, RDF.type) == URIRef("http://example.org/evaluation"):
                entity_info["evaluation_method"] = get_human_readable_label(g, entity, label_cache)
            
            # Extract information about research groups
            elif g.value(entity, RDF.type) == URIRef("http://example.org/research_lab"):
                entity_info["research_group"] = get_human_readable_label(g, entity, label_cache)
            
            # Extract information about course categories
            elif g.value(entity, RDF.type) == URIRef("http://example.org/course_category"):
                entity_info["course_category"] = get_human_readable_label(g, entity, label_cache)
            
            # Add label for all entities
            entity_info["entity_label"] = get_human_readable_label(g, entity, label_cache)
    
    return entity_info

def extract_variable_contents(g, variable_mapping, context_pattern):
    """Extract actual content for variables to provide better context for question generation"""
    variable_contents = {}
    
    for entity, var_name in variable_mapping.items():
        if isinstance(entity, Literal):
            variable_contents[var_name] = str(entity)
        elif isinstance(entity, URIRef):
            # Look for content associated with this entity
            rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
            ns1 = Namespace("http://example.org/")
            
            # Try to get label first
            labels = list(g.objects(entity, rdfs.label))
            if labels:
                variable_contents[var_name] = str(labels[0])
            
            # Try to get course code
            course_codes = list(g.objects(entity, ns1.has_course_code))
            if course_codes:
                if var_name not in variable_contents:
                    variable_contents[var_name] = str(course_codes[0])
                else:
                    variable_contents[var_name] += f" (Code: {str(course_codes[0])})"
            
            # Try to get also_known_as
            also_known = list(g.objects(entity, ns1.also_known_as))
            if also_known:
                aka_str = ", ".join([str(aka) for aka in also_known])
                if var_name not in variable_contents:
                    variable_contents[var_name] = f"Also known as: {aka_str}"
                else:
                    variable_contents[var_name] += f" (Also known as: {aka_str})"
    
    return variable_contents

def generate_questions_for_predicate(g, pred_name, pattern_description, query_pattern, 
                                     variable_mapping, variable_contents, gemini_api_key=None, query_complexity=None, selected_variable=None):
    """Generate questions based on the relationship type and query complexity"""
    # Extract metadata from pattern for templates
    entity_info = extract_entity_info_from_pattern(g, query_pattern, variable_mapping)
    
    # Try to generate with Gemini API if available
    if gemini_api_key:
        # Add information about the selected variable to guide question generation
        selected_var_info = f"\nSelected Variable: {selected_variable}" if selected_variable else ""
        template_info = f"Relationship type: {pred_name}\nPattern: {pattern_description}\nEntity info: {entity_info}\nVariable contents: {variable_contents}\nQuery complexity: {query_complexity}{selected_var_info}"
        questions = generate_questions_with_gemini(template_info, gemini_api_key, variable_mapping, variable_contents, query_complexity, query_pattern, selected_variable)
        if questions and questions.get("indonesian") and questions.get("english"):
            # Ensure no variable placeholders in questions
            for var_name in variable_mapping:
                if var_name in questions["indonesian"] or var_name in questions["english"]:
                    # If variables still appear, try again with templates
                    return generate_questions_from_templates(pred_name, entity_info, variable_contents, query_complexity, query_pattern, selected_variable)
            
            return questions
    
    # Fallback to templates if no API or API failed
    return generate_questions_from_templates(pred_name, entity_info, variable_contents, query_complexity, query_pattern, selected_variable)

def generate_questions_with_gemini(pattern_text, api_key, variable_mapping, variable_contents, query_complexity=None, query_pattern=None, selected_variable=None):
    """Generate bilingual questions with improved prompting for specificity"""
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Prepare context about variables
    variable_context = "\n\nVARIABLE INFORMATION:\n"
    for var_name, content in variable_contents.items():
        short_content = content[:100] + "..." if len(content) > 100 else content
        if var_name == selected_variable:
            variable_context += f"{var_name} - content: {short_content} (THIS IS THE SELECTED VARIABLE FOR THE QUERY)\n"
        else:
            variable_context += f"{var_name} - content: {short_content}\n"
    
    # Add context about query complexity
    complexity_context = ""
    if query_complexity:
        complexity_context = f"\n\nQUERY COMPLEXITY: {query_complexity}\n"
        if query_complexity == "filter":
            complexity_context += "This query includes a FILTER condition. Your question should ask about courses that meet specific criteria like 'more than X credits' or 'taught by specific research group'."
        elif query_complexity == "count":
            complexity_context += "This query counts entities. Your question should ask about counting or the number of courses with certain properties."
        elif query_complexity == "optional":
            complexity_context += "This query includes OPTIONAL information. Your question should ask for primary information and optional additional details if available."
    
    # Add context about query pattern to ensure alignment
    query_context = ""
    if query_pattern:
        query_context = "\n\nQUERY PATTERN TYPE:"
        
        if selected_variable:
            query_context += f"\nThis query is asking specifically about {selected_variable} in the context of the other variables."
            query_context += f"\nThe question should focus on finding the value of {selected_variable} given the other constraints."
        else:
            # Analyze pattern to determine basic structure
            subject_is_variable = False
            object_is_variable = False
            
            if len(query_pattern) > 0:
                s, p, o = query_pattern[0]
                subject_is_variable = isinstance(s, str) and s.startswith('?')
                object_is_variable = isinstance(o, str) and o.startswith('?')
                
                if subject_is_variable and not object_is_variable:
                    query_context += "\nThis query is asking for COURSES that have a specific property or relationship."
                    query_context += "\nExample: 'Which courses belong to the Study Program Elective Course category?'"
                elif not subject_is_variable and object_is_variable:
                    query_context += "\nThis query is asking for PROPERTIES of a specific course."
                    query_context += "\nExample: 'What is the category of the Database course?'"
                elif subject_is_variable and object_is_variable:
                    query_context += "\nThis query is asking for relationships between variables."
                    query_context += "\nExample: 'What courses have which prerequisites?'"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""Generate two versions of a natural language question (one in Bahasa Indonesia and one in English) based on the following information about university courses:
{pattern_text}
{variable_context}
{complexity_context}
{query_context}

CRITICAL REQUIREMENTS FOR BOTH LANGUAGES:

1. BE EXTREMELY SPECIFIC - Your questions MUST include ALL specific identifiers found in the pattern
2. If you see specific entities like "Advanced Programming with course code CSCM602223", your question MUST mention these exact identifiers
3. DO NOT generate generic questions about courses, credits, or education systems in general
4. Each question should be asking for specific information about the specific course entities mentioned
5. NEVER include variable placeholders like "?value1" or "?course1" in the questions - replace these with descriptive phrases like "apa" or "yang mana" for Indonesian, or "what", "which" for English
6. When asking for content represented by a variable, use natural phrasing like "apa" or "what"
7. If query complexity is specified, make sure the question reflects that complexity (filters, counting, optional information)
8. MOST IMPORTANT: Your question MUST align perfectly with the SPARQL query pattern. If the query asks for "What courses have category X", your question CANNOT ask "Does course Y have category X"
9. If a specific variable is selected, the question should be focused on finding THAT variable's value

Examples of GOOD questions:
- "Berapa jumlah kredit untuk mata kuliah Advanced Programming dengan kode CSCM602223?"
- "How many credits does the Advanced Programming course with code CSCM602223 have?"
- "Mata kuliah apa yang menjadi prasyarat untuk Compiler Techniques?"
- "What courses are prerequisites for Compiler Techniques?"
- "Berapa banyak mata kuliah yang diajarkan oleh laboratorium Reliable Software Engineering?" (for COUNT queries)
- "Which courses have more than 3 credits and are in the Faculty Mandatory Course category?" (for FILTER queries)
- "Mata kuliah apa saja yang termasuk dalam kategori Study Program Elective Course?" (for queries about multiple courses)

Examples of BAD questions to AVOID:
- "Bagaimana sistem kredit dalam dunia pendidikan universitas?"
- "How does the university credit system work?"
- "Apa isi dari ?course1 dengan kode ?value1?"
- "What is the content of ?course1 with code ?value1?"
- "Apakah mata kuliah Robotics termasuk dalam kategori Study Program Elective Course?" (when the query asks for all courses in that category)

Format your response exactly as follows:
Indonesian: [Question in Bahasa Indonesia]
English: [Question in English]

Remember: BE SPECIFIC! Use the entity labels and information in the pattern and phrase questions naturally without variable placeholders. Make sure your question matches the SPARQL query pattern."""
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 200
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        response_text = response_json["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Parse both questions from the response
        id_match = re.search(r'Indonesian:\s*(.*?)(?:\n|$)', response_text)
        en_match = re.search(r'English:\s*(.*?)(?:\n|$)', response_text)
        
        indonesian_question = id_match.group(1).strip() if id_match else None
        english_question = en_match.group(1).strip() if en_match else response_text
        
        # Post-process to ensure no variable placeholders
        if indonesian_question:
            for var_name in variable_mapping:
                indonesian_question = indonesian_question.replace(var_name, "yang dicari")
        
        if english_question:
            for var_name in variable_mapping:
                english_question = english_question.replace(var_name, "the requested information")
        
        return {
            "indonesian": indonesian_question,
            "english": english_question
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def generate_questions_from_templates(pred_name, entity_info, variable_contents, query_complexity=None, query_pattern=None, selected_variable=None):
    """Generate questions using templates based on the predicate type"""
    # Define templates by predicate type
    templates = {
        "has_prerequisite_course": [
            {"id": "Mata kuliah apa yang menjadi prasyarat untuk {course_name}?",
             "en": "What courses are prerequisites for {course_name}?"},
            {"id": "Apa prasyarat yang diperlukan untuk mengambil mata kuliah {course_name}?",
             "en": "What are the prerequisites required to take {course_name}?"}
        ],
        "has_course_code": [
            {"id": "Apa kode mata kuliah untuk {course_name}?",
             "en": "What is the course code for {course_name}?"},
            {"id": "Kode mata kuliah apa yang dimiliki oleh {course_name}?",
             "en": "What course code does {course_name} have?"}
        ],
        "has_credits": [
            {"id": "Berapa jumlah kredit untuk mata kuliah {course_name}?",
             "en": "How many credits does the {course_name} course have?"},
            {"id": "Berapa SKS yang dimiliki oleh mata kuliah {course_name}?",
             "en": "How many credits are assigned to the {course_name} course?"}
        ],
        "has_evaluation_method": [
            {"id": "Metode evaluasi apa yang digunakan dalam mata kuliah {course_name}?",
             "en": "What evaluation methods are used in the {course_name} course?"},
            {"id": "Bagaimana cara penilaian di mata kuliah {course_name}?",
             "en": "How is the assessment done in the {course_name} course?"}
        ],
        "has_research_group": [
            {"id": "Kelompok riset apa yang terkait dengan mata kuliah {course_name}?",
             "en": "What research groups are associated with the {course_name} course?"},
            {"id": "Laboratorium riset mana yang mengampu mata kuliah {course_name}?",
             "en": "Which research laboratories oversee the {course_name} course?"}
        ],
        "has_course_category": [
            {"id": "Mata kuliah {course_name} termasuk dalam kategori apa?",
             "en": "What category does the {course_name} course belong to?"},
            {"id": "Apa kategori dari mata kuliah {course_name}?",
             "en": "What is the category of the {course_name} course?"}
        ],
        "also_known_as": [
            {"id": "Apa saja nama lain atau singkatan untuk mata kuliah {course_name}?",
             "en": "What are other names or abbreviations for the {course_name} course?"},
            {"id": "Dikenal dengan nama apa lagi mata kuliah {course_name}?",
             "en": "What else is the {course_name} course known as?"}
        ]
    }
    
    # Additional templates for complex queries
    if query_complexity == "filter":
        filter_templates = [
            {"id": "Mata kuliah apa yang memiliki lebih dari {credits} kredit dan diajarkan oleh {research_group}?",
             "en": "What courses have more than {credits} credits and are taught by {research_group}?"},
            {"id": "Diantara mata kuliah kategori {course_category}, mana yang memiliki kredit kurang dari {credits}?",
             "en": "Among the {course_category} courses, which ones have fewer than {credits} credits?"}
        ]
        if pred_name in templates:
            templates[pred_name].extend(filter_templates)
            
    elif query_complexity == "count":
        count_templates = [
            {"id": "Berapa banyak mata kuliah yang diajarkan oleh {research_group}?",
             "en": "How many courses are taught by {research_group}?"},
            {"id": "Berapa jumlah mata kuliah dalam kategori {course_category}?",
             "en": "What is the number of courses in the {course_category} category?"}
        ]
        if pred_name in templates:
            templates[pred_name].extend(count_templates)
            
    elif query_complexity == "optional":
        optional_templates = [
            {"id": "Apa kode dan jumlah kredit mata kuliah {course_name}, dan jika tersedia, apa prasyaratnya?",
             "en": "What is the code and credit count for the {course_name} course, and if available, what are its prerequisites?"},
            {"id": "Berikan detail mata kuliah {course_name} termasuk metode evaluasi jika ada?",
             "en": "Provide details about the {course_name} course including evaluation methods if any?"}
        ]
        if pred_name in templates:
            templates[pred_name].extend(optional_templates)
    
    # Default templates if the predicate doesn't have specific templates
    default_templates = [
        {"id": "Apa informasi tentang mata kuliah {entity_label}?",
         "en": "What information exists about the {entity_label} course?"},
        {"id": "Berikan informasi mengenai mata kuliah {entity_label}.",
         "en": "Provide information about the {entity_label} course."}
    ]
    
    # Select and fill template
    template_list = templates.get(pred_name, default_templates)
    template = random.choice(template_list)
    
    try:
        # Add some placeholder values for complex queries if needed
        if query_complexity and query_complexity != "basic":
            if "credits" not in entity_info:
                entity_info["credits"] = str(random.randint(2, 4))
            if "research_group" not in entity_info:
                entity_info["research_group"] = "Reliable Software Engineering"
            if "course_category" not in entity_info:
                entity_info["course_category"] = "Study Program Elective Course"
        
        id_question = template["id"].format(**entity_info)
        en_question = template["en"].format(**entity_info)
        
        return {
            "indonesian": id_question,
            "english": english_question
        }
    except KeyError as e:
        # If template has placeholders we can't fill, use fallback
        return {
            "indonesian": f"Apa informasi tentang mata kuliah {entity_info.get('entity_label', '')}?",
            "english": f"What information exists about the {entity_info.get('entity_label', '')} course?"
        }

def generate_complex_sparql_query(query_pattern, query_complexity=None):
    """
    Generate a more complex SPARQL query based on the pattern.
    Depending on the complexity level, adds filters, aggregations, etc.
    MODIFIED: Only select one variable in the SELECT clause
    """
    # Get variables used in the pattern
    variables = set()
    for s, p, o in query_pattern:
        if isinstance(s, str) and s.startswith('?'):
            variables.add(s)
        if isinstance(o, str) and o.startswith('?'):
            variables.add(o)
    
    if not variables:
        # If no variables, return a basic query format
        query = "SELECT * WHERE { " + " ".join([f"{s} {p} {o} ." for s, p, o in query_pattern]) + " }"
        return query, "basic"
    
    # Select only one variable for the SELECT clause
    selected_variable = random.choice(list(variables))
    
    # If no complexity specified, choose based on pattern
    if query_complexity is None:
        if len(variables) >= 2 and len(query_pattern) >= 3:
            # More variables and triples enable more complex queries
            query_complexity = random.choice(["filter", "count", "optional", "basic"])
        else:
            query_complexity = "basic"
    
    # Generate query based on complexity
    if query_complexity == "filter" and len(variables) >= 2:
        # Generate a query with a FILTER
        numeric_variables = []
        for var in variables:
            # Find if this variable appears in an object position with a numeric predicate
            for s, p, o in query_pattern:
                if o == var and (
                    "credits" in str(p) or 
                    "minimum" in str(p) or 
                    "number" in str(p)
                ):
                    numeric_variables.append(var)
                    break
        
        if numeric_variables:
            # Create a FILTER on a numeric variable
            filter_var = random.choice(numeric_variables)
            filter_value = random.randint(1, 5)  # Common value range for credits
            filter_op = random.choice([">", ">=", "<", "<=", "="])
            
            # Build the query with only the selected variable
            select_clause = f"SELECT {selected_variable} WHERE {{"
            where_clauses = []
            for s, p, o in query_pattern:
                s_str = format_term_for_sparql(s)
                p_str = format_term_for_sparql(p)
                o_str = format_term_for_sparql(o)
                where_clauses.append(f"{s_str} {p_str} {o_str} .")
            
            filter_clause = f"FILTER({filter_var} {filter_op} {filter_value})"
            query = select_clause + " " + " ".join(where_clauses) + " " + filter_clause + " }"
            return query, query_complexity, selected_variable
    
    elif query_complexity == "count":
        # Generate a COUNT query
        # With count, we're counting instances of the selected variable
        select_clause = f"SELECT (COUNT({selected_variable}) AS ?count) WHERE {{"
        where_clauses = []
        for s, p, o in query_pattern:
            s_str = format_term_for_sparql(s)
            p_str = format_term_for_sparql(p)
            o_str = format_term_for_sparql(o)
            where_clauses.append(f"{s_str} {p_str} {o_str} .")
        
        query = select_clause + " " + " ".join(where_clauses) + " }"
        return query, query_complexity, "?count"  # Return ?count as the selected variable for count queries
    
    elif query_complexity == "optional" and len(query_pattern) >= 2:
        # Generate a query with an OPTIONAL clause
        # Split pattern into main and optional parts
        optional_start = random.randint(1, len(query_pattern)-1)
        main_pattern = query_pattern[:optional_start]
        optional_pattern = query_pattern[optional_start:]
        
        # Build the query with only the selected variable
        select_clause = f"SELECT {selected_variable} WHERE {{"
        
        # Main pattern
        main_clauses = []
        for s, p, o in main_pattern:
            s_str = format_term_for_sparql(s)
            p_str = format_term_for_sparql(p)
            o_str = format_term_for_sparql(o)
            main_clauses.append(f"{s_str} {p_str} {o_str} .")
        
        # Optional pattern
        optional_clauses = []
        for s, p, o in optional_pattern:
            s_str = format_term_for_sparql(s)
            p_str = format_term_for_sparql(p)
            o_str = format_term_for_sparql(o)
            optional_clauses.append(f"{s_str} {p_str} {o_str} .")
        
        optional_part = "OPTIONAL { " + " ".join(optional_clauses) + " }"
        query = select_clause + " " + " ".join(main_clauses) + " " + optional_part + " }"
        return query, query_complexity, selected_variable
    
    # Default to basic query with only the selected variable
    select_clause = f"SELECT {selected_variable} WHERE {{"
    where_clauses = []
    for s, p, o in query_pattern:
        s_str = format_term_for_sparql(s)
        p_str = format_term_for_sparql(p)
        o_str = format_term_for_sparql(o)
        where_clauses.append(f"{s_str} {p_str} {o_str} .")
    
    query = select_clause + " " + " ".join(where_clauses) + " }"
    return query, "basic", selected_variable

def format_term_for_sparql(term):
    """
    Format a term (URIRef, Literal, or variable) for inclusion in a SPARQL query.
    """
    if isinstance(term, str) and term.startswith('?'):
        return term
    elif isinstance(term, URIRef):
        return f"<{term}>"
    elif isinstance(term, Literal):
        if term.datatype:
            return f'"{term}"^^<{term.datatype}>'
        elif term.language:
            return f'"{term}"@{term.language}'
        else:
            return f'"{term}"'
    else:
        return str(term)

def generate_statistics(dataset):
    """
    Generate statistics about the generated dataset.
    """
    property_counts = [item['num_properties'] for item in dataset]
    variable_counts = [item['num_variables'] for item in dataset]
    relation_types = [item.get('relation_type', 'unknown') for item in dataset]
    query_complexities = [item.get('query_complexity', 'unknown') for item in dataset]
    
    stats = {
        "total_samples": len(dataset),
        "property_distribution": {
            "min": min(property_counts) if property_counts else 0,
            "max": max(property_counts) if property_counts else 0,
            "avg": sum(property_counts) / len(property_counts) if property_counts else 0,
            "counts": {i: property_counts.count(i) for i in range(min(property_counts), max(property_counts) + 1)} if property_counts else {}
        },
        "variable_distribution": {
            "min": min(variable_counts) if variable_counts else 0,
            "max": max(variable_counts) if variable_counts else 0,
            "avg": sum(variable_counts) / len(variable_counts) if variable_counts else 0,
            "counts": {i: variable_counts.count(i) for i in range(min(variable_counts), max(variable_counts) + 1)} if variable_counts else {}
        },
        "relation_type_distribution": {
            type_name: relation_types.count(type_name) for type_name in set(relation_types)
        },
        "query_complexity_distribution": {
            complexity: query_complexities.count(complexity) for complexity in set(query_complexities)
        }
    }
    
    return stats

def generate_improved_dataset(ttl_file, num_samples, max_hops=3, gemini_api_key=None):
    """
    Generate a dataset of question-SPARQL pairs from a TTL file using the improved approach:
    1. Pick a random relationship type (edge) from the knowledge graph
    2. Build a coherent path pattern with 1-3 hops
    3. Set variables strategically based on the path length:
       - 1-hop: 1 variable
       - 2-hop: 2 variables
       - 3-hop: 2-3 variables
    4. Select only one variable for the SELECT clause
    5. Generate natural language questions based on the pattern
    """
    # Load the TTL file
    g = Graph()
    g.parse(ttl_file, format='ttl')
    
    # Define namespaces
    ns1 = Namespace("http://example.org/")
    rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
    xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    
    # Get all unique predicates (edge types) in the graph
    predicates = set()
    for s, p, o in g:
        if isinstance(p, URIRef) and 'http://example.org/' in str(p):
            predicates.add(p)
    
    # Filter out meta-predicates
    filtered_predicates = [p for p in predicates if not any(meta in str(p).lower() 
                                                          for meta in ["label", "domain", "range", "subproperty"])]
    
    # Track predicate usage to ensure balanced coverage
    predicate_usage = {p: 0 for p in filtered_predicates}
    
    dataset = []
    samples_generated = 0
    attempt_count = 0
    max_attempts = num_samples * 10  # Set a reasonable limit to prevent infinite loops
    
    while samples_generated < num_samples and attempt_count < max_attempts:
        attempt_count += 1
        print(f"Attempting sample {samples_generated + 1}/{num_samples} (attempt {attempt_count})")
        
        # Step 1: Select an edge type (predicate) with weighted probability favoring underused predicates
        weights = [1 / (predicate_usage[p] + 1) for p in filtered_predicates]
        selected_predicate = random.choices(filtered_predicates, weights=weights, k=1)[0]
        
        # Step 2: Determine the number of hops for this sample (1-3)
        num_hops = random.randint(1, max_hops)
        
        # Step 3: Build a coherent path pattern
        pattern, path = build_path_pattern(g, selected_predicate, num_hops)
        
        if not pattern or len(path) < 2:
            print(f"  Failed to build a valid path pattern")
            continue
        
        # Step 4: Determine the optimal number of variables based on path length
        num_variables = determine_optimal_variable_count(len(path))
        
        # Step 5: Create strategic variable mapping based on the path
        variable_mapping = create_path_based_variable_mapping(g, path, num_variables)
        
        if not variable_mapping:
            print(f"  Failed to create variable mapping")
            continue
        
        # Step 6: Replace elements with variables in pattern
        query_pattern = []
        for s, p, o in pattern:
            new_s = variable_mapping.get(s, s)
            new_o = variable_mapping.get(o, o)
            query_pattern.append((new_s, p, new_o))
        
        # Step 7: Extract contents for variables to provide better context
        variable_contents = extract_variable_contents(g, variable_mapping, pattern)
        
        # Step 8: Create pattern description with human-readable labels
        pattern_description = create_detailed_pattern_description(query_pattern, g)
        
        # Step 9: Get the predicate name for relationship-specific processing
        pred_name = str(selected_predicate).split('/')[-1]
        
        # Step 10: Generate SPARQL query with complexity appropriate to the pattern
        # This now returns the selected variable as well
        sparql_query, query_complexity, selected_variable = generate_complex_sparql_query(query_pattern)
        
        # Step 11: Generate questions based on relationship type, query complexity, and selected variable
        questions = generate_questions_for_predicate(
            g, pred_name, pattern_description, query_pattern, 
            variable_mapping, variable_contents, gemini_api_key, query_complexity, selected_variable)
        
        # Add to dataset
        dataset.append({
            "question": questions["indonesian"],
            "englishQuestion": questions["english"],
            "sparql": sparql_query,
            "relation_type": pred_name,
            "num_properties": len(pattern),
            "num_variables": len(variable_mapping),
            "query_complexity": query_complexity,
            "selected_variable": selected_variable
        })
        
        # Update usage count for this predicate
        predicate_usage[selected_predicate] += 1
        
        # Increment counter for successful samples
        samples_generated += 1
        print(f"  Successfully generated sample {samples_generated}/{num_samples}")
        print(f"  Indonesian: {questions['indonesian']}")
        print(f"  English: {questions['english']}")
        print(f"  Path length: {len(path)}, Properties: {len(pattern)}, Variables: {len(variable_mapping)}")
        print(f"  Selected variable: {selected_variable}")
    
    if samples_generated < num_samples:
        print(f"Warning: Could only generate {samples_generated} samples after {max_attempts} attempts")
    
    return dataset

if __name__ == "__main__":
    # Optional: Load Gemini API key from environment variables
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    # Number of samples to generate
    num_samples = 15
    
    # Maximum number of hops per pattern
    max_hops = 3
    
    # Generate the dataset using improved approach
    dataset = generate_improved_dataset(
        'final_result.ttl', 
        num_samples, 
        max_hops,
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
    
    print("\nRelation type distribution:")
    for rel_type, occurrences in stats['relation_type_distribution'].items():
        print(f"  {rel_type}: {occurrences} samples ({occurrences/stats['total_samples']*100:.1f}%)")
        
    print("\nQuery complexity distribution:")
    for complexity, occurrences in stats['query_complexity_distribution'].items():
        print(f"  {complexity}: {occurrences} samples ({occurrences/stats['total_samples']*100:.1f}%)")
    
    # Save the dataset to a JSON file
    with open('question_sparql_pairs_improved.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(dataset)} question-SPARQL pairs and saved to question_sparql_pairs_improved.json")