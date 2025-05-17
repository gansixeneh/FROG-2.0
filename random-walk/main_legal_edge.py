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

def separate_camel_case(text):
    """
    Separate camelCase text into words
    """
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

def legal_entity_label(url):
    """
    Generate a human-readable label from a legal entity URL
    """
    parts = str(url).strip("/").split("/")
    transformed_parts = []
    month_mapping = {
        "January": "Januari",
        "February": "Februari",
        "March": "Maret",
        "April": "April",
        "May": "Mei",
        "June": "Juni",
        "July": "Juli",
        "August": "Agustus",
        "September": "September",
        "October": "Oktober",
        "November": "November",
        "December": "Desember",
    }
    for i, part in enumerate(parts):
        if part == "lex2kg":
            transformed_parts = []
            continue
        if part == "uu":
            transformed_parts.append("UU")
        elif part.isdigit() and len(part) <= 2:
            transformed_parts.append(f"no {part}")
        elif part.isdigit() and len(part) == 4 and int(part) >= 1945:
            transformed_parts.append(f"tahun {part}")
        elif part.isdigit() and len(part) == 8:
            try:
                date_obj = datetime.strptime(part, "%Y%m%d")
                formatted_date = date_obj.strftime("%-d %B %Y")
                for eng, indo in month_mapping.items():
                    formatted_date = formatted_date.replace(eng, indo)
                transformed_parts.append(formatted_date)
            except ValueError:
                transformed_parts.append(part)
        elif part.isdigit():
            num = str(int(part))
            transformed_parts.append(num)
        else:
            transformed_parts.append(separate_camel_case(part).lower())
    return " ".join(transformed_parts)

def legal_property_label(x):
    """
    Generate a human-readable label from a legal property
    """
    if "http" in x:
        x = x.split("/")[-1]
    else:
        x = x.split(":")[-1]
    return separate_camel_case(x).lower()

def format_property_label(property_uri):
    """Format a property URI into a readable label in Indonesian"""
    if not isinstance(property_uri, URIRef):
        return str(property_uri)
        
    p_name = str(property_uri).split('/')[-1]
    
    # Map property names to Indonesian labels
    property_mapping = {
        "nomor": "memiliki nomor",
        "teks": "memiliki teks",
        "judul": "memiliki judul",
        "merujuk": "merujuk kepada",
        "mengubah": "mengubah",
        "bagianDari": "merupakan bagian dari",
        "versi": "memiliki versi",
        "tanggal": "memiliki tanggal",
        "segmen": "memiliki segmen",
        "ayat": "memiliki ayat",
        "huruf": "memiliki huruf",
        "pasal": "memiliki pasal",
        "bab": "memiliki bab",
        "bagian": "memiliki bagian",
        "daftarPasal": "memiliki daftar pasal",
        "paragraf": "memiliki paragraf",
        "jenisPeraturan": "memiliki jenis peraturan",
        "disahkanOleh": "disahkan oleh",
        "disahkanPada": "disahkan pada",
        "disahkanDi": "disahkan di",
        "tentang": "tentang",
        "jabatanPengesah": "memiliki jabatan pengesah",
        "menghapus": "menghapus",
        "yurisdiksi": "memiliki yurisdiksi"
    }
    
    return property_mapping.get(p_name, separate_camel_case(p_name).lower())

