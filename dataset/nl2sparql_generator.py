"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator

This tool creates pairs of natural language questions and corresponding SPARQL queries
for any knowledge graph by using templates and entity instantiation.

Usage example:

# Configure with KG schema information
config = {
    "prefixes": {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
        'dbo': 'http://dbpedia.org/ontology/',
        'dbr': 'http://dbpedia.org/resource/',
        'xsd': 'http://www.w3.org/2001/XMLSchema#'
    },
    "entityExamples": [
        {"value": "dbr:Berlin", "label": "Berlin", "uri": "http://dbpedia.org/resource/Berlin"},
        {"value": "dbr:Paris", "label": "Paris", "uri": "http://dbpedia.org/resource/Paris"},
        {"value": "dbr:Leonardo_da_Vinci", "label": "Leonardo da Vinci", "uri": "http://dbpedia.org/resource/Leonardo_da_Vinci"}
    ],
    "schemaInfo": {
        "properties": [
            {"value": "dbo:capital", "label": "capital", "uri": "http://dbpedia.org/ontology/capital"},
            {"value": "dbo:populationTotal", "label": "population", "uri": "http://dbpedia.org/ontology/populationTotal"}
        ],
        "types": [
            {"value": "dbo:City", "label": "City", "uri": "http://dbpedia.org/ontology/City"},
            {"value": "dbo:Country", "label": "Country", "uri": "http://dbpedia.org/ontology/Country"}
        ],
        "numericProperties": [
            {"value": "dbo:populationTotal", "label": "population", "uri": "http://dbpedia.org/ontology/populationTotal"}
        ],
        "dateProperties": [
            {"value": "dbo:foundingDate", "label": "founding date", "uri": "http://dbpedia.org/ontology/foundingDate"}
        ]
    }
}

generator = NL2SPARQLGenerator(config)

# Generate a dataset with 100 question-query pairs
dataset = generator.generate_dataset(
    size=100,
    complexity_distribution={"basic": 0.5, "intermediate": 0.3, "advanced": 0.15, "expert": 0.05},
    include_variations=True,
    variations_per_question=2
)

# Export to JSON
json_output = generator.export_json(dataset)

