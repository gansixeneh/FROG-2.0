"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Modified for University Course Data

This version has been temporarily modified to focus exclusively on generating question-SPARQL pairs
for the university course TTL file (final_result.ttl).
"""

import json
import random
import re
import datetime
import csv
import io
import os

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for university courses."""
    
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
        
        print("======================================")
        print(self.entity_examples)
        print("======================================")
        

    def initialize_templates(self):
        """
        Initialize question-query template pairs for university course data
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # University course specific templates
        university_templates = [
            # Basic course information templates
            {
                "id": "course-credits",
                "category": "university",
                "questionTemplate": "How many credits does the {entity} course have?",
                "sparqlTemplate": """
                    SELECT ?value WHERE {
                      {entity} ns1:has_credits ?value .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-code",
                "category": "university",
                "questionTemplate": "What is the course code for {entity}?",
                "sparqlTemplate": """
                    SELECT ?code WHERE {
                      {entity} ns1:has_course_code ?code .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-category",
                "category": "university",
                "questionTemplate": "What category does {entity} belong to?",
                "sparqlTemplate": """
                    SELECT ?category WHERE {
                      {entity} ns1:has_course_category ?category .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-prerequisites",
                "category": "university",
                "questionTemplate": "What are the prerequisites for {entity}?",
                "sparqlTemplate": """
                    SELECT ?prereq WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-evaluation",
                "category": "university",
                "questionTemplate": "What evaluation methods are used for {entity}?",
                "sparqlTemplate": """
                    SELECT ?method WHERE {
                      {entity} ns1:has_evaluation_method ?method .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-research-group",
                "category": "university",
                "questionTemplate": "Which research group is associated with {entity}?",
                "sparqlTemplate": """
                    SELECT ?group WHERE {
                      {entity} ns1:has_research_group ?group .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "course-nickname",
                "category": "university",
                "questionTemplate": "What are the alternative names or abbreviations for {entity}?",
                "sparqlTemplate": """
                    SELECT ?nickname WHERE {
                      {entity} ns1:also_known_as ?nickname .
                    }
                """,
                "complexity": "basic"
            },
            
            # Intermediate templates
            {
                "id": "count-prerequisites",
                "category": "university",
                "questionTemplate": "How many prerequisites does {entity} have?",
                "sparqlTemplate": """
                    SELECT (COUNT(?prereq) AS ?count) WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "courses-with-credits",
                "category": "university",
                "questionTemplate": "Which courses have {value} credits?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_credits {value} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "courses-by-research-group",
                "category": "university",
                "questionTemplate": "Which courses are associated with the {entity} research group?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_research_group {entity} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "courses-by-evaluation",
                "category": "university",
                "questionTemplate": "Which courses are evaluated using {entity}?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_evaluation_method {entity} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "count-courses-by-category",
                "category": "university",
                "questionTemplate": "How many courses are in the {entity} category?",
                "sparqlTemplate": """
                    SELECT (COUNT(?course) AS ?count) WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_course_category {entity} .
                    }
                """,
                "complexity": "intermediate"
            },
            
            # Advanced templates
            {
                "id": "courses-with-same-prerequisites",
                "category": "university",
                "questionTemplate": "Which courses have the same prerequisites as {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?course WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                      ?course ns1:has_prerequisite_course ?prereq .
                      FILTER(?course != {entity})
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-most-credits",
                "category": "university",
                "questionTemplate": "Which courses have the highest number of credits?",
                "sparqlTemplate": """
                    SELECT ?course ?credits WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_credits ?credits .
                    }
                    ORDER BY DESC(?credits)
                    LIMIT 5
                """,
                "complexity": "advanced"
            },
            {
                "id": "research-group-most-courses",
                "category": "university",
                "questionTemplate": "Which research group is associated with the most courses?",
                "sparqlTemplate": """
                    SELECT ?group (COUNT(?course) as ?count) WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_research_group ?group .
                    }
                    GROUP BY ?group
                    ORDER BY DESC(?count)
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "common-prerequisites",
                "category": "university",
                "questionTemplate": "What are the most common prerequisite courses?",
                "sparqlTemplate": """
                    SELECT ?prereq (COUNT(?course) as ?count) WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                    }
                    GROUP BY ?prereq
                    ORDER BY DESC(?count)
                    LIMIT 5
                """,
                "complexity": "advanced"
            }
        ]
        
        # Only use university templates for now, ignoring any custom templates 
        # to focus specifically on university course data
        return university_templates

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True,
                        variations_per_question=3, validate_queries=False):
        """
        Generate dataset based on university course knowledge graph
        
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
                "basic": 0.6,
                "intermediate": 0.3,
                "advanced": 0.1
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
            # print(complexity, count, eligible_templates)
            # print()
            # print("==============================")
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            for i in range(count):
                
                if len(dataset) >= size:
                    break
                
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)
                print(template, "*******************\n")
                if complexity == "advance":
                    print(template, "*******************\n")
                
                try:
                    # Instantiate the template
                    instance = self.instantiate_template(template)
                    
                    if instance:
                        # Add the base question-query pair
                        dataset.append({
                            "id": f"q{id_counter}",
                            "question": instance["question"],
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
                                template["category"],
                                min(variations_per_question, 5)
                            )
                            
                            for variation in variations:
                                if len(dataset) >= size:
                                    break
                                
                                dataset.append({
                                    "id": f"q{id_counter}",
                                    "question": variation,
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
        sparql = template["sparqlTemplate"].strip()
        
        # Skip adding prefixes to SPARQL query - we'll use full URIs instead
        
        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
            
            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            question = re.sub(pattern, replacement_text, question)
            
            # Replace in SPARQL
            if "uri" in replacement:
                sparql_value = f"<{replacement['uri']}>"
            elif "sparqlValue" in replacement:
                sparql_value = replacement["sparqlValue"]
            else:
                sparql_value = replacement["value"]
                
            sparql = re.sub(pattern, sparql_value, sparql)
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "sparql": sparql}

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
        sparql_template = template["sparqlTemplate"].strip()
        
        # Use a pattern that can handle potential whitespace around the placeholders
        pattern = r"{[\s]*([^{}]+)[\s]*}"
        
        # Search in question template
        for match in re.finditer(pattern, question_template):
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
            
            # Handle entity placeholders - UNIVERSITY SPECIFIC
            if placeholder.startswith('entity'):
                # For university data, select appropriate entity type based on template
                if "research-group" in template["id"] or "courses-by-research-group" in template["id"]:
                    replacement = self.select_entity_by_type("ns1:research_lab")
                elif "courses-by-evaluation" in template["id"]:
                    replacement = self.select_entity_by_type("ns1:evaluation")
                elif "courses-by-category" in template["id"] or "course-category" in template["id"]:
                    replacement = self.select_entity_by_type("ns1:course_category")
                else:
                    # Default to course entities
                    replacement = self.select_entity_by_type("ns1:course")
                
                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()
            
            # Handle value placeholders - UNIVERSITY SPECIFIC
            elif placeholder == "value" or placeholder.endswith("Value"):
                if "credits" in template["id"]:
                    # For credit-related templates, use realistic credit values
                    replacement = self.select_credit_value()
                else:
                    replacement = self.select_random_value(template)
            
            # Handle property placeholders
            elif placeholder.startswith('property'):
                replacement = self.select_university_property(template, placeholder)
            
            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None
            
            replacements[placeholder] = replacement
        
        return replacements

    def select_entity_by_type(self, type_value):
        """
        Select a random entity of a specific type
        
        Args:
            type_value (str): The type to filter by
            
        Returns:
            dict: Selected entity or None
        """
        # Filter entities by type
        matching_entities = [e for e in self.entity_examples if e.get("type") == type_value]
        
        if matching_entities:
            return random.choice(matching_entities)
        
        return None

    def select_random_entity(self):
        """
        Select a random entity from available examples - MODIFIED FOR UNIVERSITY COURSE DATA
        
        Returns:
            dict: Selected entity
        """
        # If we have entity examples from the schema extractor, use them
        if self.entity_examples:
            return random.choice(self.entity_examples)
        
        # Fallback to predefined university course entities
        # This ensures we always have something workable for the university data
        university_entities = [
            {"value": "ns1:advanced_database", "label": "Advanced Database", 
             "uri": "http://example.org/advanced_database", "type": "ns1:course"},
            {"value": "ns1:algorithm_design_and_analysis", "label": "Algorithm Design and Analysis", 
             "uri": "http://example.org/algorithm_design_and_analysis", "type": "ns1:course"},
            {"value": "ns1:machine_learning", "label": "Machine Learning", 
             "uri": "http://example.org/machine_learning", "type": "ns1:course"},
            {"value": "ns1:computer_vision", "label": "Computer Vision", 
             "uri": "http://example.org/computer_vision", "type": "ns1:course"},
            {"value": "ns1:deep_learning", "label": "Deep Learning", 
             "uri": "http://example.org/deep_learning", "type": "ns1:course"}
        ]
        
        print("Warning: Using fallback university entities")
        return random.choice(university_entities)

    def select_university_property(self, template, placeholder):
        """
        Select a property appropriate for university course templates
        
        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name
            
        Returns:
            dict: Selected property
        """
        # Define common university course properties
        university_properties = {
            "credits": {"value": "ns1:has_credits", "label": "credits", 
                       "uri": "http://example.org/has_credits"},
            "prerequisite": {"value": "ns1:has_prerequisite_course", "label": "prerequisite course", 
                            "uri": "http://example.org/has_prerequisite_course"},
            "code": {"value": "ns1:has_course_code", "label": "course code", 
                    "uri": "http://example.org/has_course_code"},
            "evaluation": {"value": "ns1:has_evaluation_method", "label": "evaluation method", 
                          "uri": "http://example.org/has_evaluation_method"},
            "research": {"value": "ns1:has_research_group", "label": "research group", 
                        "uri": "http://example.org/has_research_group"},
            "category": {"value": "ns1:has_course_category", "label": "course category", 
                        "uri": "http://example.org/has_course_category"},
            "nickname": {"value": "ns1:also_known_as", "label": "also known as", 
                        "uri": "http://example.org/also_known_as"},
        }
        
        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "credit" in template["id"] or "credit" in placeholder:
                prop = self.find_property_by_name("has_credits")
                if prop:
                    return prop
                
            elif "prerequisite" in template["id"] or "prerequisite" in placeholder:
                prop = self.find_property_by_name("has_prerequisite_course")
                if prop:
                    return prop
                
            elif "code" in template["id"] or "code" in placeholder:
                prop = self.find_property_by_name("has_course_code")
                if prop:
                    return prop
                
            elif "evaluation" in template["id"] or "evaluation" in placeholder:
                prop = self.find_property_by_name("has_evaluation_method")
                if prop:
                    return prop
                
            elif "research" in template["id"] or "research" in placeholder:
                prop = self.find_property_by_name("has_research_group")
                if prop:
                    return prop
                
            elif "category" in template["id"] or "category" in placeholder:
                prop = self.find_property_by_name("has_course_category")
                if prop:
                    return prop
                
            elif "nickname" in template["id"] or "nickname" in placeholder:
                prop = self.find_property_by_name("also_known_as")
                if prop:
                    return prop
        
        # If we don't have the property in schema info, use our predefined ones
        if "credit" in template["id"] or "credit" in placeholder:
            return university_properties["credits"]
            
        elif "prerequisite" in template["id"] or "prerequisite" in placeholder:
            return university_properties["prerequisite"]
            
        elif "code" in template["id"] or "code" in placeholder:
            return university_properties["code"]
            
        elif "evaluation" in template["id"] or "evaluation" in placeholder:
            return university_properties["evaluation"]
            
        elif "research" in template["id"] or "research" in placeholder:
            return university_properties["research"]
            
        elif "category" in template["id"] or "category" in placeholder:
            return university_properties["category"]
            
        elif "nickname" in template["id"] or "nickname" in placeholder:
            return university_properties["nickname"]
            
        # Fallback to any property if we can't find a specific match
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return random.choice(self.schema_info["properties"])
            
        # Last resort - return credits as default
        return university_properties["credits"]

    def select_credit_value(self):
        """
        Select a realistic credit value for university courses
        
        Returns:
            dict: Credit value object
        """
        credit_values = [1, 2, 3, 4, 6]  # Common credit values in university courses
        value = random.choice(credit_values)
        return {"value": str(value), "label": str(value)}

    def select_random_value(self, template):
        """
        Select a random appropriate value - MODIFIED FOR UNIVERSITY DATA
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Special handling for university course data
        if template.get("category") == "university":
            if "credit" in template["id"]:
                return self.select_credit_value()
            
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
        writer.writerow(['id', 'question', 'sparql', 'category', 'complexity', 'templateId'])
        
        # Write rows
        for item in dataset:
            sparql_escaped = item["sparql"].replace("\n", " ")
            writer.writerow([
                item["id"],
                item["question"],
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
    
    def generate_variations(self, question, category, count=3):
        """
        Generate variations of a question
        
        Args:
            question (str): Original question
            category (str): Question category
            count (int): Number of variations to generate
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # Add university-specific variations
        if category == "university":
            variations.extend(self.get_university_variations(question))
        
        # Add general variations
        variations.extend(self.get_general_variations(question))
        
        # Ensure we don't have duplicate variations
        unique_variations = list(set(variations))
        
        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[:min(count, len(unique_variations))]

    def get_university_variations(self, question):
        """
        Get variations specific to university course questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # "How many credits" variations
        if question.startswith("How many credits"):
            variations.append(question.replace("How many credits", "What is the credit value"))
            variations.append(question.replace("How many credits", "What number of credits"))
            variations.append("Could you tell me " + question.lower())
        
        # "What is the course code" variations
        elif question.startswith("What is the course code"):
            variations.append(question.replace("What is the course code", "What's the course code"))
            variations.append(question.replace("What is the course code", "What code is assigned"))
            variations.append("I need to know " + question.lower().replace("?", "."))
        
        # "What category" variations
        elif "category" in question.lower():
            variations.append(question.replace("What category", "Which category"))
            variations.append(question.replace("does", "is").replace("belong to", "in"))
        
        # "What are the prerequisites" variations
        elif "prerequisites" in question.lower():
            variations.append(question.replace("What are the prerequisites", "Which courses are prerequisites"))
            variations.append(question.replace("What are the prerequisites", "What courses do I need to take before"))
            variations.append(question.replace("What are the prerequisites", "What prior courses are required for"))
        
        # "What evaluation methods" variations
        elif "evaluation methods" in question.lower():
            variations.append(question.replace("What evaluation methods", "How is"))
            variations.append(question.replace("What evaluation methods are used for", "How do they evaluate"))
            variations.append(question.replace("What evaluation methods", "What assessment methods"))
        
        # "Which research group" variations
        elif "research group" in question.lower():
            variations.append(question.replace("Which research group is", "What research group is"))
            variations.append(question.replace("is associated with", "conducts research on"))
        
        # "Which courses" variations
        elif question.startswith("Which courses"):
            variations.append(question.replace("Which courses", "What courses"))
            variations.append("Can you list " + question.lower())
            variations.append("I'd like to know " + question.lower().replace("?", "."))
        
        return variations

    def get_general_variations(self, question):
        """
        Get general variations that apply to any question
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # Add please
        if question.endswith('?'):
            variations.append(question.replace('?', ' please?'))
        
        # Do you know...
        variations.append(f"Do you know {question.lower()}")
        
        # Can you find/tell...
        if question.startswith('What') or question.startswith('Which'):
            variations.append(f"Can you tell me {question.lower()}")
        
        return variations