def generate_dataset_from_ttl_edge_first(ttl_file, num_samples, max_properties=2, gemini_api_key=None):
    """
    Generate a dataset of question-SPARQL pairs from a TTL file using the edge-first approach:
    1. Pick a random relationship type (edge) from the knowledge graph
    2. Find a triple using this relationship 
    3. Expand the context with up to max_properties-1 additional properties
    4. Set up to max_properties-1 entities as variables to guarantee at least one entity remains
    5. Generate natural language questions based on the pattern
    
    Args:
        ttl_file: Path to the TTL file
        num_samples: Number of question-SPARQL pairs to generate
        max_properties: Maximum number of hops in the graph (max 2)
        gemini_api_key: API key for the Gemini API
        
    Returns:
        List of dictionaries with keys 'question', 'englishQuestion', 'sparql'
    """
    # Load the TTL file
    g = Graph()
    g.parse(ttl_file, format='ttl')
    
    # Define namespaces
    ns1 = Namespace("http://example.org/")
    rdfs = Namespace("http://www.w3.org/2000/01/rdf-schema#")
    xsd = Namespace("http://www.w3.org/2001/XMLSchema#")
    RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    lex2kg = Namespace("https://example.org/lex2kg/ontology/")
    
    # Get all unique predicates (edge types) in the graph
    predicates = set()
    for s, p, o in g:
        if isinstance(p, URIRef) and 'lex2kg/ontology' in str(p):
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
        
        # Step a: Determine the actual number of properties to use (1 to max_properties)
        num_properties = random.randint(1, max_properties)
        
        # Step 2: Find all triples with this predicate
        triples_with_predicate = list(g.triples((None, selected_predicate, None)))
        if not triples_with_predicate:
            print(f"  No triples found for predicate {selected_predicate}")
            continue
        
        # Step 3: Pick a random triple with this predicate
        random_triple = random.choice(triples_with_predicate)
        subject, predicate, object_ = random_triple
        
        # Get the predicate name for relationship-specific processing
        pred_name = str(predicate).split('/')[-1]
        print(f"  Selected predicate: {pred_name}")
        
        # Step 4: Build a context pattern starting with this triple
        context_pattern = [random_triple]
        entities_in_context = []
        
        # Add subject and object to entities list if they're URIRefs
        if isinstance(subject, URIRef):
            entities_in_context.append(subject)
        if isinstance(object_, URIRef):
            entities_in_context.append(object_)
        
        # Step 5: Add relationship-specific context, with the max_properties constraint
        related_triples = get_related_triples_for_predicate(g, pred_name, subject, object_)
        
        # FIX: Only add related triples if we're still under max_properties
        available_slots = max_properties - len(context_pattern)
        for triple in related_triples[:available_slots]:  # Limit by available slots
            if triple not in context_pattern:
                context_pattern.append(triple)
                s, p, o = triple
                if isinstance(s, URIRef) and s not in entities_in_context:
                    entities_in_context.append(s)
                if isinstance(o, URIRef) and o not in entities_in_context:
                    entities_in_context.append(o)
        
        # Update counter_p after adding related triples
        counter_p = len(context_pattern)
        
        # FIX: Check if we already hit max properties limit - if so, skip the expansion loop
        if counter_p >= max_properties:
            # We've reached our limit, so make sure we don't exceed it
            context_pattern = context_pattern[:max_properties]
            counter_p = max_properties
        else:
            # Step 6: Continue expansion similarly to entity-first approach until we reach num_properties
            expansion_attempts = 0
            max_expansion_attempts = 50
            
            while counter_p < num_properties and counter_p < max_properties and expansion_attempts < max_expansion_attempts and entities_in_context:
                expansion_attempts += 1
                
                # Pick a random entity from our context
                entity = random.choice(entities_in_context)
                
                # Find properties for this entity
                entity_properties = []
                for s, p, o in g.triples((entity, None, None)):
                    if p not in [rdfs.label, rdfs.domain, rdfs.range, rdfs.subPropertyOf, ns1.also_known_as, RDF.type]:
                        entity_properties.append((s, p, o))
                
                for s, p, o in g.triples((None, None, entity)):
                    if p not in [rdfs.label, rdfs.domain, rdfs.range, rdfs.subPropertyOf, ns1.also_known_as, RDF.type]:
                        entity_properties.append((s, p, o))
                
                if not entity_properties:
                    continue
                
                # Pick a random property
                random_prop_triple = random.choice(entity_properties)
                
                # Skip if this triple is already in our context
                if random_prop_triple in context_pattern:
                    continue
                
                # Add this triple to context if we haven't hit max_properties
                if counter_p < max_properties:
                    context_pattern.append(random_prop_triple)
                    counter_p += 1
                    
                    # Add new entities to context
                    s, p, o = random_prop_triple
                    if isinstance(s, URIRef) and s not in entities_in_context:
                        entities_in_context.append(s)
                    if isinstance(o, URIRef) and o not in entities_in_context:
                        entities_in_context.append(o)
                else:
                    # We've hit our limit, so break out of the loop
                    break
        
        # FIX: Final check to ensure we don't exceed max_properties
        if counter_p > max_properties:
            context_pattern = context_pattern[:max_properties]
            counter_p = max_properties
            
        # If we couldn't find enough properties, skip this sample
        if counter_p < 1:
            print(f"  Skipping sample - couldn't find enough properties")
            continue
        
        # Step 7: Set variables - max number is num_properties-1 to ensure at least one entity remains
        max_variables = num_properties - 1 if num_properties > 1 else 1
        num_variables = random.randint(1, max_variables) if max_variables > 0 else 0
        
        # Get all elements that could be variables
        all_elements = []
        for s, p, o in context_pattern:
            all_elements.append(s)
            all_elements.append(o)
        
        # Remove duplicates and non-entities/literals
        all_elements = [e for e in set(all_elements) if isinstance(e, (URIRef, Literal))]
        
        # Ensure we have enough elements for variables
        if len(all_elements) < 1:
            print(f"  Skipping sample - not enough elements for variables")
            continue
        
        # Score elements for fixed/variable status
        all_elements_with_scores = [(e, score_entity_for_fixed_status(e)) for e in all_elements]
        all_elements_with_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by score descending
        
        # Select elements to make into variables (lowest scores become variables)
        elements_to_replace = [e for e, _ in all_elements_with_scores[-num_variables:]]
        
        # Create mapping from elements to variables with meaningful names
        variable_mapping = {}
        for i, elem in enumerate(elements_to_replace):
            var_name = create_variable_name(elem, i)
            variable_mapping[elem] = var_name
        
        # Replace elements with variables in context pattern
        query_pattern = []
        for s, p, o in context_pattern:
            new_s = variable_mapping.get(s, s)
            new_o = variable_mapping.get(o, o)
            query_pattern.append((new_s, p, new_o))
        
        # Step A: Create a human-readable label mapping for all entities (including those in variable_mapping)
        human_readable_mapping = {}
        for entity in all_elements:
            if isinstance(entity, URIRef) and 'lex2kg' in str(entity):
                human_readable_mapping[entity] = legal_entity_label(entity)
        
        # Step B: Update variable_mapping to include human-readable labels
        for entity, var_name in variable_mapping.items():
            if entity in human_readable_mapping:
                variable_mapping[entity] = (var_name, human_readable_mapping[entity])
            else:
                variable_mapping[entity] = (var_name, str(entity))
        
        # Step 8: Generate question with human-readable labels
        # Create pattern description with human-readable labels
        pattern_description = create_detailed_pattern_description_with_labels(
            query_pattern, human_readable_mapping)
        
        # Extract contents for variables to provide better context for question generation
        variable_contents = extract_variable_contents(g, variable_mapping, context_pattern)
        
        # Generate questions based on relationship type
        questions = generate_questions_for_predicate_with_labels(
            g, pred_name, pattern_description, query_pattern, 
            variable_mapping, human_readable_mapping, variable_contents, gemini_api_key)
        
        # If we couldn't generate questions, try fallback templates
        if not questions or not questions.get("indonesian") or not questions.get("english"):
            questions = generate_specific_fallback_question_with_labels(
                pattern_description, query_pattern, human_readable_mapping, variable_contents)
        
        # Step 9: Generate SPARQL query without prefixes or newlines
        sparql_query = generate_simplified_sparql_query(query_pattern)
        
        # Add to dataset
        dataset.append({
            "question": questions["indonesian"],
            "englishQuestion": questions["english"],
            "sparql": sparql_query,
            "relation_type": pred_name,
            "num_properties": len(query_pattern),  # FIX: Use actual length of query_pattern
            "num_variables": num_variables
        })
        
        # Update usage count for this predicate
        predicate_usage[selected_predicate] += 1
        
        # Increment counter for successful samples
        samples_generated += 1
        print(f"  Successfully generated sample {samples_generated}/{num_samples}")
        print(f"  Indonesian: {questions['indonesian']}")
        print(f"  English: {questions['english']}")
    
    if samples_generated < num_samples:
        print(f"Warning: Could only generate {samples_generated} samples after {max_attempts} attempts")
    
    return dataset

