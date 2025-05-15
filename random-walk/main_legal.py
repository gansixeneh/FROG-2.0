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
    """Separate camelCase text into words"""
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

def legal_entity_label(url):
    """Generate a human-readable label from a legal entity URL"""
    parts = str(url).strip("/").split('/')
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
        "tentang": "tentang"
    }
    
    return property_mapping.get(p_name, separate_camel_case(p_name).lower())

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
    
    # Define common legal entity patterns for better variable naming
    legal_entity_patterns = {
        "pasal": "article",
        "ayat": "paragraph",
        "bagian": "section",
        "bab": "chapter",
        "huruf": "letter",
        "teks": "text",
        "uu": "law",
        "versi": "version",
        "daftar": "list",
        "nomor": "number",
        "judul": "title",
        "merujuk": "reference",
        "segmen": "segment"
    }
    
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
        
        # NEW: Constrain number of variables based on properties
        original_num_vars = num_variables
        if num_properties > 1:  # For patterns with multiple properties
            # Constrain variables to be at most (properties - 1)
            num_vars_to_use = min(min(num_variables, len(all_elements)), num_properties - 1)
        else:  # num_properties == 1
            # For one property, we still need one entity fixed and one variable
            num_vars_to_use = min(min(num_variables, len(all_elements)), 1)
        
        if num_vars_to_use < original_num_vars:
            print(f"  Reduced variables from {original_num_vars} to {num_vars_to_use} to maintain question specificity")
        
        if num_vars_to_use < 1:
            print(f"  Skipping sample attempt - cannot satisfy variable constraints")
            continue
        
        # NEW: Score elements to prioritize which to keep fixed
        all_elements_with_scores = [(e, score_entity_for_fixed_status(e)) for e in all_elements]
        all_elements_with_scores.sort(key=lambda x: x[1], reverse=True)  # Sort by score descending
        
        # Select the lowest-scoring elements to replace with variables
        elements_to_replace = [e for e, _ in all_elements_with_scores[-num_vars_to_use:]]
        
        # Create a mapping from elements to variables with meaningful names
        variable_mapping = {}
        for i, elem in enumerate(elements_to_replace):
            # Try to determine what kind of element this is and use an appropriate name
            if isinstance(elem, URIRef):
                # Check for common patterns in the URI
                uri_str = str(elem)
                
                # Default variable name
                var_name = f"?var{i+1}"
                
                # Try to identify the element type from URI
                for pattern, name in legal_entity_patterns.items():
                    if pattern in uri_str.lower():
                        var_name = f"?{name}{i+1}"
                        break
            else:
                # For literals or other values
                var_name = f"?value{i+1}"
            
            variable_mapping[elem] = var_name
        
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
            p_label = format_property_label(p)
            o_label = get_label_or_format(o, label_mapping)
            
            pattern_description.append(f"({s_label}, {p_label}, {o_label})")
        
        pattern_text = "\n".join(pattern_description)
        
        # Generate bilingual questions using Gemini API with retries
        max_question_attempts = 3
        questions = None
        for q_attempt in range(max_question_attempts):
            temp_questions = generate_questions_with_gemini(pattern_text, gemini_api_key)
            
            # Check if the questions contain variable references or are too vague
            id_question = temp_questions.get("indonesian", "")
            en_question = temp_questions.get("english", "")
            
            # Validate both questions
            id_is_valid = not is_too_vague(id_question, "indonesian") and not re.search(r'\?[a-zA-Z]*\d+', id_question)
            en_is_valid = not is_too_vague(en_question, "english") and not re.search(r'\?[a-zA-Z]*\d+', en_question)
            
            if id_is_valid and en_is_valid:
                questions = temp_questions
                break
            
            # If last attempt, use the validation function to fix it
            if q_attempt == max_question_attempts - 1:
                id_question = validate_and_fix_question(id_question, pattern_text, "indonesian")
                en_question = validate_and_fix_question(en_question, pattern_text, "english")
                questions = {"indonesian": id_question, "english": en_question}
            
            # Add a small delay to avoid rate limits
            time.sleep(1)
        
        # Generate SPARQL query
        sparql_query = generate_sparql_query(query_pattern, ns1, rdfs, xsd)
        
        dataset.append({
            "question": questions["indonesian"],
            "englishQuestion": questions["english"],
            "sparql": sparql_query,
            "num_properties": counter_p,
            "num_variables": num_vars_to_use
        })
        
        # Increment the counter for successful samples
        samples_generated += 1
        print(f"  Successfully generated sample {samples_generated}/{num_samples}")
        print(f"  Indonesian: {questions['indonesian']}")
        print(f"  English: {questions['english']}")
    
    if samples_generated < num_samples:
        print(f"Warning: Could only generate {samples_generated} samples after {max_attempts} attempts")
    
    return dataset

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

