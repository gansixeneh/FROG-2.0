"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Enhanced for University Course Data

This version supports complex query patterns with multi-condition filters, multi-hop relationships,
and advanced aggregation, while maintaining context-aware entity selection for meaningful queries.
"""

import json
import random
import re
import datetime
import csv
import io
import os
from rdflib import Graph, Namespace, URIRef, Literal

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for university courses."""
    
    def __init__(self, config, graph=None):
        """
        Initialize the generator with knowledge graph schema information
        
        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            graph (rdflib.Graph, optional): RDF graph for context-aware entity selection
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()
        
        # Store the RDF graph for context-aware entity selection
        self.graph = graph
        
        # Create namespace bindings if we have a graph
        if self.graph:
            # Add standard namespaces
            for prefix, uri in self.prefixes.items():
                ns = Namespace(uri)
                self.graph.bind(prefix, ns)

    def initialize_templates(self):
        """
        Initialize question-query template pairs for university course data with enhanced complexity
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # Basic course information templates - retained from original
        basic_templates = [
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
        ]
        
        # Intermediate templates - retained and expanded
        intermediate_templates = [
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
                "id": "count-evaluation-methods",
                "category": "university",
                "questionTemplate": "How many evaluation methods are associated with {entity}?",
                "sparqlTemplate": """
                    SELECT (COUNT(?method) AS ?count) WHERE {
                      {entity} ns1:has_evaluation_method ?method .
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
            {
                "id": "courses-by-prerequisite",
                "category": "university",
                "questionTemplate": "What courses have {entity} as a prerequisite course?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course {entity} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "count-courses-by-prerequisite",
                "category": "university",
                "questionTemplate": "How many courses have {entity} as a prerequisite course?",
                "sparqlTemplate": """
                    SELECT (COUNT(?course) AS ?count) WHERE {
                      ?course ns1:has_prerequisite_course {entity} .
                    }
                """,
                "complexity": "intermediate"
            },
        ]
        
        # Advanced templates - original ones
        original_advanced_templates = [
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
            },
        ]
        
        # NEW TEMPLATES - Enhanced advanced templates matching the test dataset patterns
        enhanced_advanced_templates = [
            # Multi-condition queries (3+ properties)
            {
                "id": "courses-with-triple-condition",
                "category": "university",
                "questionTemplate": "What courses have {entity1} as their research group, are categorized as {entity2}, and use {entity3} as their evaluation method?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_research_group {entity1} .
                      ?course ns1:has_course_category {entity2} .
                      ?course ns1:has_evaluation_method {entity3} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-triple-condition-code",
                "category": "university",
                "questionTemplate": "What course has the evaluation method of {entity1} and is a {entity2} with the course code '{value}'?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_course_category {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-double-evaluation-code",
                "category": "university",
                "questionTemplate": "What courses have '{entity1}' and '{entity2}' as evaluation methods and have the course code '{value}'?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_evaluation_method {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-research-eval-code",
                "category": "university",
                "questionTemplate": "What courses have the evaluation method '{entity1}' and are associated with the research group '{entity2}' and have the course code '{value}'?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_research_group {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prereq-eval-category",
                "category": "university",
                "questionTemplate": "What courses have {entity1} as a prerequisite and {entity2} as an evaluation method, and are {entity3}?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course {entity1} .
                      ?course ns1:has_evaluation_method {entity2} .
                      ?course ns1:has_course_category {entity3} .
                    }
                """,
                "complexity": "advanced"
            },
            
            # Multi-hop relationship queries
            {
                "id": "courses-with-prerequisite-eval",
                "category": "university",
                "questionTemplate": "What courses have prerequisites that have {entity} as their evaluation method?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_evaluation_method {entity} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prerequisite-category",
                "category": "university",
                "questionTemplate": "What courses have prerequisites with {entity} as their category?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_course_category {entity} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prerequisite-credits",
                "category": "university",
                "questionTemplate": "What courses have prerequisites with {value} credits?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_credits {value} .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prereq-of-prereq",
                "category": "university", 
                "questionTemplate": "What courses have prerequisites with {entity} as their prerequisites?",
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_prerequisite_course {entity} .
                    }
                """,
                "complexity": "advanced"
            },
        ]
        
        # Combine all templates
        all_templates = basic_templates + intermediate_templates + original_advanced_templates + enhanced_advanced_templates
        
        return all_templates

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True,
                        variations_per_question=3, validate_queries=False, max_attempts_per_template=10):
        """
        Generate dataset based on university course knowledge graph
        
        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            variations_per_question (int): Number of variations per question
            validate_queries (bool): Whether to validate SPARQL queries
            max_attempts_per_template (int): Maximum number of attempts to instantiate a template
            
        Returns:
            list: Array of question-SPARQL pairs
        """
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.4,
                "intermediate": 0.3,
                "advanced": 0.3  # Increased proportion of advanced queries
            }
        
        dataset = []
        id_counter = 1
        
        # Calculate how many questions of each complexity to generate
        counts_by_complexity = {}
        for complexity, proportion in complexity_distribution.items():
            counts_by_complexity[complexity] = int(size * proportion)
        
        # Track problematic templates for reporting
        failed_templates = {}
        
        # Generate questions for each complexity level
        for complexity, count in counts_by_complexity.items():
            successful_generations = 0
            eligible_templates = [t for t in self.templates if t["complexity"] == complexity]
            
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            while successful_generations < count and len(dataset) < size:
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)
                
                # Track attempts for this template
                template_id = template["id"]
                attempts = 0
                
                # Try to instantiate this template up to max_attempts
                while attempts < max_attempts_per_template:
                    attempts += 1
                    try:
                        # Use the discovery-based approach to instantiate the template
                        instance = self.instantiate_template_with_discovery(template)
                        
                        if instance:
                            # Success! Add the question-query pair
                            dataset.append({
                                "id": f"q{id_counter}",
                                "question": instance["question"],
                                "sparql": instance["sparql"],
                                "category": template["category"],
                                "complexity": template["complexity"],
                                "templateId": template["id"]
                            })
                            id_counter += 1
                            successful_generations += 1
                            
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
                            
                            # Break out of the attempts loop
                            break
                    except Exception as e:
                        print(f"Error instantiating template {template['id']}: {e}")
                
                # If we've tried max_attempts and still failed, record this template as problematic
                if attempts >= max_attempts_per_template and template_id not in failed_templates:
                    failed_templates[template_id] = 0
                
                if template_id in failed_templates:
                    failed_templates[template_id] += 1
        
        # Report problematic templates
        if failed_templates:
            print("\nWarning: Some templates consistently failed to instantiate:")
            for template_id, count in failed_templates.items():
                print(f"  - {template_id}: failed {count} times")
        
        # Report complexity distribution achieved
        complexity_counts = {}
        for item in dataset:
            complexity = item["complexity"]
            if complexity not in complexity_counts:
                complexity_counts[complexity] = 0
            complexity_counts[complexity] += 1
        
        print("\nActual complexity distribution in generated dataset:")
        for complexity, count in complexity_counts.items():
            target = counts_by_complexity.get(complexity, 0)
            percentage = (count / len(dataset)) * 100 if dataset else 0
            print(f"  - {complexity}: {count}/{len(dataset)} ({percentage:.1f}%) [Target: {target}]")
        
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

    def instantiate_template_with_discovery(self, template):
        """
        Instantiate a template using a discovery-based approach
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        if not self.graph:
            # If we don't have a graph, fall back to the old method
            return self.instantiate_template(template)
            
        # Extract placeholders from the template
        placeholders = self.extract_placeholders(template)
        
        # Create a discovery query that will find valid values for all placeholders
        discovery_query = self.create_discovery_query(template, placeholders)
        
        # Execute the discovery query
        try:
            results = list(self.graph.query(discovery_query))
            
            if not results:
                print(f"No valid combinations found for template: {template['id']}")
                return None
                
            # Randomly select one result
            selected = random.choice(results)
            
            # Extract replacements for each placeholder
            replacements = {}
            for i, placeholder in enumerate(placeholders):
                # Skip the first value if it's a dummy result variable
                offset = 1 if "dummy_result" in discovery_query else 0
                
                value_index = i + offset
                if value_index >= len(selected):
                    print(f"Error: Not enough values in result for placeholder {placeholder}")
                    return None
                    
                value = selected[value_index]
                
                # Create replacement object based on placeholder type
                if placeholder.startswith('entity'):
                    # For entity placeholders, get URI and label
                    entity_uri = str(value)
                    
                    # Try to find a label from the result (look for <placeholder>Label)
                    label_index = -1
                    for j, var_name in enumerate(self.graph.query(discovery_query).vars):
                        if str(var_name) == f"{placeholder}Label":
                            label_index = j
                            break
                            
                    if label_index >= 0 and label_index < len(selected) and selected[label_index]:
                        entity_label = str(selected[label_index])
                    else:
                        # Extract label from URI if not found in result
                        entity_label = self.extract_label_from_uri(entity_uri)
                        
                    replacement = {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri
                    }
                elif placeholder == "value" or placeholder.endswith("Value"):
                    # For value placeholders
                    value_str = str(value)
                    
                    # Handle different value types appropriately
                    if "credits" in template["id"] or "credits" in template["questionTemplate"].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                    elif "code" in template["id"] or "code" in template["questionTemplate"].lower():
                        replacement = {
                            "value": f'"{value_str}"',  # Include quotes for string literal
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"'
                        }
                    else:
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                else:
                    # For other placeholders, use as is
                    replacement = {
                        "value": str(value),
                        "label": str(value)
                    }
                    
                replacements[placeholder] = replacement
            
            # Apply replacements to the question template
            question = template["questionTemplate"].strip()
            sparql = template["sparqlTemplate"].strip()
            
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
            
        except Exception as e:
            print(f"Error executing discovery query for template {template['id']}: {e}")
            return None

    def create_discovery_query(self, template, placeholders):
        """
        Create a discovery query that finds valid values for all placeholders
        
        Args:
            template (dict): The template to convert
            placeholders (set): Set of placeholders in the template
            
        Returns:
            str: The discovery query
        """
        sparql_template = template["sparqlTemplate"].strip()
        
        # Extract the WHERE clause from the template
        where_match = re.search(r'WHERE\s*{(.*)}', sparql_template, re.DOTALL | re.IGNORECASE)
        if not where_match:
            print(f"Error: Could not extract WHERE clause from template: {template['id']}")
            return None
            
        where_clause = where_match.group(1).strip()
        
        # Replace placeholders with variables in the WHERE clause
        for placeholder in placeholders:
            pattern = r'{[\s]*' + re.escape(placeholder) + r'[\s]*}'
            var_name = placeholder
            where_clause = re.sub(pattern, f"?{var_name}", where_clause)
        
        # Build SELECT clause with all placeholder variables
        select_clause = "SELECT DISTINCT"
        
        # Add result variable from original query if it exists
        # This helps with aggregation queries
        result_var_match = re.search(r'SELECT\s+(?:\(.*\)\s+AS\s+)?(\?\w+)', sparql_template, re.IGNORECASE)
        if result_var_match:
            result_var = result_var_match.group(1)
            if "COUNT" not in result_var and "count" not in result_var:
                select_clause += f" {result_var}"
            else:
                # For COUNT queries, add a dummy result variable
                select_clause += " ?dummy_result"
        
        # Add all placeholder variables to SELECT clause
        for placeholder in placeholders:
            select_clause += f" ?{placeholder}"
            # For entity placeholders, also select label if available
            if placeholder.startswith('entity'):
                select_clause += f" ?{placeholder}Label"
        
        # Construct the complete discovery query
        discovery_query = f"{select_clause} WHERE {{ {where_clause}"
        
        # Add OPTIONAL label patterns for entity placeholders
        for placeholder in placeholders:
            if placeholder.startswith('entity'):
                discovery_query += f" OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label . }}"
        
        # Close the query
        discovery_query += " } LIMIT 100"
        
        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            discovery_query = re.sub(pattern, r'<' + uri + r'\1>', discovery_query)
        
        return discovery_query

    def instantiate_template(self, template):
        """
        Original method to instantiate a template with specific entities and properties
        Kept as a fallback method
        
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
            
            # Handle entity placeholders
            if placeholder.startswith('entity'):
                # If we have a graph, try to find entities that fit the template
                if self.graph:
                    # For placeholder that are numbered (entity1, entity2), we need to
                    # extract the pattern based on the placeholder name
                    placeholder_number = None
                    if placeholder != "entity":
                        match = re.match(r'entity(\d+)', placeholder)
                        if match:
                            placeholder_number = int(match.group(1))
                    
                    replacement = self.select_entity_from_graph(template, placeholder_number)
                
                # If we didn't get a replacement from the graph, try pattern-based selection
                if not replacement:
                    if "research-group" in template["id"] or placeholder == "entity1" and "research" in template["questionTemplate"].lower():
                        replacement = self.select_entity_by_type("ns1:research_lab")
                    elif "evaluation" in template["id"] or placeholder in ["entity1", "entity2", "entity3"] and "evaluation" in template["questionTemplate"].lower():
                        replacement = self.select_entity_by_type("ns1:evaluation")
                    elif "category" in template["id"] or placeholder in ["entity2", "entity3"] and "categor" in template["questionTemplate"].lower():
                        replacement = self.select_entity_by_type("ns1:course_category")
                    else:
                        # Default to course entities
                        replacement = self.select_entity_by_type("ns1:course")
                
                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()
            
            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                # If we have a graph, try to find values that fit the template
                if self.graph:
                    replacement = self.select_value_from_graph(template, placeholder)
                
                # If we didn't get a replacement from the graph, use predefined values
                if not replacement:
                    if "credits" in template["id"] or "credits" in template["questionTemplate"].lower():
                        # For credit-related templates, use realistic credit values
                        replacement = self.select_credit_value()
                    elif "code" in template["id"] or "code" in template["questionTemplate"].lower():
                        # For course code, use realistic course code format
                        replacement = self.select_course_code_value()
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

    def select_entity_from_graph(self, template, placeholder_number=None):
        """
        Select an entity from the RDF graph that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            placeholder_number (int, optional): If provided, specifically look for entityN pattern
            
        Returns:
            dict: Selected entity info or None if not found
        """
        if not self.graph:
            return None
        
        sparql_template = template["sparqlTemplate"]
        entity_placeholder = "entity" if placeholder_number is None else f"entity{placeholder_number}"
        
        # Extract the predicate pattern for the entity
        # Look for patterns like: {entity} predicate ?object or {entityN} predicate ?object
        pattern_str = r'{' + entity_placeholder + r'}\s+([^\s.{}<>]+)\s+'
        predicate_match = re.search(pattern_str, sparql_template)
        
        if not predicate_match:
            # Try the alternative pattern: ?subject predicate {entity} or ?subject predicate {entityN}
            pattern_str = r'([^\s.{}<>]+)\s+{' + entity_placeholder + r'}'
            predicate_match = re.search(pattern_str, sparql_template)
            if predicate_match:
                # This is a reverse relationship
                return self.select_entity_for_reverse_pattern(predicate_match.group(1), template, placeholder_number)
        
        if not predicate_match:
            return None
            
        predicate = predicate_match.group(1)
        
        # Handle prefixed predicates
        if ':' in predicate:
            prefix, local_name = predicate.split(':', 1)
            if prefix in self.prefixes:
                predicate_uri = f"{self.prefixes[prefix]}{local_name}"
            else:
                # Unknown prefix, can't construct URI
                return None
        else:
            # Not a prefixed name, use as is
            predicate_uri = predicate
            
        # Construct a query to find valid subjects for this predicate
        query = f"""
            SELECT DISTINCT ?entity ?label
            WHERE {{
                ?entity <{predicate_uri}> ?obj .
                OPTIONAL {{ ?entity rdfs:label ?label }}
            }}
            LIMIT 50
        """
        
        try:
            # Execute query against the graph
            results = list(self.graph.query(query))
            
            if not results:
                return None
                
            # Randomly select one entity from the results
            selected = random.choice(results)
            entity_uri = str(selected[0])
            
            # Get the label if available, otherwise use URI
            if len(selected) > 1 and selected[1]:
                entity_label = str(selected[1])
            else:
                # Try to get label through a separate query
                label_query = f"""
                    SELECT ?label 
                    WHERE {{ <{entity_uri}> rdfs:label ?label }}
                    LIMIT 1
                """
                label_results = list(self.graph.query(label_query))
                if label_results and label_results[0][0]:
                    entity_label = str(label_results[0][0])
                else:
                    entity_label = self.extract_label_from_uri(entity_uri)
                
            return {
                "value": self.shorten_uri(entity_uri),
                "label": entity_label,
                "uri": entity_uri
            }
            
        except Exception as e:
            print(f"Error selecting entity from graph: {e}")
            return None

    def select_entity_for_reverse_pattern(self, predicate, template, placeholder_number=None):
        """
        Select an entity for patterns like ?subject predicate {entity}
        
        Args:
            predicate (str): The predicate in the pattern
            template (dict): The template with the pattern
            placeholder_number (int, optional): If provided, specifically look for entityN pattern
            
        Returns:
            dict: Selected entity info or None
        """
        # Similar to select_entity_from_graph but for reverse patterns
        if not self.graph:
            return None
            
        # Handle prefixed predicates
        if ':' in predicate:
            prefix, local_name = predicate.split(':', 1)
            if prefix in self.prefixes:
                predicate_uri = f"{self.prefixes[prefix]}{local_name}"
            else:
                return None
        else:
            predicate_uri = predicate
        
        # Find objects that appear in triples with this predicate
        query = f"""
            SELECT DISTINCT ?entity ?label
            WHERE {{
                ?subject <{predicate_uri}> ?entity .
                OPTIONAL {{ ?entity rdfs:label ?label }}
            }}
            LIMIT 50
        """
        
        try:
            results = list(self.graph.query(query))
            if not results:
                return None
                
            selected = random.choice(results)
            entity_uri = str(selected[0])
            
            # Get label as before
            if len(selected) > 1 and selected[1]:
                entity_label = str(selected[1])
            else:
                entity_label = self.extract_label_from_uri(entity_uri)
                
            return {
                "value": self.shorten_uri(entity_uri),
                "label": entity_label,
                "uri": entity_uri
            }
        except Exception as e:
            print(f"Error selecting entity for reverse pattern: {e}")
            return None

    def select_value_from_graph(self, template, placeholder):
        """
        Select a value from the RDF graph that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            placeholder (str): The name of the placeholder
            
        Returns:
            dict: Selected value info or None if not found
        """
        if not self.graph:
            return None
            
        sparql_template = template["sparqlTemplate"]
        
        # Match the pattern where value is used in the SPARQL
        value_pattern = r'{' + placeholder + r'}'
        
        # University-specific value handling
        if "credits" in template["id"] or "credits" in template["questionTemplate"].lower():
            # For credit values, find actual credit values in the data
            query = """
                SELECT DISTINCT ?credits
                WHERE {
                    ?course <http://example.org/has_credits> ?credits .
                }
                ORDER BY ?credits
            """
            
            try:
                results = list(self.graph.query(query))
                if results:
                    # Pick a random credit value
                    credit_value = str(random.choice(results)[0])
                    return {
                        "value": credit_value,
                        "label": credit_value
                    }
            except Exception as e:
                print(f"Error querying for credit values: {e}")
                
        elif "code" in template["id"] or "code" in template["questionTemplate"].lower():
            # For course codes, find actual course codes in the data
            query = """
                SELECT DISTINCT ?code
                WHERE {
                    ?course <http://example.org/has_course_code> ?code .
                }
                LIMIT 50
            """
            
            try:
                results = list(self.graph.query(query))
                if results:
                    # Pick a random course code
                    code_value = str(random.choice(results)[0])
                    return {
                        "value": f'"{code_value}"',  # Include quotes for string literal
                        "label": code_value,
                        "sparqlValue": f'"{code_value}"'
                    }
            except Exception as e:
                print(f"Error querying for course codes: {e}")
        
        # For other value types, fall back to default handling
        return None

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
        Select a random entity from available examples
        
        Returns:
            dict: Selected entity
        """
        # If we have entity examples from the schema extractor, use them
        if self.entity_examples:
            return random.choice(self.entity_examples)
        
        # Fallback to predefined university course entities
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

    def select_course_code_value(self):
        """
        Select a realistic course code value
        
        Returns:
            dict: Course code object
        """
        prefixes = ["CSCE", "CSGE", "CSCM", "UIGE"]
        number = random.randint(600000, 699999)
        code = f"{random.choice(prefixes)}{number}"
        return {
            "value": f'"{code}"',  # Include quotes for string literal
            "label": code,
            "sparqlValue": f'"{code}"'
        }

    def select_random_value(self, template):
        """
        Select a random appropriate value
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Special handling for university course data
        if template.get("category") == "university":
            if "credit" in template["id"] or "credit" in template["questionTemplate"].lower():
                return self.select_credit_value()
            elif "code" in template["id"] or "code" in template["questionTemplate"].lower():
                return self.select_course_code_value()
            
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

    def extract_label_from_uri(self, uri):
        """
        Extract a human-readable label from a URI
        
        Args:
            uri (str): URI to extract label from
            
        Returns:
            str: Human-readable label
        """
        # Extract the last part of the URI
        last_part = uri.split('/')[-1].split('#')[-1]
        
        # University course specific handling
        if '_' in last_part:
            # Replace underscores with spaces
            with_spaces = last_part.replace('_', ' ')
            # Capitalize each word
            return ' '.join(word.capitalize() for word in with_spaces.split())
        else:
            # Convert camelCase to spaces
            return re.sub(r'([a-z])([A-Z])', r'\1 \2', last_part)

    def shorten_uri(self, uri):
        """
        Shorten a URI using known prefixes
        
        Args:
            uri (str): URI to shorten
            
        Returns:
            str: Shortened URI
        """
        for prefix, namespace in self.prefixes.items():
            if uri.startswith(namespace):
                return f"{prefix}:{uri[len(namespace):]}"
        
        return uri

    def format_sparql(self, sparql):
        """
        Format SPARQL query for readability with properly formatted URIs
        
        Args:
            sparql (str): Raw SPARQL query
            
        Returns:
            str: Formatted SPARQL query
        """
        # First, clean URIs by removing spaces within angle brackets
        def clean_uri(match):
            uri = match.group(0)
            # Aggressively remove all spaces from URIs
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
            
        # "How many" variations
        elif question.startswith("How many"):
            variations.append(question.replace("How many", "What is the number of"))
            variations.append(question.replace("How many", "Count the"))
            variations.append("Could you count " + question[8:].lower())
            
        # Complex question variations
        elif "have" in question and "as" in question and len(question.split()) > 10:
            # For complex questions with multiple conditions
            variations.append("Find " + question.lower())
            variations.append("I need to know " + question.lower())
            variations.append("Please list " + question.lower())
        
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
            
        # I want to know
        variations.append(f"I want to know {question.lower().rstrip('?')}.")
        
        # I'm interested in
        variations.append(f"I'm interested in knowing {question.lower().rstrip('?')}.")
        
        return variations