def extract_variable_contents(g, variable_mapping, context_pattern):
    """Extract actual content for variables to provide better context for question generation"""
    variable_contents = {}
    
    for entity, (var_name, label) in variable_mapping.items():
        if isinstance(entity, Literal):
            variable_contents[var_name] = str(entity)
        elif isinstance(entity, URIRef):
            # Look for text content associated with this entity
            for s, p, o in context_pattern:
                if s == entity and 'teks' in str(p) and isinstance(o, Literal):
                    variable_contents[var_name] = str(o)
                    break
                elif o == entity and 'teks' in str(p) and isinstance(s, Literal):
                    variable_contents[var_name] = str(s)
                    break
            
            # If no text found in context pattern, try direct lookup
            if var_name not in variable_contents:
                text_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/teks"), None)))
                if text_triples:
                    variable_contents[var_name] = str(text_triples[0][2])
    
    return variable_contents

def get_related_triples_for_predicate(g, pred_name, subject, object_):
    """Get important related triples based on the predicate type"""
    related_triples = []
    
    if pred_name == "merujuk":
        # For references, add text content of both the referring and referenced entities
        for entity in [subject, object_]:
            text_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/teks"), None)))
            if text_triples:
                related_triples.append(text_triples[0])
                
    elif pred_name == "teks":
        # For text content, try to add information about the entity's number or parent
        nomor_triples = list(g.triples((subject, URIRef("https://example.org/lex2kg/ontology/nomor"), None)))
        if nomor_triples:
            related_triples.append(nomor_triples[0])
            
    elif pred_name == "nomor":
        # For number properties, add text of the numbered entity
        text_triples = list(g.triples((subject, URIRef("https://example.org/lex2kg/ontology/teks"), None)))
        if text_triples:
            related_triples.append(text_triples[0])
            
    elif pred_name == "ayat":
        # For paragraph relationships, add the paragraph's text and number
        for entity in [object_]:  # Focus on the paragraph object
            text_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/teks"), None)))
            if text_triples:
                related_triples.append(text_triples[0])
            nomor_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/nomor"), None)))
            if nomor_triples:
                related_triples.append(nomor_triples[0])
                
    elif pred_name == "huruf":
        # For letter relationships, add the letter's text and number
        for entity in [object_]:  # Focus on the letter object
            text_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/teks"), None)))
            if text_triples:
                related_triples.append(text_triples[0])
            nomor_triples = list(g.triples((entity, URIRef("https://example.org/lex2kg/ontology/nomor"), None)))
            if nomor_triples:
                related_triples.append(nomor_triples[0])
                
    elif pred_name == "pasal":
        # For article relationships, add the article's version information
        versi_triples = list(g.triples((object_, URIRef("https://example.org/lex2kg/ontology/versi"), None)))
        if versi_triples:
            related_triples.append(versi_triples[0])
    
    return related_triples

def create_variable_name(entity, index):
    """Create a meaningful variable name based on entity type"""
    if isinstance(entity, URIRef):
        uri_str = str(entity)
        
        # Default variable name
        var_name = f"?var{index+1}"
        
        # Legal entity patterns for better naming
        patterns = {
            "pasal": "article",
            "ayat": "paragraph",
            "bagian": "section",
            "bab": "chapter",
            "huruf": "letter",
            "teks": "text",
            "uu": "law",
            "versi": "version",
            "nomor": "number"
        }
        
        for pattern, name in patterns.items():
            if pattern in uri_str.lower():
                var_name = f"?{name}{index+1}"
                break
    else:
        # For literals or other values
        var_name = f"?value{index+1}"
    
    return var_name