def is_too_vague(question, language="english"):
    """
    Check if a question is too vague to be useful
    
    Args:
        question (str): The question to check
        language (str): The language of the question ("english" or "indonesian")
        
    Returns:
        bool: True if the question is too vague, False otherwise
    """
    # Define vague patterns for both languages
    vague_patterns = {
        "english": [
            r"\bthis article\b",
            r"\bthis section\b", 
            r"\bthis law\b", 
            r"\bthis paragraph\b",
            r"\bthis letter\b",
            r"\bthis chapter\b"
        ],
        "indonesian": [
            r"\bpasal ini\b",
            r"\bbagian ini\b",
            r"\bundang-undang ini\b",
            r"\bayat ini\b",
            r"\bhuruf ini\b",
            r"\bbab ini\b",
            r"\bUU ini\b"
        ]
    }
    
    # Use the appropriate patterns for the language
    language_patterns = vague_patterns.get(language.lower(), vague_patterns["english"])
    
    # Check for vague patterns
    for pattern in language_patterns:
        if re.search(pattern, question.lower()):
            # Check if there's specific qualification before the vague term
            qualified = False
            if language.lower() == "english":
                qualified = re.search(r'(Article|Law|Section|Chapter) (\d+|[a-zA-Z])[^\?]+'+pattern, question.lower())
            else:  # indonesian
                qualified = re.search(r'(Pasal|UU|Bagian|Bab) (\d+|[a-zA-Z])[^\?]+'+pattern, question.lower())
                
            if not qualified:
                return True
    
    # Check for questions that are too short or generic
    if len(question.split()) < 6:
        return True
        
    return False

def generate_generic_legal_question(pattern_text, language="english"):
    """
    Generate a generic but meaningful legal question for patterns without specific identifiers
    
    Args:
        pattern_text (str): The pattern text
        language (str): The language to generate the question in ("english" or "indonesian")
        
    Returns:
        str: A generic legal question
    """
    if language.lower() == "indonesian":
        if "nomor" in pattern_text.lower():
            return "Bagaimana sistem penomoran untuk pasal dan bagian dalam kerangka hukum Indonesia?"
        
        if "teks" in pattern_text.lower():
            return "Apa saja jenis konten teks yang terdapat dalam berbagai komponen legislasi Indonesia?"
        
        if "merujuk" in pattern_text.lower():
            return "Bagaimana ketentuan-ketentuan dalam hukum Indonesia saling merujuk atau berhubungan satu sama lain?"
        
        if "versi" in pattern_text.lower():
            return "Bagaimana struktur dan identifikasi versi-versi artikel hukum dalam undang-undang Indonesia?"
        
        if "huruf" in pattern_text.lower():
            return "Bagaimana subbagian berupa huruf digunakan untuk mengorganisir ketentuan hukum dalam legislasi Indonesia?"
        
        # Default generic question if no specific pattern is identified
        return "Hubungan struktural seperti apa yang ada antara komponen-komponen berbeda dalam sistem hukum Indonesia?"
    
    else:  # English
        if "nomor" in pattern_text.lower():
            return "What numbering systems are used for articles and sections in the Indonesian legal framework?"
        
        if "teks" in pattern_text.lower():
            return "What types of text content exist within different components of Indonesian legislation?"
        
        if "merujuk" in pattern_text.lower():
            return "How do different provisions in Indonesian law reference or relate to one another?"
        
        if "versi" in pattern_text.lower():
            return "How are different versions of legal articles structured and identified in Indonesian law?"
        
        if "huruf" in pattern_text.lower():
            return "How are lettered subsections used to organize legal provisions in Indonesian legislation?"
        
        # Default generic question if no specific pattern is identified
        return "What structural relationships exist between different components in the Indonesian legal system?"