# Export to CSV
csv_output = generator.export_csv(dataset)
"""

import json
import random
import re
import datetime
import csv
import io

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs."""
    
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

    def initialize_templates(self):
        """
        Initialize question-query template pairs for different complexity levels
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # Basic templates that work with most knowledge graphs
        basic_templates = [
            # Simple entity retrieval templates
            {
                "id": "simple-property",
                "category": "simple",
                "questionTemplate": "What is the {property} of {entity}?",
                "sparqlTemplate": """
                    SELECT ?value WHERE {
                      {entity} {property} ?value .
                    }
                """,
                "complexity": "basic",
                "applicableProperties": ["name", "label", "title", "description"]
            },
            {
                "id": "simple-inverse-property",
                "category": "simple",
                "questionTemplate": "Which {subjectType} has {property} {value}?",
                "sparqlTemplate": """
                    SELECT ?entity WHERE {
                      ?entity a {subjectType} .
                      ?entity {property} {value} .
                    }
                """,
                "complexity": "basic"
            },
            
            # Logical reasoning templates
            {
                "id": "logical-and",
                "category": "logical",
                "questionTemplate": "Which {objectType} are both {property1} of {entity1} and {property2} of {entity2}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?obj WHERE {
                      {entity1} {property1} ?obj .
                      {entity2} {property2} ?obj .
                      ?obj a {objectType} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "logical-or",
                "category": "logical",
                "questionTemplate": "Which {objectType} are either {property1} of {entity1} or {property2} of {entity2}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?obj WHERE {
                      {
                        {entity1} {property1} ?obj .
                      } UNION {
                        {entity2} {property2} ?obj .
                      }
                      ?obj a {objectType} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "logical-not",
                "category": "logical",
                "questionTemplate": "Which {objectType} are {property1} of {entity1} but not {property2} of {entity2}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?obj WHERE {
                      {entity1} {property1} ?obj .
                      ?obj a {objectType} .
                      FILTER NOT EXISTS {
                        {entity2} {property2} ?obj .
                      }
                    }
                """,
                "complexity": "intermediate"
            },
            
            # Quantitative templates
            {
                "id": "count-simple",
                "category": "quantitative",
                "questionTemplate": "How many {objectType} are {property} of {entity}?",
                "sparqlTemplate": """
                    SELECT (COUNT(DISTINCT ?obj) AS ?count) WHERE {
                      {entity} {property} ?obj .
                      ?obj a {objectType} .
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "count-complex",
                "category": "quantitative",
                "questionTemplate": "How many {objectType} are both {property1} of {entity1} and {property2} of {entity2}?",
                "sparqlTemplate": """
                    SELECT (COUNT(DISTINCT ?obj) AS ?count) WHERE {
                      {entity1} {property1} ?obj .
                      {entity2} {property2} ?obj .
                      ?obj a {objectType} .
                    }
                """,
                "complexity": "advanced"
            },
            
            # Comparative templates
            {
                "id": "superlative-max",
                "category": "comparative",
                "questionTemplate": "Which {subjectType} has the highest {numericProperty}?",
                "sparqlTemplate": """
                    SELECT ?entity (MAX(?value) AS ?maxValue) WHERE {
                      ?entity a {subjectType} .
                      ?entity {numericProperty} ?value .
                    }
                    ORDER BY DESC(?maxValue)
                    LIMIT 1
                """,
                "complexity": "advanced",
                "requiresNumericProperty": True
            },
            {
                "id": "superlative-min",
                "category": "comparative",
                "questionTemplate": "Which {subjectType} has the lowest {numericProperty}?",
                "sparqlTemplate": """
                    SELECT ?entity (MIN(?value) AS ?minValue) WHERE {
                      ?entity a {subjectType} .
                      ?entity {numericProperty} ?value .
                    }
                    ORDER BY ASC(?minValue)
                    LIMIT 1
                """,
                "complexity": "advanced",
                "requiresNumericProperty": True
            },
            {
                "id": "comparative-greater-than",
                "category": "comparative",
                "questionTemplate": "Which {subjectType} have {numericProperty} greater than {value}?",
                "sparqlTemplate": """
                    SELECT ?entity ?value WHERE {
                      ?entity a {subjectType} .
                      ?entity {numericProperty} ?value .
                      FILTER(?value > {value})
                    }
                    ORDER BY DESC(?value)
                """,
                "complexity": "advanced",
                "requiresNumericProperty": True
            },
            
            # Filter templates
            {
                "id": "filter-date",
                "category": "filter",
                "questionTemplate": "Which {subjectType} were {dateProperty} after {date}?",
                "sparqlTemplate": """
                    SELECT ?entity ?date WHERE {
                      ?entity a {subjectType} .
                      ?entity {dateProperty} ?date .
                      FILTER(?date > "{date}"^^xsd:dateTime)
                    }
                    ORDER BY ?date
                """,
                "complexity": "advanced",
                "requiresDateProperty": True
            },
            {
                "id": "filter-text",
                "category": "filter",
                "questionTemplate": "Which {subjectType} have {textProperty} containing the word '{text}'?",
                "sparqlTemplate": """
                    SELECT ?entity ?text WHERE {
                      ?entity a {subjectType} .
                      ?entity {textProperty} ?text .
                      FILTER(CONTAINS(LCASE(?text), LCASE("{text}")))
                    }
                """,
                "complexity": "advanced"
            },
            
            # Path templates
            {
                "id": "path-two-hop",
                "category": "path",
                "questionTemplate": "What are the {property2} of the {property1} of {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?final WHERE {
                      {entity} {property1} ?intermediate .
                      ?intermediate {property2} ?final .
                    }
                """,
                "complexity": "advanced"
            },
            {
                "id": "path-three-hop",
                "category": "path",
                "questionTemplate": "What are the {property3} of the {property2} of the {property1} of {entity}?",
                "sparqlTemplate": """
                    SELECT DISTINCT ?final WHERE {
                      {entity} {property1} ?intermediate1 .
                      ?intermediate1 {property2} ?intermediate2 .
                      ?intermediate2 {property3} ?final .
                    }
                """,
                "complexity": "expert"
            }
        ]
        
        # Merge with any custom templates provided in config
        return basic_templates + self.config.get("customTemplates", [])

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True,
                        variations_per_question=3, validate_queries=False):
        """
        Generate dataset based on knowledge graph schema
        
        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            variations_per_question (int): Number of variations per question
            validate_queries (bool): Whether to validate SPARQL queries
            
        Returns:
            list: Array of question-query pairs
        """
        if complexity_distribution is None:
            complexity_distribution = {
                "basic": 0.5,
                "intermediate": 0.3,
                "advanced": 0.15,
                "expert": 0.05
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
        question = template["questionTemplate"]
        sparql = template["sparqlTemplate"]
        
        # Add prefixes to SPARQL query
        prefix_string = ""
        for prefix, uri in self.prefixes.items():
            prefix_string += f"PREFIX {prefix}: <{uri}>\n"
        
        sparql = prefix_string + sparql
        
        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            pattern = "{" + placeholder + "}"
            question = question.replace(pattern, replacement.get("label", replacement.get("value", "")))
            
            # For SPARQL, use the URI or full representation
            if "uri" in replacement:
                sparql = sparql.replace(pattern, f"<{replacement['uri']}>")
            elif "sparqlValue" in replacement:
                sparql = sparql.replace(pattern, replacement["sparqlValue"])
            else:
                sparql = sparql.replace(pattern, replacement["value"])
        
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
        pattern = r"{([^}]+)}"
        
        # Search in question template
        for match in re.finditer(pattern, template["questionTemplate"]):
            placeholders.add(match.group(1))
        
        # Search in SPARQL template
        for match in re.finditer(pattern, template["sparqlTemplate"]):
            placeholders.add(match.group(1))
        
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
            if placeholder.startswith("entity"):
                replacement = self.select_random_entity()
            
            # Handle property placeholders
            elif placeholder.startswith("property"):
                replacement = self.select_random_property(template, placeholder)
            
            # Handle type placeholders
            elif placeholder.endswith("Type"):
                replacement = self.select_random_type(placeholder)
            
            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                replacement = self.select_random_value(template)
            
            # Handle date placeholders
            elif placeholder == "date" or placeholder.endswith("Date"):
                replacement = self.generate_random_date()
            
            # Handle text placeholder
            elif placeholder == "text":
                term = self.generate_random_search_term()
                replacement = {"value": term, "label": term}
            
            # Handle numeric placeholders
            elif placeholder.startswith("numeric") or placeholder.endswith("Number"):
                num = random.randint(0, 100)
                replacement = {"value": str(num), "label": str(num)}
            
            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None
            
            replacements[placeholder] = replacement
        
        return replacements

    def select_random_entity(self):
        """
        Select a random entity from available examples
        
        Returns:
            dict: Selected entity
        """
        if not self.entity_examples:
            return self.generate_dummy_entity()
        
        return random.choice(self.entity_examples)

    def select_random_property(self, template, placeholder):
        """
        Select a random property appropriate for the template
        
        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name
            
        Returns:
            dict: Selected property
        """
        # Check if template has specific applicable properties for this placeholder
        prop_key = f"applicable{placeholder[0].upper()}{placeholder[1:]}s"
        
        if prop_key in template and template[prop_key]:
            property_name = random.choice(template[prop_key])
            result = self.find_property_by_name(property_name)
            if result:
                return result
            return self.generate_dummy_property(property_name)
        
        # Check if we have numeric, date, or text property requirements
        if placeholder.startswith("numeric") and "numericProperties" in self.schema_info:
            return self.select_random_from_array(self.schema_info["numericProperties"])
        
        if placeholder.startswith("date") and "dateProperties" in self.schema_info:
            return self.select_random_from_array(self.schema_info["dateProperties"])
        
        if placeholder.startswith("text") and "textProperties" in self.schema_info:
            return self.select_random_from_array(self.schema_info["textProperties"])
        
        # Fall back to general properties
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return self.select_random_from_array(self.schema_info["properties"])
        
        # Generate a dummy property if nothing else available
        return self.generate_dummy_property()

    def select_random_type(self, placeholder):
        """
        Select a random entity type
        
        Args:
            placeholder (str): The type placeholder
            
        Returns:
            dict: Selected type
        """
        if "types" in self.schema_info and self.schema_info["types"]:
            return self.select_random_from_array(self.schema_info["types"])
        
        # Generate dummy types with appropriate labels
        type_mappings = {
            'subjectType': ['Person', 'Organization', 'Place', 'Event'],
            'objectType': ['Book', 'Movie', 'Product', 'Artwork'],
            'entityType': ['Entity', 'Thing', 'Object', 'Item']
        }
        
        # Find the best match from mappings
        for type_key, options in type_mappings.items():
            if type_key in placeholder:
                label = random.choice(options)
                return {
                    "value": label.lower(),
                    "label": label,
                    "uri": f"http://example.org/ontology/{label}",
                    "sparqlValue": f"<http://example.org/ontology/{label}>"
                }
        
        # Default dummy type
        return {
            "value": "thing",
            "label": "Thing",
            "uri": "http://example.org/ontology/Thing",
            "sparqlValue": "<http://example.org/ontology/Thing>"
        }

    def select_random_value(self, template):
        """
        Select a random appropriate value
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Generate different kinds of values based on template category
        if template.get("requiresNumericProperty", False):
            value = random.randint(0, 1000)
            return {"value": str(value), "label": str(value)}
        
        if template.get("requiresDateProperty", False):
            return self.generate_random_date()
        
        # Default to a string value
        options = ['name', 'title', 'description', 'identifier', 'location']
        value = random.choice(options)
        return {"value": f'"{value}"', "label": value}

    def generate_random_date(self):
        """
        Generate a random date
        
        Returns:
            dict: Generated date
        """
        year = 2000 + random.randint(0, 20)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        
        date_str = f"{year}-{month:02d}-{day:02d}"
        return {
            "value": date_str,
            "label": date_str,
            "sparqlValue": f'"{date_str}"^^xsd:date'
        }

    def generate_random_search_term(self):
        """
        Generate a random search term
        
        Returns:
            str: Generated search term
        """
        terms = ['science', 'art', 'technology', 'history', 'music', 'politics', 'nature']
        return random.choice(terms)

    def generate_dummy_entity(self):
        """
        Generate a dummy entity when no examples are available
        
        Returns:
            dict: Generated entity
        """
        entities = [
            {"value": "dbr:Albert_Einstein", "label": "Albert Einstein", "uri": "http://dbpedia.org/resource/Albert_Einstein"},
            {"value": "dbr:New_York_City", "label": "New York City", "uri": "http://dbpedia.org/resource/New_York_City"},
            {"value": "dbr:Google", "label": "Google", "uri": "http://dbpedia.org/resource/Google"},
            {"value": "dbr:The_Beatles", "label": "The Beatles", "uri": "http://dbpedia.org/resource/The_Beatles"},
            {"value": "dbr:World_War_II", "label": "World War II", "uri": "http://dbpedia.org/resource/World_War_II"}
        ]
        
        return random.choice(entities)

    def generate_dummy_property(self, name=None):
        """
        Generate a dummy property
        
        Args:
            name (str, optional): Optional property name
            
        Returns:
            dict: Generated property
        """
        properties = [
            {"value": "dbo:birthPlace", "label": "birth place", "uri": "http://dbpedia.org/ontology/birthPlace"},
            {"value": "dbo:director", "label": "director", "uri": "http://dbpedia.org/ontology/director"},
            {"value": "dbo:author", "label": "author", "uri": "http://dbpedia.org/ontology/author"},
            {"value": "dbo:country", "label": "country", "uri": "http://dbpedia.org/ontology/country"},
            {"value": "dbo:populationTotal", "label": "population", "uri": "http://dbpedia.org/ontology/populationTotal"}
        ]
        
        if name:
            # Convert camelCase to space separated
            label = re.sub(r'([A-Z])', r' \1', name).strip().lower()
            return {
                "value": f"dbo:{name}",
                "label": label,
                "uri": f"http://dbpedia.org/ontology/{name}"
            }
        
        return random.choice(properties)

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
            if prop["value"] == name or prop["label"].lower() == name.lower():
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
        Format SPARQL query for readability
        
        Args:
            sparql (str): Raw SPARQL query
            
        Returns:
            str: Formatted SPARQL query
        """
        # Replace multiple spaces with a single space
        sparql = re.sub(r'\s+', ' ', sparql)
        
        # Format dots
        sparql = re.sub(r'\s*\.\s*', ' . ', sparql)
        
        # Format braces
        sparql = re.sub(r'\s*{\s*', ' { ', sparql)
        sparql = re.sub(r'\s*}\s*', ' } ', sparql)
        
        # Format keywords
        sparql = re.sub(r'\s*SELECT', 'SELECT', sparql)
        sparql = re.sub(r'\s*WHERE', '\nWHERE', sparql)
        sparql = re.sub(r'\s*FILTER', '\n  FILTER', sparql)
        sparql = re.sub(r'\s*ORDER BY', '\nORDER BY', sparql)
        sparql = re.sub(r'\s*LIMIT', '\nLIMIT', sparql)
        sparql = re.sub(r'\s*GROUP BY', '\nGROUP BY', sparql)
        sparql = re.sub(r'\s*HAVING', '\nHAVING', sparql)
        
        return sparql.strip()

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
        
        # Add standard variations based on category
        category_variations = self.get_category_variations(question, category)
        variations.extend(category_variations)
        
        # Add general variations
        variations.extend(self.get_general_variations(question))
        
        # Ensure we don't have duplicate variations
        unique_variations = list(set(variations))
        
        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[:min(count, len(unique_variations))]

    def get_category_variations(self, question, category):
        """
        Get category-specific variations
        
        Args:
            question (str): Original question
            category (str): Question category
            
        Returns:
            list: Array of variation strings
        """
        variation_methods = {
            'simple': self.get_simple_variations,
            'logical': self.get_logical_variations,
            'quantitative': self.get_quantitative_variations,
            'comparative': self.get_comparative_variations,
            'filter': self.get_filter_variations,
            'path': self.get_path_variations
        }
        
        if category in variation_methods:
            return variation_methods[category](question)
        
        return []

    def get_simple_variations(self, question):
        """
        Get variations for simple questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # What is -> What's
        variations.append(question.replace('What is', "What's"))
        
        # Adding "Can you tell me"
        if question.startswith('What'):
            variations.append(f"Can you tell me {question.lower()}")
        
        # Adding "I want to know"
        variations.append(f"I want to know {question.lower().replace('?', '.')}")
        
        return variations

    def get_logical_variations(self, question):
        """
        Get variations for logical questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # Replace "which" with "what"
        variations.append(re.sub(r'Which', 'What', question, flags=re.IGNORECASE))
        
        # Add "Could you list"
        if question.startswith('Which'):
            variations.append(f"Could you list {question.lower()}")
        
        return variations

    def get_quantitative_variations(self, question):
        """
        Get variations for quantitative questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # How many -> What is the number of
        variations.append(question.replace('How many', 'What is the number of'))
        
        # How many -> Count the
        variations.append(question.replace('How many', 'Count the'))
        
        return variations

    def get_comparative_variations(self, question):
        """
        Get variations for comparative questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # Which X has the highest -> What is the X with the highest
        variations.append(re.sub(r'Which (.*?) has the highest', r'What is the \1 with the highest', question, flags=re.IGNORECASE))
        
        # Which X has the lowest -> What is the X with the lowest
        variations.append(re.sub(r'Which (.*?) has the lowest', r'What is the \1 with the lowest', question, flags=re.IGNORECASE))
        
        return variations

    def get_filter_variations(self, question):
        """
        Get variations for filter questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # Which -> List all
        variations.append(re.sub(r'Which', 'List all', question, flags=re.IGNORECASE))
        
        # Which -> Give me
        variations.append(re.sub(r'Which', 'Give me all', question, flags=re.IGNORECASE))
        
        return variations

    def get_path_variations(self, question):
        """
        Get variations for path questions
        
        Args:
            question (str): Original question
            
        Returns:
            list: Array of variation strings
        """
        variations = []
        
        # What are -> Show me
        variations.append(re.sub(r'What are', 'Show me', question, flags=re.IGNORECASE))
        
        # What are -> List
        variations.append(re.sub(r'What are', 'List', question, flags=re.IGNORECASE))
        
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
        
        # Can you find...
        if question.startswith('What') or question.startswith('Which'):
            variations.append(f"Can you find {question.lower()}")
        
        return variations