def create_detailed_pattern_description_with_labels(query_pattern, human_readable_mapping):
    """Create a detailed description of the pattern with human-readable labels"""
    pattern_description = []
    for s, p, o in query_pattern:
        s_label = get_human_readable_label(s, human_readable_mapping)
        p_label = format_property_label(p)
        o_label = get_human_readable_label(o, human_readable_mapping)
        
        pattern_description.append(f"({s_label}, {p_label}, {o_label})")
    
    return "\n".join(pattern_description)

def get_human_readable_label(term, human_readable_mapping):
    """Get a human-readable label for a term"""
    if isinstance(term, str):
        return term  # It's already a variable
    elif isinstance(term, URIRef) and term in human_readable_mapping:
        return human_readable_mapping[term]
    elif isinstance(term, URIRef) and 'lex2kg' in str(term):
        return legal_entity_label(term)
    elif isinstance(term, Literal):
        str_value = str(term)
        if len(str_value) > 50:
            return str_value[:47] + "..."
        return str_value
    else:
        return str(term)

def generate_questions_for_predicate_with_labels(g, pred_name, pattern_description, query_pattern, 
                                              variable_mapping, human_readable_mapping, 
                                              variable_contents, gemini_api_key=None):
    """Generate questions based on the relationship type using human-readable labels"""
    # Extract metadata from pattern for templates
    entity_info = extract_entity_info_from_pattern_with_labels(
        g, query_pattern, variable_mapping, human_readable_mapping)
    
    # Try to generate with Gemini API if available
    if gemini_api_key:
        # First try generating with Gemini
        template_info = f"Relationship type: {pred_name}\nPattern: {pattern_description}\nEntity info: {entity_info}\nVariable contents: {variable_contents}"
        questions = generate_questions_with_gemini_improved(template_info, gemini_api_key, variable_mapping, variable_contents)
        if questions and questions.get("indonesian") and questions.get("english"):
            # Post-process to ensure no URIs are in the questions
            questions["indonesian"] = remove_uris_from_text(questions["indonesian"])
            questions["english"] = remove_uris_from_text(questions["english"])
            
            # Ensure no variable placeholders in questions
            for var_name in variable_mapping:
                if isinstance(var_name, tuple):
                    var_name = var_name[0]
                if var_name in questions["indonesian"] or var_name in questions["english"]:
                    # If variables still appear, try again with templates
                    return generate_questions_from_templates_with_labels(
                        pred_name, entity_info, human_readable_mapping, variable_contents)
            
            return questions
    
    # Fallback to templates if no API or API failed
    return generate_questions_from_templates_with_labels(
        pred_name, entity_info, human_readable_mapping, variable_contents)

def remove_uris_from_text(text):
    """Remove URI patterns from generated text"""
    # Replace URI patterns with human-readable labels
    uri_pattern = r'https://example\.org/lex2kg/[^\s,\.\?]+'
    
    def replace_with_label(match):
        uri = match.group(0)
        return legal_entity_label(uri)
    
    text = re.sub(uri_pattern, replace_with_label, text)
    
    # Remove variable placeholders
    var_pattern = r'\?[a-zA-Z]+\d+'
    text = re.sub(var_pattern, "yang dicari", text)
    
    return text

def extract_entity_info_from_pattern_with_labels(g, query_pattern, variable_mapping, human_readable_mapping):
    """Extract entity information from pattern for template filling using human-readable labels"""
    # Extract key information from URIs
    entity_info = {}
    
    for entity, (var_name, human_label) in variable_mapping.items():
        if isinstance(entity, URIRef):
            uri_str = str(entity)
            
            # Extract law information
            law_match = re.search(r'/uu/(\d{4})/(\d+)', uri_str)
            if law_match:
                entity_info["law_year"] = law_match.group(1)
                entity_info["law_num"] = law_match.group(2)
            
            # Extract article information
            article_match = re.search(r'/pasal/(\d+)', uri_str)
            if article_match:
                entity_info["article_num"] = article_match.group(1).lstrip('0')
            
            # Extract paragraph information
            paragraph_match = re.search(r'/ayat/(\d+)', uri_str)
            if paragraph_match:
                entity_info["paragraph_num"] = paragraph_match.group(1).lstrip('0')
            
            # Extract letter information
            letter_match = re.search(r'/huruf/([a-zA-Z0-9]+)', uri_str)
            if letter_match:
                entity_info["letter_id"] = letter_match.group(1)
            
            # Extract version information
            version_match = re.search(r'/versi/(\d{8})', uri_str)
            if version_match:
                date_str = version_match.group(1)
                try:
                    date_obj = datetime.strptime(date_str, "%Y%m%d")
                    entity_info["version_date"] = date_obj.strftime("%-d %B %Y").replace("May", "Mei").replace("August", "Agustus")
                except ValueError:
                    entity_info["version_date"] = date_str
            
            # Add human-readable label
            entity_info["entity_label"] = human_label
    
    return entity_info