def validate_and_fix_question(question, pattern_text, language="english"):
    """
    Validate if the question contains variable references or is too vague, and fix it
    
    Args:
        question (str): The generated question
        pattern_text (str): The pattern description used to generate the question
        language (str): The language of the question ("english" or "indonesian")
        
    Returns:
        str: Improved question without variable references and with better specificity
    """
    # Check if question contains variable references
    if re.search(r'\?[a-zA-Z]*\d+', question):
        # Replace specific common variable patterns based on language
        if language.lower() == "indonesian":
            question = re.sub(r'\?var\d+', "entitas ini", question)
            question = re.sub(r'\?article\d+', "pasal ini", question)
            question = re.sub(r'\?paragraph\d+', "ayat ini", question)
            question = re.sub(r'\?section\d+', "bagian ini", question)
            question = re.sub(r'\?chapter\d+', "bab ini", question)
            question = re.sub(r'\?text\d+', "teks ini", question)
            question = re.sub(r'\?law\d+', "undang-undang ini", question)
            question = re.sub(r'\?version\d+', "versi ini", question)
            question = re.sub(r'\?title\d+', "judul ini", question)
            question = re.sub(r'\?number\d+', "nomor ini", question)
            question = re.sub(r'\?segment\d+', "segmen ini", question)
            question = re.sub(r'\?letter\d+', "huruf ini", question)
        else:  # English
            question = re.sub(r'\?var\d+', "this entity", question)
            question = re.sub(r'\?article\d+', "this article", question)
            question = re.sub(r'\?paragraph\d+', "this paragraph", question)
            question = re.sub(r'\?section\d+', "this section", question)
            question = re.sub(r'\?chapter\d+', "this chapter", question)
            question = re.sub(r'\?text\d+', "this text", question)
            question = re.sub(r'\?law\d+', "this law", question)
            question = re.sub(r'\?version\d+', "this version", question)
            question = re.sub(r'\?title\d+', "this title", question)
            question = re.sub(r'\?number\d+', "this number", question)
            question = re.sub(r'\?segment\d+', "this segment", question)
            question = re.sub(r'\?letter\d+', "this letter", question)
        
        # Replace any remaining variables based on language
        if language.lower() == "indonesian":
            question = re.sub(r'diidentifikasi oleh \?[a-zA-Z]*\d+', "", question)
            question = re.sub(r'dengan \?[a-zA-Z]*\d+', "", question)
            question = re.sub(r'\?[a-zA-Z]*\d+', "entitas mana", question)
        else:  # English
            question = re.sub(r'identified by \?[a-zA-Z]*\d+', "", question)
            question = re.sub(r'with \?[a-zA-Z]*\d+', "", question)
            question = re.sub(r'\?[a-zA-Z]*\d+', "which items", question)
    
    # Check if question is too vague after variable replacements
    if is_too_vague(question, language):
        # Extract any specific laws or articles from the pattern
        law_match = re.search(r'/uu/(\d{4})/(\d+)', pattern_text)
        article_match = re.search(r'/pasal/(\d+)', pattern_text)
        
        if law_match and article_match:
            year, number = law_match.groups()
            article_num = article_match.group(1)
            
            # Replace vague references with specific ones based on language
            if language.lower() == "indonesian":
                question = re.sub(r'\bpasal ini\b', f"Pasal {int(article_num)} UU no {number} tahun {year}", question)
                question = re.sub(r'\bundang-undang ini\b', f"UU no {number} tahun {year}", question)
                question = re.sub(r'\bUU ini\b', f"UU no {number} tahun {year}", question)
            else:  # English
                question = re.sub(r'\bthis article\b', f"Article {int(article_num)} of Law Number {number} of {year}", question)
                question = re.sub(r'\bthis law\b', f"Law Number {number} of {year}", question)
        else:
            # If we can't find specific references, use a generic but meaningful question
            question = generate_generic_legal_question(pattern_text, language)
    
    # Fix double spaces
    question = re.sub(r' +', ' ', question).strip()
    
    # Fix question that might end without question mark
    if not question.endswith('?'):
        question = question + '?'
    
    # If the question becomes too generic or short, provide a better one
    if len(question.split()) < 5:
        return generate_generic_legal_question(pattern_text, language)
    
    return question

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
        # Use legal_entity_label for legal URIs
        if "/lex2kg/" in str(term):
            return legal_entity_label(term)
        else:
            # For non-legal URIs, extract the name from the URI
            return term.split('/')[-1].replace('_', ' ')
    elif isinstance(term, Literal):
        # If the literal is too long, truncate it for readability
        str_value = str(term)
        if len(str_value) > 50:
            return str_value[:47] + "..."
        return str_value
    else:
        return str(term)

