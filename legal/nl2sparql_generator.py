"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Modified for Indonesian Legal Documents

This version has been modified to focus on generating question-SPARQL pairs
for Indonesian legal documents from the data-lex2kg knowledge graph.
"""

import json
import random
import re
import datetime
import csv
import io
import os

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for legal documents."""
    
    def __init__(self, config):
        """
        Initialize the generator with knowledge graph schema information
        
        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()
        
        # print("===============================================")
        # for i in self.entity_examples:
        #     print(i)
        # print("===============================================")
        

    def initialize_templates(self):
        """
        Initialize question-query template pairs for legal document data
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # Legal document specific templates
        legal_templates = [
            # Basic information about laws (UU)
            {
                "id": "law-title",
                "category": "legal",
                "questionTemplate": "Apa isi dari {entity}?",
                "englishQuestion": "What is the title of {entity}?",
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                      {entity} lex:tentang ?title .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "law-enactment-date",
                "category": "legal",
                "questionTemplate": "Kapan {entity} disahkan?",
                "englishQuestion": "When was {entity} enacted?",
                "sparqlTemplate": """
                    SELECT ?date WHERE {
                      {entity} lex:disahkanPada ?date .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "law-enactment-location",
                "category": "legal",
                "questionTemplate": "Di mana {entity} disahkan?",
                "englishQuestion": "Where was {entity} enacted?",
                "sparqlTemplate": """
                    SELECT ?location WHERE {
                      {entity} lex:disahkanDi ?location .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "law-enactment-person",
                "category": "legal",
                "questionTemplate": "Siapa yang mengesahkan {entity}?",
                "englishQuestion": "Who enacted {entity}?",
                "sparqlTemplate": """
                    SELECT ?person WHERE {
                      {entity} lex:disahkanOleh ?person .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "law-enactment-position",
                "category": "legal",
                "questionTemplate": "Apa jabatan pengesah {entity}?",
                "englishQuestion": "What is the position of the person who enacted {entity}?",
                "sparqlTemplate": """
                    SELECT ?position WHERE {
                      {entity} lex:jabatanPengesah ?position .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "law-type",
                "category": "legal",
                "questionTemplate": "Apa jenis peraturan dari {entity}?",
                "englishQuestion": "What type of regulation is {entity}?",
                "sparqlTemplate": """
                    SELECT ?type WHERE {
                      {entity} lex:jenisPeraturan ?type .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "article-text",
                "category": "legal",
                "questionTemplate": "Apa isi dari {entity}?",
                "englishQuestion": "What is the content of {entity}?",
                "sparqlTemplate": """
                    SELECT ?text WHERE {
                      {entity} lex:teks ?text .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "article-version",
                "category": "legal",
                "questionTemplate": "Apa versi terbaru dari {entity}?",
                "englishQuestion": "What is the latest version of {entity}?",
                "sparqlTemplate": """
                    SELECT ?version WHERE {
                      {entity} lex:versi ?version .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "chapter-title",
                "category": "legal",
                "questionTemplate": "Apa judul dari {entity}?",
                "englishQuestion": "What is the title of {entity}?",
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                      {entity} lex:judul ?title .
                    }
                """,
                "complexity": "basic"
            },
            
            # Intermediate: Structure and relationships
            {
                "id": "law-articles",
                "category": "legal",
                "questionTemplate": "Berapa jumlah pasal dalam {entity}?",
                "englishQuestion": "How many articles are in {entity}?",
                "sparqlTemplate": """
                    SELECT (COUNT(?article) AS ?count) WHERE {
                      {entity} lex:pasal ?article .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "law-chapters",
                "category": "legal",
                "questionTemplate": "Berapa jumlah bab dalam {entity}?",
                "englishQuestion": "How many chapters are in {entity}?",
                "sparqlTemplate": """
                    SELECT (COUNT(?chapter) AS ?count) WHERE {
                      {entity} lex:daftarBab ?chapters .
                      ?chapters lex:bab ?chapter .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "article-sections",
                "category": "legal",
                "questionTemplate": "Berapa jumlah ayat dalam {entity}?",
                "englishQuestion": "How many sections are in {entity}?",
                "sparqlTemplate": """
                    SELECT (COUNT(?section) AS ?count) WHERE {
                      {entity} lex:versi ?version .
                      ?version lex:daftarAyat ?sections .
                      ?sections lex:ayat ?section .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "law-amended-by",
                "category": "legal",
                "questionTemplate": "Peraturan mana yang mengubah {entity}?",
                "englishQuestion": "Which regulations amended {entity}?",
                "sparqlTemplate": """
                    SELECT ?amendment WHERE {
                      ?article lex:mengubah {entity} .
                      ?article lex:bagianDari ?amendment .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "laws-enacted-in-year",
                "category": "legal",
                "questionTemplate": "Undang-undang apa saja yang disahkan pada tahun {value}?",
                "englishQuestion": "What laws were enacted in the year {value}?",
                "sparqlTemplate": """
                    SELECT ?law ?title WHERE {
                      ?law lex:tahun {value} .
                      ?law lex:tentang ?title .
                    }
                """,
                "complexity": "intermediate"
            },
            
            # Advanced: Complex relationships and analytics
            {
                "id": "article-references",
                "category": "legal",
                "questionTemplate": "Pasal mana saja yang merujuk ke {entity}?",
                "englishQuestion": "Which articles reference {entity}?",
                "sparqlTemplate": """
                    SELECT ?referringArticle ?text WHERE {
                      ?textSegment lex:merujuk {entity} .
                      ?textSegment lex:bagianDari ?referringArticle .
                      ?referringArticle lex:teks ?text .
                    }
                    LIMIT 10
                """,
                "complexity": "advanced"
            },
            {
                "id": "law-amendments",
                "category": "legal",
                "questionTemplate": "Undang-undang apa saja yang diubah oleh {entity}?",
                "englishQuestion": "Which laws were amended by {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?amendedLaw ?title WHERE {
                      {entity} lex:pasal ?article .
                      ?article lex:versi ?articleVersion .
                      ?articleVersion lex:huruf ?letter .
                      ?letter lex:mengubah ?amendedArticle .
                      ?amendedArticle lex:bagianDari ?amendedLaw .
                      ?amendedLaw lex:tentang ?title .
                    }
                    LIMIT 10
                """,
                "complexity": "advanced"
            },
            {
                "id": "law-by-keyword",
                "category": "legal",
                "questionTemplate": "Undang-undang apa saja yang berhubungan dengan '{value}'?",
                "englishQuestion": "Which laws are related to '{value}'?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?law ?title WHERE {
                      ?law lex:tentang ?title .
                      FILTER(CONTAINS(LCASE(?title), LCASE("{value}")))
                    }
                    LIMIT 10
                """,
                "complexity": "advanced"
            },
            {
                "id": "law-with-most-articles",
                "category": "legal",
                "questionTemplate": "Undang-undang dengan jumlah pasal terbanyak?",
                "englishQuestion": "Which law has the most articles?",
                "sparqlTemplate": """
                    SELECT ?law ?title (COUNT(?article) AS ?articleCount) WHERE {
                      ?law lex:tentang ?title .
                      ?law lex:pasal ?article .
                    }
                    GROUP BY ?law ?title
                    ORDER BY DESC(?articleCount)
                    LIMIT 5
                """,
                "complexity": "advanced"
            },
            {
                "id": "law-by-enactor",
                "category": "legal",
                "questionTemplate": "Undang-undang apa saja yang disahkan oleh {value}?",
                "englishQuestion": "What laws were enacted by {value}?",
                "sparqlTemplate": """
                    SELECT ?law ?title ?date WHERE {
                      ?law lex:disahkanOleh "{value}" .
                      ?law lex:tentang ?title .
                      ?law lex:disahkanPada ?date .
                    }
                    ORDER BY DESC(?date)
                    LIMIT 10
                """,
                "complexity": "advanced"
            }
        ]
        
        # Only use legal templates, ignoring any custom templates
        # to focus specifically on legal document data
        return legal_templates

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True,
                        variations_per_question=3, validate_queries=False):
        """
        Generate dataset based on legal document knowledge graph
        
        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            variations_per_question (int): Number of variations per question
            validate_queries (bool): Whether to validate SPARQL queries
            
        Returns:
            list: Array of question-SPARQL pairs
        """
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.5,
                "intermediate": 0.3,
                "advanced": 0.2
            }
        
        dataset = []
        id_counter = 1
        
        # Calculate how many questions of each complexity to generate
        counts_by_complexity = {}
        for complexity, proportion in complexity_distribution.items():
            counts_by_complexity[complexity] = int(size * proportion)
        
        # Generate questions for each complexity level
        for complexity, count in counts_by_complexity.items():
            eligible_templates = [t for t in self.templates if t["complexity"] == complexity]
            
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            for i in range(count):
                if len(dataset) >= size:
                    break
                
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)
                
                try:
                    # Instantiate the template
                    instance = self.instantiate_template(template)
                    
                    if instance:
                        # Add the base question-query pair
                        dataset.append({
                            "id": f"q{id_counter}",
                            "question": instance["question"],
                            "englishQuestion": instance["englishQuestion"],
                            "sparql": instance["sparql"],
                            "category": template["category"],
                            "complexity": template["complexity"],
                            "templateId": template["id"]
                        })
                        id_counter += 1
                        
                        # Add variations if requested
                        if include_variations and instance["question"]:
                            variations = self.variation_generator.generate_variations(
                                instance["question"],
                                instance["englishQuestion"],
                                template["category"],
                                min(variations_per_question, 5)
                            )
                            
                            for variation in variations:
                                if len(dataset) >= size:
                                    break
                                
                                dataset.append({
                                    "id": f"q{id_counter}",
                                    "question": variation["indonesian"],
                                    "englishQuestion": variation["english"],
                                    "sparql": instance["sparql"],
                                    "category": template["category"],
                                    "complexity": template["complexity"],
                                    "templateId": template["id"],
                                    "isVariation": True
                                })
                                id_counter += 1
                except Exception as e:
                    print(f"Error instantiating template {template['id']}: {e}")
        
        # Validate queries if requested
        if validate_queries and hasattr(self.config, "query_validator"):
            validator = self.config["query_validator"]
            filtered_dataset = []
            
            for item in dataset:
                try:
                    if validator(item["sparql"]):
                        filtered_dataset.append(item)
                    else:
                        print(f"Invalid SPARQL query for id {item['id']}")
                except Exception as e:
                    print(f"Error validating query for id {item['id']}: {e}")
            
            return filtered_dataset
        
        return dataset

    def instantiate_template(self, template):
        """
        Instantiate a template with specific entities and properties
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Select entities and properties appropriate for this template
        placeholders = self.extract_placeholders(template)
        replacements = self.select_replacements(placeholders, template)
        
        if not replacements:
            return None
        
        # Apply replacements to the question template
        question = template["questionTemplate"].strip()
        english_question = template["englishQuestion"].strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Add prefixes to SPARQL query
        prefix_string = ""
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        sparql = prefix_string + sparql
        
        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
            
            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            question = re.sub(pattern, replacement_text, question)
            english_question = re.sub(pattern, replacement_text, english_question)
            
            # Replace in SPARQL
            if "uri" in replacement:
                sparql_value = f"<{replacement['uri']}>"
            elif "sparqlValue" in replacement:
                sparql_value = replacement["sparqlValue"]
            else:
                sparql_value = replacement["value"]
                
            sparql = re.sub(pattern, sparql_value, sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}

    def extract_placeholders(self, template):
        """
        Extract all placeholders from template
        
        Args:
            template (dict): Template with question and SPARQL
            
        Returns:
            set: Set of placeholder names
        """
        placeholders = set()
        
        # For Python triple-quoted strings, we need to handle whitespace
        # First, normalize the templates by removing extra whitespace
        question_template = template["questionTemplate"].strip()
        english_question = template["englishQuestion"].strip()
        sparql_template = template["sparqlTemplate"].strip()
        
        # Use a pattern that can handle potential whitespace around the placeholders
        pattern = r"{[\s]*([^{}]+)[\s]*}"
        
        # Search in question template
        for match in re.finditer(pattern, question_template):
            placeholders.add(match.group(1).strip())
            
        # Search in English question template (for consistency)
        for match in re.finditer(pattern, english_question):
            placeholders.add(match.group(1).strip())
        
        # Search in SPARQL template
        for match in re.finditer(pattern, sparql_template):
            placeholders.add(match.group(1).strip())
        
        return placeholders

    def select_replacements(self, placeholders, template):
        """
        Select appropriate replacements for template placeholders
        
        Args:
            placeholders (set): Set of placeholder names
            template (dict): The template being instantiated
            
        Returns:
            dict: Map of placeholder to replacement value or None if failed
        """
        replacements = {}
        
        # Try to select appropriate values for each placeholder
        for placeholder in placeholders:
            replacement = None
            
            # Handle entity placeholders
            if placeholder.startswith('entity'):
                # Select entity based on template type
                if "law-" in template["id"]:
                    # For law templates, select a UU entity
                    replacement = self.select_entity_by_pattern("uu/")
                elif "article" in template["id"]:
                    # For article templates, select a pasal entity
                    replacement = self.select_entity_by_pattern("pasal/")
                elif "chapter" in template["id"]:
                    # For chapter templates, select a bab entity
                    replacement = self.select_entity_by_pattern("bab/")
                else:
                    # Default to any entity
                    replacement = self.select_random_entity()
                
                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()
            
            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                if "law-by-enactor" in template["id"]:
                    # For law by enactor, use a person name
                    replacement = self.select_enactor_value()
                elif "laws-enacted-in-year" in template["id"]:
                    # For laws by year, use a year
                    replacement = self.select_year_value()
                elif "law-by-keyword" in template["id"]:
                    # For laws by keyword, use a keyword
                    replacement = self.select_keyword_value()
                else:
                    replacement = self.select_random_value(template)
            
            # Handle property placeholders
            elif placeholder.startswith('property'):
                replacement = self.select_legal_property(template, placeholder)
            
            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None
            
            replacements[placeholder] = replacement
        
        return replacements

    def select_entity_by_pattern(self, pattern):
        """
        Select a random entity that matches a URI pattern
        
        Args:
            pattern (str): Pattern to match in entity URI
            
        Returns:
            dict: Selected entity or None
        """
        # Filter entities by URI pattern
        matching_entities = [e for e in self.entity_examples if pattern in e.get("uri", "")]
        
        if matching_entities:
            return random.choice(matching_entities)
        
        return None

    def select_random_entity(self):
        """
        Select a random entity from available examples
        
        Returns:
            dict: Selected entity
        """
        # If we have entity examples from the schema extractor, use them
        if self.entity_examples:
            return random.choice(self.entity_examples)
        
        # Fallback to predefined legal entities
        # This ensures we always have something workable for the legal data
        legal_entities = [
            {"value": "lex:UU-2020-9", "label": "UU No. 9 Tahun 2020", 
             "uri": "https://example.org/lex2kg/uu/2020/9", "type": "lex:UndangUndang"},
            {"value": "lex:UU-2020-11", "label": "UU No. 11 Tahun 2020", 
             "uri": "https://example.org/lex2kg/uu/2020/11", "type": "lex:UndangUndang"},
            {"value": "lex:UU-2020-9-pasal-47", "label": "Pasal 47 UU No. 9 Tahun 2020", 
             "uri": "https://example.org/lex2kg/uu/2020/9/pasal/0047", "type": "lex:Pasal"},
            {"value": "lex:UU-2020-11-bab-10", "label": "Bab 10 UU No. 11 Tahun 2020", 
             "uri": "https://example.org/lex2kg/uu/2020/11/bab/0010", "type": "lex:Bab"},
            {"value": "lex:UU-2020-9-pasal-46-ayat-1", "label": "Pasal 46 Ayat 1 UU No. 9 Tahun 2020", 
             "uri": "https://example.org/lex2kg/uu/2020/9/pasal/0046/versi/20201026/ayat/0001", "type": "lex:Ayat"}
        ]
        
        print("Warning: Using fallback legal entities")
        return random.choice(legal_entities)

    def select_legal_property(self, template, placeholder):
        """
        Select a property appropriate for legal templates
        
        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name
            
        Returns:
            dict: Selected property
        """
        # Define common legal properties
        legal_properties = {
            "title": {"value": "lex:tentang", "label": "tentang", 
                     "uri": "https://example.org/lex2kg/ontology/tentang"},
            "enactment_date": {"value": "lex:disahkanPada", "label": "disahkan pada", 
                              "uri": "https://example.org/lex2kg/ontology/disahkanPada"},
            "enactment_location": {"value": "lex:disahkanDi", "label": "disahkan di", 
                                  "uri": "https://example.org/lex2kg/ontology/disahkanDi"},
            "enactor": {"value": "lex:disahkanOleh", "label": "disahkan oleh", 
                       "uri": "https://example.org/lex2kg/ontology/disahkanOleh"},
            "enactor_position": {"value": "lex:jabatanPengesah", "label": "jabatan pengesah", 
                                "uri": "https://example.org/lex2kg/ontology/jabatanPengesah"},
            "regulation_type": {"value": "lex:jenisPeraturan", "label": "jenis peraturan", 
                               "uri": "https://example.org/lex2kg/ontology/jenisPeraturan"},
            "content": {"value": "lex:teks", "label": "teks", 
                       "uri": "https://example.org/lex2kg/ontology/teks"},
            "chapter_title": {"value": "lex:judul", "label": "judul", 
                             "uri": "https://example.org/lex2kg/ontology/judul"}
        }
        
        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "title" in template["id"] or "title" in placeholder:
                prop = self.find_property_by_name("tentang") or self.find_property_by_name("judul")
                if prop:
                    return prop
                
            elif "enactment-date" in template["id"] or "date" in placeholder:
                prop = self.find_property_by_name("disahkanPada")
                if prop:
                    return prop
                
            elif "enactment-location" in template["id"] or "location" in placeholder:
                prop = self.find_property_by_name("disahkanDi")
                if prop:
                    return prop
                
            elif "enactment-person" in template["id"] or "person" in placeholder:
                prop = self.find_property_by_name("disahkanOleh")
                if prop:
                    return prop
                
            elif "enactment-position" in template["id"] or "position" in placeholder:
                prop = self.find_property_by_name("jabatanPengesah")
                if prop:
                    return prop
                
            elif "type" in template["id"] or "type" in placeholder:
                prop = self.find_property_by_name("jenisPeraturan")
                if prop:
                    return prop
                
            elif "text" in template["id"] or "content" in placeholder:
                prop = self.find_property_by_name("teks")
                if prop:
                    return prop
        
        # If we don't have the property in schema info, use our predefined ones
        if "title" in template["id"] or "title" in placeholder:
            if "chapter" in template["id"]:
                return legal_properties["chapter_title"]
            else:
                return legal_properties["title"]
            
        elif "enactment-date" in template["id"] or "date" in placeholder:
            return legal_properties["enactment_date"]
            
        elif "enactment-location" in template["id"] or "location" in placeholder:
            return legal_properties["enactment_location"]
            
        elif "enactment-person" in template["id"] or "person" in placeholder:
            return legal_properties["enactor"]
            
        elif "enactment-position" in template["id"] or "position" in placeholder:
            return legal_properties["enactor_position"]
            
        elif "type" in template["id"] or "type" in placeholder:
            return legal_properties["regulation_type"]
            
        elif "text" in template["id"] or "content" in placeholder:
            return legal_properties["content"]
            
        # Fallback to any property if we can't find a specific match
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return random.choice(self.schema_info["properties"])
            
        # Last resort - return title as default
        return legal_properties["title"]

    def select_enactor_value(self):
        """
        Select a realistic enactor value for legal documents
        
        Returns:
            dict: Enactor value object
        """
        enactors = ["JOKO WIDODO", "SUSILO BAMBANG YUDHOYONO", "MEGAWATI SOEKARNOPUTRI"]
        value = random.choice(enactors)
        return {"value": value, "label": value}

    def select_year_value(self):
        """
        Select a realistic year value for legal documents
        
        Returns:
            dict: Year value object
        """
        years = [2015, 2016, 2017, 2018, 2019, 2020]
        value = random.choice(years)
        return {"value": str(value), "label": str(value)}

    def select_keyword_value(self):
        """
        Select a keyword value for searching legal documents
        
        Returns:
            dict: Keyword value object
        """
        keywords = ["KESEHATAN", "PENDIDIKAN", "LINGKUNGAN", "KETENAGAKERJAAN", "PAJAK", "INVESTASI"]
        value = random.choice(keywords)
        return {"value": value, "label": value}

    def select_random_value(self, template):
        """
        Select a random appropriate value
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Special handling for legal data
        if template.get("category") == "legal":
            if "law-by-enactor" in template["id"]:
                return self.select_enactor_value()
            elif "laws-enacted-in-year" in template["id"]:
                return self.select_year_value()
            elif "law-by-keyword" in template["id"]:
                return self.select_keyword_value()
            
        # Default to a generic value
        dummy_value = random.randint(1, 10)
        return {"value": str(dummy_value), "label": str(dummy_value)}

    def find_property_by_name(self, name):
        """
        Find a property by name in schema info
        
        Args:
            name (str): Property name to find
            
        Returns:
            dict: Found property or None
        """
        if "properties" not in self.schema_info:
            return None
        
        for prop in self.schema_info["properties"]:
            if (name in prop["value"] or 
                name in prop["label"] or 
                (prop.get("uri", "").split("/")[-1] == name)):
                return prop
        
        return None

    def select_random_from_array(self, array):
        """
        Select a random item from an array
        
        Args:
            array (list): Array to select from
            
        Returns:
            Any: Random item or None if array is empty
        """
        if not array:
            return None
        
        return random.choice(array)

    def format_sparql(self, sparql):
        """
        Format SPARQL query for readability with properly formatted URIs
        
        Args:
            sparql (str): Raw SPARQL query
            
        Returns:
            str: Formatted SPARQL query
        """
        # First, clean URIs by removing spaces within angle brackets
        # This needs to happen BEFORE other formatting
        def clean_uri(match):
            uri = match.group(0)
            # Aggressively remove all spaces from URIs
            # print(uri, "ini uriiii")
            return uri.replace(" ", "")
        
        # Fix all URIs first by removing spaces
        sparql = re.sub(r'<[^>]+>', clean_uri, sparql)
        
        # Now proceed with other formatting
        sparql = re.sub(r'PREFIX\s+\w+:\s+<[^>]+>\s*', '', sparql)
        sparql = re.sub(r'\s+', ' ', sparql)
        
        # Format spaces around keywords properly
        sparql = re.sub(r'(?i)\bSELECT\b', 'select', sparql)
        sparql = re.sub(r'(?i)\bWHERE\b', ' where ', sparql)
        sparql = re.sub(r'(?i)\bFILTER\b', ' filter ', sparql)
        sparql = re.sub(r'(?i)\bORDER BY\b', ' order by ', sparql)
        sparql = re.sub(r'(?i)\bLIMIT\b', ' limit ', sparql)
        sparql = re.sub(r'(?i)\bGROUP BY\b', ' group by ', sparql)
        sparql = re.sub(r'(?i)\bHAVING\b', ' having ', sparql)
        sparql = re.sub(r'(?i)\bCOUNT\b', 'count', sparql)
        sparql = re.sub(r'(?i)\bAS\b', ' as ', sparql)
        sparql = re.sub(r'(?i)\bDISTINCT\b', 'distinct ', sparql)
        
        # Format braces
        sparql = re.sub(r'\s*{\s*', ' { ', sparql)
        sparql = re.sub(r'\s*}\s*', ' } ', sparql)
        
        # Fix the dot spacing - NO SPACES around dots
        sparql = re.sub(r'\s*\.\s*', '.', sparql)
        
        # Final cleanup of any double spaces
        sparql = re.sub(r'\s+', ' ', sparql).strip()
        
        # print(sparql, "ini sparql nya bosssss")
        return sparql

    def export_json(self, dataset):
        """
        Export dataset to JSON format
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: JSON string
        """
        return json.dumps(dataset, indent=2)

    def export_csv(self, dataset):
        """
        Export dataset to CSV format
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(['id', 'question', 'englishQuestion', 'sparql', 'category', 'complexity', 'templateId'])
        
        # Write rows
        for item in dataset:
            sparql_escaped = item["sparql"].replace("\n", " ")
            writer.writerow([
                item["id"],
                item["question"],
                item["englishQuestion"],
                sparql_escaped,
                item["category"],
                item["complexity"],
                item["templateId"]
            ])
        
        return output.getvalue()

    def export_jsonl(self, dataset):
        """
        Export dataset to JSONL format (one JSON object per line)
        
        Args:
            dataset (list): Generated dataset
            
        Returns:
            str: JSONL string
        """
        return "\n".join(json.dumps(item) for item in dataset)


class VariationGenerator:
    """Generates variations of natural language questions"""
    
    def generate_variations(self, question, english_question, category, count=3):
        """
        Generate variations of a question
        
        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English
            category (str): Question category
            count (int): Number of variations to generate
            
        Returns:
            list: Array of variation dictionaries with Indonesian and English versions
        """
        variations = []
        
        # Add legal-specific variations
        if category == "legal":
            variations.extend(self.get_legal_variations(question, english_question))
        
        # Add general variations
        variations.extend(self.get_general_variations(question, english_question))
        
        # Ensure we don't have duplicate variations
        unique_variations = []
        seen_questions = set()
        
        for var in variations:
            if var["indonesian"] not in seen_questions:
                seen_questions.add(var["indonesian"])
                unique_variations.append(var)
        
        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[:min(count, len(unique_variations))]

    def get_legal_variations(self, question, english_question):
        """
        Get variations specific to legal document questions
        
        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # "Apa judul dari" variations
        if question.startswith("Apa judul dari"):
            variations.append({
                "indonesian": question.replace("Apa judul dari", "Apa nama dari"),
                "english": english_question.replace("What is the title of", "What is the name of")
            })
            variations.append({
                "indonesian": question.replace("Apa judul dari", "Bagaimana judul dari"),
                "english": english_question.replace("What is the title of", "How is the title of")
            })
            variations.append({
                "indonesian": "Tolong beritahu saya " + question.lower(),
                "english": "Please tell me " + english_question.lower()
            })
        
        # "Kapan" variations
        elif question.startswith("Kapan"):
            variations.append({
                "indonesian": question.replace("Kapan", "Pada tanggal berapa"),
                "english": english_question.replace("When was", "On what date was")
            })
            variations.append({
                "indonesian": "Tanggal berapa " + question[6:],
                "english": "What date was " + english_question[9:]
            })
        
        # "Di mana" variations
        elif question.startswith("Di mana"):
            variations.append({
                "indonesian": question.replace("Di mana", "Di kota mana"),
                "english": english_question.replace("Where was", "In which city was")
            })
            variations.append({
                "indonesian": question.replace("Di mana", "Di tempat mana"),
                "english": english_question.replace("Where was", "In what place was")
            })
        
        # "Siapa yang" variations
        elif question.startswith("Siapa yang"):
            variations.append({
                "indonesian": question.replace("Siapa yang", "Siapa nama orang yang"),
                "english": english_question.replace("Who", "What is the name of the person who")
            })
            variations.append({
                "indonesian": "Oleh siapa " + question[10:].replace("mengesahkan", "disahkan"),
                "english": "By whom was " + english_question[4:].replace("enacted", "signed")
            })
        
        # "Apa jabatan" variations
        elif question.startswith("Apa jabatan"):
            variations.append({
                "indonesian": question.replace("Apa jabatan", "Apa posisi"),
                "english": english_question.replace("What is the position", "What is the role")
            })
        
        # "Apa jenis peraturan" variations
        elif question.startswith("Apa jenis peraturan"):
            variations.append({
                "indonesian": question.replace("Apa jenis peraturan", "Apa kategori peraturan"),
                "english": english_question.replace("What type of regulation", "What category of regulation")
            })
            variations.append({
                "indonesian": question.replace("Apa jenis peraturan dari", "Termasuk jenis peraturan apa"),
                "english": english_question.replace("What type of regulation is", "Which type of regulation is")
            })
        
        # "Apa isi dari" variations
        elif question.startswith("Apa isi dari"):
            variations.append({
                "indonesian": question.replace("Apa isi dari", "Apa konten dari"),
                "english": english_question.replace("What is the content of", "What is the text of")
            })
            variations.append({
                "indonesian": question.replace("Apa isi dari", "Bagaimana bunyi dari"),
                "english": english_question.replace("What is the content of", "How does the text read for")
            })
        
        # "Berapa jumlah" variations
        elif question.startswith("Berapa jumlah"):
            variations.append({
                "indonesian": "Ada berapa " + question[13:],
                "english": "How many " + english_question[13:]
            })
        
        return variations

    def get_general_variations(self, question, english_question):
        """
        Get general variations that apply to any question
        
        Args:
            question (str): Original question in Indonesian
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # Add please
        if question.endswith('?'):
            variations.append({
                "indonesian": question.replace('?', ' tolong?'),
                "english": english_question.replace('?', ' please?')
            })
        
        # Could you tell me...
        variations.append({
            "indonesian": f"Bisakah Anda memberi tahu saya {question.lower()}",
            "english": f"Could you tell me {english_question.lower()}"
        })
        
        # I want to know...
        variations.append({
            "indonesian": f"Saya ingin mengetahui {question.lower()}",
            "english": f"I want to know {english_question.lower()}"
        })
        
        return variations