def generate_questions_with_gemini_improved(pattern_text, api_key, variable_mapping, variable_contents):
    """Generate bilingual questions with improved prompting for specificity"""
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Prepare context about variables to help model avoid including variable placeholders directly
    variable_context = "\n\nVARIABLE INFORMATION:\n"
    for var_name, content in variable_contents.items():
        if isinstance(var_name, tuple):
            var_name = var_name[0]
        short_content = content[:100] + "..." if len(content) > 100 else content
        variable_context += f"{var_name} - content: {short_content}\n"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""Generate two versions of a natural language question (one in Bahasa Indonesia and one in English) based on the following information about Indonesian legal documents:
{pattern_text}
{variable_context}

CRITICAL REQUIREMENTS FOR BOTH LANGUAGES:

1. BE EXTREMELY SPECIFIC - Your questions MUST include ALL specific identifiers found in the pattern
2. If you see specific entities like "UU no 39 tahun 2004 pasal 97", your question MUST mention these exact identifiers
3. DO NOT generate generic questions about legal systems, numbering, or structures in general
4. Each question should be asking for specific information about the specific legal entities mentioned
5. NEVER include raw URLs or URIs in the questions - only use the human-readable labels provided
6. DO NOT include phrases like "which has the URI" or references to URLs in the questions
7. NEVER include variable placeholders like "?value1" or "?article1" in the questions - replace these with descriptive phrases like "apa" or "yang mana" for Indonesian, or "what", "which" for English
8. When asking for content represented by a variable, use natural phrasing like "apa isi dari" or "what is the content of"

Examples of GOOD questions:
- "Apa nomor dari Pasal 97 dalam UU no 39 tahun 2004?"
- "What is the number of Article 97 in Law Number 39 of 2004?"
- "Berapa nomor yang dimiliki oleh Pasal 4 Undang-Undang Nomor 14 Tahun 2015?"
- "What number does Article 4 of Law Number 14 of 2015 have?"

Examples of BAD questions to AVOID:
- "Bagaimana sistem penomoran untuk pasal dan bagian dalam kerangka hukum Indonesia?"
- "What numbering systems are used for articles and sections?"
- "Apa isi pasal pada https://example.org/lex2kg/uu/2009/22/pasal/0115?"
- "What is the content of the article with URI https://example.org/lex2kg/uu/2009/22/pasal/0115?"
- "Ayat mana yang dirujuk oleh Ayat 3 Pasal 157 yang memiliki teks ?value1?"
- "What is the text ?value1 of the article referenced by paragraph 3?"

Format your response exactly as follows:
Indonesian: [Question in Bahasa Indonesia]
English: [Question in English]