def generate_questions_with_gemini(pattern_text, api_key):
    """
    Generate a bilingual (Bahasa Indonesia and English) questions for the given pattern using the Gemini API.
    
    Args:
        pattern_text: A string describing the pattern
        api_key: The Gemini API key
        
    Returns:
        dict: Dictionary with "indonesian" and "english" questions
    """
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"""Generate two versions of a natural language question (one in Bahasa Indonesia and one in English) based on the following information about Indonesian legal documents:
{pattern_text}

Your questions should be based on the Indonesian legal system where:
- "UU" means Law/Undang-Undang
- "pasal" means article
- "ayat" means paragraph
- "huruf" means letter/item
- "bab" means chapter
- "bagian" means section
- "versi" means version, typically with a date
- "tahun" means year

Format your response exactly as follows:
Indonesian: [Question in Bahasa Indonesia]
English: [Question in English]

IMPORTANT REQUIREMENTS FOR BOTH LANGUAGES:
1. BE SPECIFIC - Your questions MUST specify exactly which law, article, section, or paragraph they're referring to
2. When numbers appear in the pattern (like "UU tahun 2014 no 37"), include these exact numbers in your questions
3. NEVER use vague terms like "this article" or "pasal ini" without specifying which one
4. Use proper Indonesian legal terminology in the Bahasa Indonesia version
5. Use formal language appropriate for legal queries
6. Include all relevant details from the pattern (law numbers, article numbers, dates, etc.)

EXAMPLES OF EXCELLENT QUESTIONS:
Indonesian: Apa judul dari UU tahun 2014 no 37 bab 7?
English: What is the title of Chapter 7 of Law Number 37 of 2014?

Indonesian: Siapa yang mengesahkan UU tahun 1999 no 42?
English: Who enacted Law Number 42 of 1999?

Indonesian: Apa isi dari UU tahun 2010 no 13 pasal 31 versi 24 November 2010 ayat 1?
English: What is the content of Paragraph 1 of Article 31, version November 24, 2010, of Law Number 13 of 2010?

EXAMPLES OF POOR QUESTIONS TO AVOID:
- "Apa isi dari pasal ini?" (too vague - which article?)
- "What articles reference this law?" (needs specific law reference)
- "Nomor berapa yang ditetapkan untuk UU ini?" (needs specific law)

Only return the question without any explanation or preamble."""
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
        
        # Add fallback for missing questions
        if not indonesian_question:
            indonesian_question = generate_generic_legal_question(pattern_text, "indonesian")
        
        if not english_question:
            english_question = generate_generic_legal_question(pattern_text, "english")
        
        return {
            "indonesian": indonesian_question,
            "english": english_question
        }
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        # Return fallback questions
        return {
            "indonesian": generate_generic_legal_question(pattern_text, "indonesian"),
            "english": generate_generic_legal_question(pattern_text, "english")
        }

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
        'modified_data-lex2kg.ttl', 
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
    with open('question_sparql_pairs_legal_bilingual.json', 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\nGenerated {len(dataset)} question-SPARQL pairs and saved to question_sparql_pairs_legal_bilingual.json")