Remember: BE SPECIFIC! Use the human-readable labels for all entities in the pattern and phrase questions naturally without variable placeholders."""
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
                if isinstance(var_name, tuple):
                    var_name = var_name[0]
                indonesian_question = indonesian_question.replace(var_name, "yang dicari")
        
        if english_question:
            for var_name in variable_mapping:
                if isinstance(var_name, tuple):
                    var_name = var_name[0]
                english_question = english_question.replace(var_name, "the requested information")
        
        return {
            "indonesian": indonesian_question,
            "english": english_question
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

def generate_questions_from_templates_with_labels(pred_name, entity_info, human_readable_mapping, variable_contents):
    """Generate questions using templates based on the predicate type with human-readable labels"""
    # Define templates by predicate type
    templates = {
        "merujuk": [
            {"id": "Ayat manakah yang dirujuk oleh ayat {paragraph_num} pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "Which paragraph is referenced by paragraph {paragraph_num} of article {article_num} of Law No. {law_num} of {law_year}?"},
            {"id": "Dalam ayat {paragraph_num} pasal {article_num} UU no {law_num} tahun {law_year}, ayat berapa yang dirujuk?",
             "en": "In paragraph {paragraph_num} of article {article_num} of Law No. {law_num} of {law_year}, which paragraph is referenced?"}
        ],
        "teks": [
            {"id": "Apa isi dari {entity_type} {entity_id} pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What is the content of {entity_type} {entity_id} of article {article_num} of Law No. {law_num} of {law_year}?"},
            {"id": "Bagaimana bunyi {entity_type} {entity_id} pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What does {entity_type} {entity_id} of article {article_num} of Law No. {law_num} of {law_year} state?"}
        ],
        "nomor": [
            {"id": "Apa nomor dari {entity_type} dalam pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What is the number of the {entity_type} in article {article_num} of Law No. {law_num} of {law_year}?"},
            {"id": "Berapa nomor {entity_type} dalam pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What is the number of the {entity_type} in article {article_num} of Law No. {law_num} of {law_year}?"}
        ],
        "ayat": [
            {"id": "Ayat apa saja yang terdapat dalam pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What paragraphs are contained in article {article_num} of Law No. {law_num} of {law_year}?"},
            {"id": "Berapa jumlah ayat dalam pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "How many paragraphs are there in article {article_num} of Law No. {law_num} of {law_year}?"}
        ],
        "huruf": [
            {"id": "Huruf apa saja yang terdapat dalam ayat {paragraph_num} pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "What letters are contained in paragraph {paragraph_num} of article {article_num} of Law No. {law_num} of {law_year}?"},
            {"id": "Berapa jumlah huruf dalam ayat {paragraph_num} pasal {article_num} UU no {law_num} tahun {law_year}?",
             "en": "How many letters are there in paragraph {paragraph_num} of article {article_num} of Law No. {law_num} of {law_year}?"}
        ],
        "jabatanPengesah": [
            {"id": "Siapa jabatan pengesah dari UU no {law_num} tahun {law_year}?",
             "en": "What is the approving official position of Law No. {law_num} of {law_year}?"}
        ],
        "disahkanPada": [
            {"id": "Kapan UU no {law_num} tahun {law_year} disahkan?",
             "en": "When was Law No. {law_num} of {law_year} ratified?"}
        ],
        "bab": [
            {"id": "Bab apa yang dimiliki oleh UU no {law_num} tahun {law_year}?",
             "en": "What chapter does Law No. {law_num} of {law_year} have?"}
        ],
        "bagian": [
            {"id": "Bagian apa yang dimiliki oleh Bab {chapter_num} UU no {law_num} tahun {law_year}?",
             "en": "What section is contained in Chapter {chapter_num} of Law No. {law_num} of {law_year}?"}
        ],
        "paragraf": [
            {"id": "Paragraf apa yang dimiliki oleh Bagian {section_num} Bab {chapter_num} UU no {law_num} tahun {law_year}?",
             "en": "What paragraph is contained in Section {section_num} of Chapter {chapter_num} of Law No. {law_num} of {law_year}?"}
        ],
        "judul": [
            {"id": "Apa judul dari {entity_label}?",
             "en": "What is the title of {entity_label}?"}
        ],
        "yurisdiksi": [
            {"id": "Apa yurisdiksi yang terkait dengan UU no {law_num} tahun {law_year}?",
             "en": "What is the jurisdiction associated with Law No. {law_num} of {law_year}?"}
        ],
        "tentang": [
            {"id": "UU no {law_num} tahun {law_year} tentang apa?",
             "en": "What is Law No. {law_num} of {law_year} about?"}
        ],
        "tanggal": [
            {"id": "Tanggal berapa yang dimiliki oleh {entity_label}?",
             "en": "What date does {entity_label} have?"}
        ],
        "mengubah": [
            {"id": "Peraturan apa yang diubah oleh {entity_label}?",
             "en": "Which regulation is amended by {entity_label}?"}
        ],
        "menghapus": [
            {"id": "Peraturan apa yang dihapus oleh {entity_label}?",
             "en": "Which regulation is repealed by {entity_label}?"}
        ]
    }
    
    # Additional templates for specific variable content conditions
    if variable_contents:
        for var_name, content in variable_contents.items():
            if isinstance(var_name, tuple):
                var_name = var_name[0]
            
            # If we have text content for a variable, add templates that include reference to it
            if content and len(content) > 10:
                # Truncate content for readability in templates
                short_content = content[:50] + "..." if len(content) > 50 else content
                
                if "merujuk" in templates:
                    templates["merujuk"].extend([
                        {"id": "Ayat manakah yang dirujuk oleh ayat {paragraph_num} pasal {article_num} UU no {law_num} tahun {law_year}, yang ayat tersebut memiliki teks yang dicari?",
                         "en": "Which paragraph is referenced by paragraph {paragraph_num} of article {article_num} of Law No. {law_num} of {law_year}, where the referenced paragraph has the requested text?"},
                    ])
                
                if "teks" in templates:
                    templates["teks"].extend([
                        {"id": "Apa isi dari {entity_type} {entity_id} pasal {article_num} UU no {law_num} tahun {law_year}, yang memiliki nomor yang dicari?",
                         "en": "What is the content of {entity_type} {entity_id} of article {article_num} of Law No. {law_num} of {law_year}, which has the requested number?"}
                    ])
    
    # Default templates if the predicate doesn't have specific templates
    default_templates = [
        {"id": "Apa informasi tentang {entity_label}?",
         "en": "What information exists about {entity_label}?"},
        {"id": "Berikan informasi mengenai {entity_label}.",
         "en": "Provide information about {entity_label}."}
    ]
    
    # Set entity type for templates
    if "paragraph_num" in entity_info:
        entity_info["entity_type"] = "ayat"
        entity_info["entity_id"] = entity_info["paragraph_num"]
    elif "letter_id" in entity_info:
        entity_info["entity_type"] = "huruf"
        entity_info["entity_id"] = entity_info["letter_id"]
    elif "article_num" in entity_info:
        entity_info["entity_type"] = "pasal"
        entity_info["entity_id"] = entity_info["article_num"]
    elif "chapter_num" in entity_info:
        entity_info["entity_type"] = "bab"
        entity_info["entity_id"] = entity_info["chapter_num"]
    else:
        entity_info["entity_type"] = "bagian"
        entity_info["entity_id"] = ""
    
    # Select and fill template
    template_list = templates.get(pred_name, default_templates)
    template = random.choice(template_list)
    
    try:
        id_question = template["id"].format(**entity_info)
        en_question = template["en"].format(**entity_info)
        
        return {
            "indonesian": id_question,
            "english": en_question
        }
    except KeyError as e:
        # If template has placeholders we can't fill, use fallback
        return {
            "indonesian": f"Apa informasi tentang UU no {entity_info.get('law_num', '')} tahun {entity_info.get('law_year', '')}?",
            "english": f"What information exists about Law No. {entity_info.get('law_num', '')} of {entity_info.get('law_year', '')}?"
        }

def generate_specific_fallback_question_with_labels(pattern_description, query_pattern, human_readable_mapping, variable_contents):
    """Generate specific fallback questions based on actual entities in the pattern with human-readable labels"""
    # Extract specific entities from pattern text
    law_matches = re.findall(r'/uu/(\d{4})/(\d+)', pattern_description)
    article_matches = re.findall(r'/pasal/(\d+)', pattern_description)
    version_matches = re.findall(r'/versi/(\d{8})', pattern_description)
    paragraph_matches = re.findall(r'/ayat/(\d+)', pattern_description)
    letter_matches = re.findall(r'/huruf/([a-zA-Z0-9]+)', pattern_description)
    
    # Determine what's being asked for based on the query pattern
    asking_for_number = any('nomor' in str(p) for _, p, _ in query_pattern)
    asking_for_text = any('teks' in str(p) for _, p, _ in query_pattern)
    asking_for_title = any('judul' in str(p) for _, p, _ in query_pattern)
    asking_for_reference = any('merujuk' in str(p) for _, p, _ in query_pattern)
    asking_for_change = any('mengubah' in str(p) for _, p, _ in query_pattern)
    asking_for_delete = any('menghapus' in str(p) for _, p, _ in query_pattern)
    
    # Extract text content from variables if available
    text_content = None
    for var_name, content in variable_contents.items():
        if content and len(content) > 10:
            text_content = content[:80] + "..." if len(content) > 80 else content
            break
    
    # Build specific questions
    indonesian_question = ""
    english_question = ""
    
    if law_matches and article_matches and paragraph_matches:
        year, number = law_matches[0]
        article_num = int(article_matches[0])
        paragraph_num = int(paragraph_matches[0])
        
        if version_matches:
            version_date = datetime.strptime(version_matches[0], "%Y%m%d").strftime("%-d %B %Y")
            # Replace English months with Indonesian
            month_mapping = {
                "January": "Januari", "February": "Februari", "March": "Maret",
                "April": "April", "May": "Mei", "June": "Juni",
                "July": "Juli", "August": "Agustus", "September": "September",
                "October": "Oktober", "November": "November", "December": "Desember"
            }
            for eng, indo in month_mapping.items():
                version_date = version_date.replace(eng, indo)
            
            if asking_for_number:
                indonesian_question = f"Apa nomor dari Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What is the number of Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
            elif asking_for_text:
                indonesian_question = f"Apa isi dari Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What is the content of Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
            elif asking_for_reference:
                if text_content:
                    indonesian_question = f"Ayat mana yang dirujuk oleh Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}, yang memiliki teks \"{text_content}\"?"
                    english_question = f"Which paragraph is referenced by Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, version {version_date}, that has the text \"{text_content}\"?"
                else:
                    indonesian_question = f"Ayat mana yang dirujuk oleh Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                    english_question = f"Which paragraph is referenced by Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
            else:
                indonesian_question = f"Apa informasi tentang Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What information exists about Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
        else:
            if asking_for_number:
                indonesian_question = f"Apa nomor dari Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What is the number of Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}?"
            elif asking_for_text:
                indonesian_question = f"Apa isi dari Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What is the content of Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}?"
            elif asking_for_reference:
                if text_content:
                    indonesian_question = f"Ayat mana yang dirujuk oleh Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year}, yang mana ayat tersebut memiliki teks \"{text_content}\"?"
                    english_question = f"Which paragraph is referenced by Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}, where that paragraph has the text \"{text_content}\"?"
                else:
                    indonesian_question = f"Ayat mana yang dirujuk oleh Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year}?"
                    english_question = f"Which paragraph is referenced by Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}?"
            else:
                indonesian_question = f"Apa informasi tentang Ayat {paragraph_num} Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What information exists about Paragraph {paragraph_num} of Article {article_num} in Law Number {number} of {year}?"
    
    elif law_matches and article_matches:
        year, number = law_matches[0]
        article_num = int(article_matches[0])
        
        if version_matches:
            version_date = datetime.strptime(version_matches[0], "%Y%m%d").strftime("%-d %B %Y")
            for eng, indo in month_mapping.items():
                version_date = version_date.replace(eng, indo)
                
            if asking_for_number:
                indonesian_question = f"Apa nomor dari Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What is the number of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
            elif asking_for_text:
                indonesian_question = f"Apa isi dari Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What is the content of Article {article_num} in Law Number {number} of {year}, version {version_date}?"
            else:
                indonesian_question = f"Apa informasi tentang Pasal {article_num} dalam UU no {number} tahun {year} versi {version_date}?"
                english_question = f"What information exists about Article {article_num} in Law Number {number} of {year}, version {version_date}?"
        else:
            if asking_for_number:
                indonesian_question = f"Apa nomor dari Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What is the number of Article {article_num} in Law Number {number} of {year}?"
            elif asking_for_text:
                indonesian_question = f"Apa isi dari Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What is the content of Article {article_num} in Law Number {number} of {year}?"
            elif asking_for_change:
                indonesian_question = f"Peraturan apa yang diubah oleh Pasal {article_num} UU no {number} tahun {year}?"
                english_question = f"Which regulation is amended by Article {article_num} of Law Number {number} of {year}?"
            elif asking_for_delete:
                indonesian_question = f"Peraturan apa yang dihapus oleh Pasal {article_num} UU no {number} tahun {year}?"
                english_question = f"Which regulation is repealed by Article {article_num} of Law Number {number} of {year}?"
            else:
                indonesian_question = f"Apa informasi tentang Pasal {article_num} dalam UU no {number} tahun {year}?"
                english_question = f"What information exists about Article {article_num} in Law Number {number} of {year}?"
    
    elif law_matches:
        year, number = law_matches[0]
        if asking_for_title:
            indonesian_question = f"Apa judul dari UU no {number} tahun {year}?"
            english_question = f"What is the title of Law Number {number} of {year}?"
        else:
            indonesian_question = f"Apa informasi tentang UU no {number} tahun {year}?"
            english_question = f"What information exists about Law Number {number} of {year}?"
    
    # If we still don't have questions, create generic ones as last resort
    if not indonesian_question:
        # Find any human-readable entity to use in the generic question
        human_readable_entity = None
        for entity, label in human_readable_mapping.items():
            if isinstance(entity, URIRef) and 'lex2kg' in str(entity):
                human_readable_entity = label
                break
                
        if human_readable_entity:
            return {
                "indonesian": f"Apa informasi tentang {human_readable_entity}?",
                "english": f"What information is available about {human_readable_entity}?"
            }
        else:
            return {
                "indonesian": "Apa informasi yang tersedia dalam dokumen hukum ini?",
                "english": "What information is available in this legal document?"
            }
    
    return {
        "indonesian": indonesian_question,
        "english": english_question
    }

def score_entity_for_fixed_status(entity):
    """
    Score an entity to determine if it should be kept fixed (not turned into a variable).
    Higher scores indicate entities that should remain fixed.
    
    Args:
        entity: The entity to score
        
    Returns:
        int: A score where higher values mean the entity should more likely remain fixed
    """
    score = 0
    
    if isinstance(entity, URIRef):
        entity_str = str(entity)
        
        # Law identifiers are valuable to keep fixed
        if "/uu/" in entity_str:
            score += 10
            
            # Extract law number and year if possible
            law_match = re.search(r'/uu/(\d{4})/(\d+)', entity_str)
            if law_match:
                score += 5  # Specific laws are valuable fixed points
            
            # Article identifiers
            if "/pasal/" in entity_str:
                score += 5
                # Extract article number
                article_match = re.search(r'/pasal/(\d+)', entity_str)
                if article_match:
                    score += 3  # Specific article numbers are valuable
            
            # Paragraph identifiers
            if "/ayat/" in entity_str:
                score += 4
                # Extract paragraph number
                paragraph_match = re.search(r'/ayat/(\d+)', entity_str)
                if paragraph_match:
                    score += 2
            
            # Letter identifiers
            if "/huruf/" in entity_str:
                score += 3
        
        # Properties are less important to keep fixed
        if "ontology" in entity_str:
            score -= 5
    
    elif isinstance(entity, Literal):
        # Text content is often valuable to keep fixed if it's substantial
        if len(str(entity)) > 20:
            score += 8
        # Numbers might be more interesting as variables
        elif re.match(r'^\d+$', str(entity)):
            score -= 2
    
    return score

def generate_simplified_sparql_query(query_pattern):
    """
    Generate a simplified SPARQL query without prefixes or newlines.
    
    Args:
        query_pattern: List of (subject, predicate, object) triples
        
    Returns:
        A SPARQL query string without prefixes or newlines
    """
    # Get variables used in the pattern
    variables = set()
    for s, p, o in query_pattern:
        if isinstance(s, str) and s.startswith('?'):
            variables.add(s)
        if isinstance(o, str) and o.startswith('?'):
            variables.add(o)
    
    # Generate SELECT clause
    select_clause = "SELECT " + " ".join(sorted(variables)) + " WHERE {"
    
    # Generate WHERE clause
    where_clauses = []
    for s, p, o in query_pattern:
        s_str = format_term_for_simplified_sparql(s)
        p_str = format_term_for_simplified_sparql(p)
        o_str = format_term_for_simplified_sparql(o)
        
        where_clauses.append(f"  {s_str} {p_str} {o_str} .")
    
    # Combine all parts
    query = select_clause + " " + " ".join(where_clauses) + " }"
    
    return query

def format_term_for_simplified_sparql(term):
    """
    Format a term (URIRef, Literal, or variable) for inclusion in a SPARQL query without using prefixes.
    
    Args:
        term: The term to format
        
    Returns:
        A string representation of the term for SPARQL
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
    
    Args:
        dataset: List of dictionaries with keys 'question', 'sparql', 'num_properties', 'num_variables'
    
    Returns:
        A dictionary with various statistics
    """
    property_counts = [item['num_properties'] for item in dataset]
    variable_counts = [item['num_variables'] for item in dataset]
    relation_types = [item.get('relation_type', 'unknown') for item in dataset]
    
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
        },
        "relation_type_distribution": {
            type_name: relation_types.count(type_name) for type_name in set(relation_types)
        }
    }
    
    return stats

if __name__ == "__main__":
    # Replace with your actual Gemini API key
    load_dotenv()
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    # Number of samples to generate
    num_samples = 15
    
    # Maximum number of properties per pattern (max 2 hops)
    max_properties = 2
    
    # Generate the dataset using edge-first approach with human-readable labels
    dataset = generate_dataset_from_ttl_edge_first(
        'modified_data-lex2kg.ttl', 
        num_samples, 
        max_properties,
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
    
    # Save the dataset to a JSON file
    with open('question_sparql_pairs_legal_bilingual_edge_first.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(dataset)} question-SPARQL pairs and saved to question_sparql_pairs_legal_bilingual_edge_first.json")