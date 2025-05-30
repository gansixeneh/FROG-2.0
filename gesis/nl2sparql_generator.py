"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator for GESIS Knowledge Graph

This version generates query templates based on the GESIS Knowledge Graph schema,
focusing on scholarly resources, publications, and research data.
"""

import json
import random
import re
import datetime
import csv
import io
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import Counter
from kg_schema_extractor import gesis_entity_label

class SparqlExecutor:
    """A class to execute SPARQL queries against the Fuseki server."""
    
    def __init__(self, endpoint_url="http://localhost:3030/gesis/query"):
        """Initialize the SPARQL executor with the Fuseki endpoint."""
        self.endpoint = SPARQLWrapper(endpoint_url)
        self.endpoint.setReturnFormat(JSON)
    
    def execute_query(self, query, return_format="dict"):
        """
        Execute a SPARQL query and return results.
        
        Args:
            query (str): SPARQL query to execute
            return_format (str): Format to return results in ("dict", "raw", "pandas")
            
        Returns:
            Results in the specified format
        """
        # add rdfs prefix before query
        query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n" + query
        self.endpoint.setQuery(query)
        results = self.endpoint.query().convert()
        
        if return_format == "raw":
            return results
        
        # Extract bindings from SPARQL JSON results
        result_list = []
        if 'results' in results and 'bindings' in results['results']:
            for binding in results['results']['bindings']:
                row_dict = {}
                for var, value in binding.items():
                    if value['type'] == 'uri':
                        row_dict[var] = value['value']
                    elif value['type'] == 'literal':
                        row_dict[var] = value['value']
                    else:
                        row_dict[var] = value['value']
                result_list.append(row_dict)
        
        if return_format == "pandas":
            import pandas as pd
            if result_list:
                return pd.DataFrame(result_list)
            return pd.DataFrame()
            
        # Default to dict format
        return result_list

class VariationGenerator:
    """Generates variations of natural language questions"""
    
    def generate_variations(self, question, english_question, category, count=3):
        """
        Generate variations of a question
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English (duplicate for compatibility)
            category (str): Question category
            count (int): Number of variations to generate
            
        Returns:
            list: Array of variation dictionaries with different phrasings
        """
        variations = []
        
        # Add scholarly resource specific variations
        if category == "scholarly":
            variations.extend(self.get_scholarly_variations(question, english_question))
        
        # Add general variations
        variations.extend(self.get_general_variations(question, english_question))
        
        # Ensure we don't have duplicate variations
        unique_variations = []
        seen_questions = set()
        
        for var in variations:
            if var["text"] not in seen_questions:
                seen_questions.add(var["text"])
                unique_variations.append(var)
        
        # Return requested number of variations (or fewer if not enough generated)
        return unique_variations[:min(count, len(unique_variations))]

    def get_scholarly_variations(self, question, english_question):
        """
        Get variations specific to scholarly resource questions
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # "Who is the author of" variations
        if question.startswith("Who is the author of"):
            variations.append({
                "text": question.replace("Who is the author of", "Who wrote"),
                "english": english_question.replace("Who is the author of", "Who wrote")
            })
            variations.append({
                "text": question.replace("Who is the author of", "Who created"),
                "english": english_question.replace("Who is the author of", "Who created")
            })
        
        # "When was * published" variations
        elif question.startswith("When was") and "published" in question:
            variations.append({
                "text": question.replace("When was", "In what year was"),
                "english": english_question.replace("When was", "In what year was")
            })
            variations.append({
                "text": question.replace("When was", "What is the publication date of"),
                "english": english_question.replace("When was", "What is the publication date of")
            })
        
        # "What is the title of" variations
        elif question.startswith("What is the title of"):
            variations.append({
                "text": question.replace("What is the title of", "What is the name of"),
                "english": english_question.replace("What is the title of", "What is the name of")
            })
        
        # "Which organization published" variations
        elif question.startswith("Which organization published"):
            variations.append({
                "text": question.replace("Which organization published", "Who published"),
                "english": english_question.replace("Which organization published", "Who published")
            })
            variations.append({
                "text": question.replace("Which organization published", "What is the publisher of"),
                "english": english_question.replace("Which organization published", "What is the publisher of")
            })
        
        # "What is the topic of" variations
        elif question.startswith("What is the topic of"):
            variations.append({
                "text": question.replace("What is the topic of", "What is the subject of"),
                "english": english_question.replace("What is the topic of", "What is the subject of")
            })
            variations.append({
                "text": question.replace("What is the topic of", "What is the main theme of"),
                "english": english_question.replace("What is the topic of", "What is the main theme of")
            })
        
        return variations

    def get_general_variations(self, question, english_question):
        """
        Get general variations that apply to any question
        
        Args:
            question (str): Original question in English
            english_question (str): Original question in English
            
        Returns:
            list: Array of variation dictionaries
        """
        variations = []
        
        # Could you tell me...
        variations.append({
            "text": f"Could you tell me {question.lower()}",
            "english": f"Could you tell me {english_question.lower()}"
        })
        
        # I want to know...
        variations.append({
            "text": f"I want to know {question.lower()}",
            "english": f"I want to know {english_question.lower()}"
        })
        
        # I'm looking for information about...
        variations.append({
            "text": f"I'm looking for information about {question.lower().replace('what is ', '').replace('who is ', '')}",
            "english": f"I'm looking for information about {english_question.lower().replace('what is ', '').replace('who is ', '')}"
        })
        
        return variations

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for GESIS Knowledge Graph."""
    
    def __init__(self, config, endpoint_url="http://localhost:3030/gesis/query"):
        """
        Initialize the generator with knowledge graph schema information
        
        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            endpoint_url (str): URL of the Fuseki SPARQL endpoint
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.variation_generator = VariationGenerator()
        
        # Create a SPARQL executor to connect to Fuseki
        self.sparql_exec = SparqlExecutor(endpoint_url)
        
        # Pre-extract keywords from the knowledge graph
        self.extracted_keywords = self.extract_keywords_from_kg()
        
        # Fallback keywords in case extraction fails
        self.fallback_keywords = [
            "SOCIAL SCIENCE", "RESEARCH", "SURVEY", "DATA", "PUBLICATION", 
            "METHODOLOGY", "ANALYSIS", "DATASET", "KNOWLEDGE GRAPH", "SCHOLARLY"
        ]
        
        print(f"Extracted {len(self.extracted_keywords)} keywords from the knowledge graph")
    
    def extract_keywords_from_kg(self):
        """
        Extract meaningful keywords from resource titles in the knowledge graph
        
        Returns:
            list: List of keywords that appear in resource titles
        """
        try:
            # Query to get resource titles
            query = """
            SELECT ?title
            WHERE {
                ?resource a <https://schema.org/ScholarlyArticle> .
                ?resource <https://schema.org/name> ?title .
            }
            LIMIT 1000
            """
            
            results = self.sparql_exec.execute_query(query)
            if not results:
                print("No titles found in the knowledge graph")
                return []
                
            # Process titles and extract meaningful words
            all_words = []
            for result in results:
                if "title" in result:
                    title = str(result["title"])
                    # Split by spaces and filter for meaningful words (4+ characters)
                    title_words = [w.upper() for w in title.split() if len(w) >= 4]
                    all_words.extend(title_words)
            
            # Count frequency of each word
            word_counts = Counter(all_words)
            
            # Select words that appear at least twice (more meaningful)
            common_words = [word for word, count in word_counts.items() if count >= 5]
            
            # If we don't have enough common words, include all words
            if len(common_words) < 10:
                common_words = list(set(all_words))
            
            print(f"Found {len(common_words)} common words in resource titles")
            return common_words
            
        except Exception as e:
            print(f"Error extracting keywords from knowledge graph: {e}")
            return []
    
    def initialize_templates(self):
        """
        Initialize question-query template pairs for GESIS knowledge graph
        
        Returns:
            list: Templates for different question types and complexity levels
        """
        # GESIS Knowledge Graph specific templates
        scholarly_templates = [
            # Basic information about publications
            {
                "id": "publication-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the author of {entity}?",
                    "Who wrote {entity}?", 
                    "Who created {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Who is the author of {entity}?",
                    "Who wrote {entity}?",
                    "Who created {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    {entity} schema:author ?author .
                    ?author schema:name ?authorName .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "publication-date",
                "category": "scholarly",
                "questionTemplates": [
                    "When was {entity} published?",
                    "What is the publication date of {entity}?",
                    "In what year was {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "When was {entity} published?",
                    "What is the publication date of {entity}?",
                    "In what year was {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?date WHERE {
                    {entity} schema:datePublished ?date .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "publication-publisher",
                "category": "scholarly",
                "questionTemplates": [
                    "Which organization published {entity}?",
                    "Who published {entity}?",
                    "What is the publisher of {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Which organization published {entity}?",
                    "Who published {entity}?",
                    "What is the publisher of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?publisherName WHERE {
                    {entity} schema:publisher ?publisher .
                    ?publisher schema:name ?publisherName .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "publication-topic",
                "category": "scholarly",
                "questionTemplates": [
                    "What is the topic of {entity}?",
                    "What is the subject of {entity}?",
                    "What is the main theme of {entity}?"
                ],
                "englishQuestionTemplates": [
                    "What is the topic of {entity}?",
                    "What is the subject of {entity}?",
                    "What is the main theme of {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?topicName WHERE {
                    {entity} schema:about ?topic .
                    ?topic schema:name ?topicName .
                    }
                """,
                "complexity": "basic"
            },
            {
                "id": "publication-language",
                "category": "scholarly",
                "questionTemplates": [
                    "What language is {entity} written in?",
                    "What is the language of {entity}?",
                    "In which language was {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "What language is {entity} written in?",
                    "What is the language of {entity}?",
                    "In which language was {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?language WHERE {
                    {entity} schema:inLanguage ?language .
                    }
                """,
                "complexity": "basic"
            },
            
            # Intermediate: Structure and relationships
            {
                "id": "person-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications has {entity} authored?",
                    "What is the publication count of {entity}?",
                    "How many works did {entity} create?"
                ],
                "englishQuestionTemplates": [
                    "How many publications has {entity} authored?",
                    "What is the publication count of {entity}?",
                    "How many works did {entity} create?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        ?publication schema:author {entity} .
                        }
                    }
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "person-latest-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "What is the latest publication by {entity}?",
                    "What was {entity}'s most recent work?",
                    "What did {entity} publish most recently?"
                ],
                "englishQuestionTemplates": [
                    "What is the latest publication by {entity}?",
                    "What was {entity}'s most recent work?",
                    "What did {entity} publish most recently?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:author {entity} .
                    ?publication schema:name ?title .
                    ?publication schema:datePublished ?date .
                    }
                    ORDER BY DESC(?date)
                    LIMIT 1
                """,
                "complexity": "intermediate"
            },
            {
                "id": "publication-collaborator-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many collaborators worked on {entity}?",
                    "What is the number of authors for {entity}?",
                    "How many researchers contributed to {entity}?"
                ],
                "englishQuestionTemplates": [
                    "How many collaborators worked on {entity}?",
                    "What is the number of authors for {entity}?",
                    "How many researchers contributed to {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?collaborator) AS ?count) WHERE {
                        {entity} schema:author ?collaborator .
                        }
                    }
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "organization-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications are associated with {entity}?",
                    "What is the publication count for {entity}?",
                    "How many works has {entity} published?"
                ],
                "englishQuestionTemplates": [
                    "How many publications are associated with {entity}?",
                    "What is the publication count for {entity}?",
                    "How many works has {entity} published?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        {
                            ?publication schema:publisher {entity} .
                        } UNION {
                            ?publication schema:contributor {entity} .
                        }
                        }
                    }
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "year-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications were published in {value}?",
                    "What is the publication count for the year {value}?",
                    "How many works were released in {value}?"
                ],
                "englishQuestionTemplates": [
                    "How many publications were published in {value}?",
                    "What is the publication count for the year {value}?",
                    "How many works were released in {value}?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(?publication) AS ?count) WHERE {
                        ?publication schema:datePublished {value} .
                        }
                    }
                    }
                """,
                "complexity": "intermediate"
            },
            {
                "id": "person-first-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "What was the first publication by {entity}?",
                    "What is {entity}'s earliest work?",
                    "What did {entity} publish first?"
                ],
                "englishQuestionTemplates": [
                    "What was the first publication by {entity}?",
                    "What is {entity}'s earliest work?",
                    "What did {entity} publish first?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:author {entity} .
                    ?publication schema:name ?title .
                    ?publication schema:datePublished ?date .
                    }
                    ORDER BY ASC(?date)
                    LIMIT 1
                """,
                "complexity": "intermediate"
            },
            {
                "id": "topic-publication-count",
                "category": "scholarly",
                "questionTemplates": [
                    "How many publications are about '{value}'?",
                    "What is the number of works on '{value}'?",
                    "How many research papers discuss '{value}'?"
                ],
                "englishQuestionTemplates": [
                    "How many publications are about '{value}'?",
                    "What is the number of works on '{value}'?",
                    "How many research papers discuss '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?count WHERE {
                    {
                        SELECT (COUNT(DISTINCT ?publication) AS ?count) WHERE {
                        {
                            ?publication schema:about ?topic .
                            ?topic schema:name ?topicName .
                            FILTER(CONTAINS(LCASE(?topicName), LCASE({value})))
                        } UNION {
                            ?publication schema:keywords ?keyword .
                            FILTER(CONTAINS(LCASE(?keyword), LCASE({value})))
                        }
                        }
                    }
                    }
                """,
                "complexity": "intermediate"
            },
            
            # Advanced: Complex relationships and analytics
            {
                "id": "keyword-topic-top-expert",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the top expert on '{value}'?",
                    "Which researcher is most prominent in '{value}'?",
                    "Who has published the most about '{value}'?"
                ],
                "englishQuestionTemplates": [
                    "Who is the top expert on '{value}'?",
                    "Which researcher is most prominent in '{value}'?",
                    "Who has published the most about '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    ?author schema:name ?authorName .
                    ?publication schema:author ?author .
                    {
                        ?publication schema:about ?topic .
                        ?topic schema:name ?topicName .
                        FILTER(CONTAINS(LCASE(?topicName), LCASE({value})))
                    } UNION {
                        ?publication schema:keywords ?keyword .
                        FILTER(CONTAINS(LCASE(?keyword), LCASE({value})))
                    } UNION {
                        ?publication schema:name ?title .
                        FILTER(CONTAINS(LCASE(?title), LCASE({value})))
                    }
                    }
                    GROUP BY ?author ?authorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "organization-top-contributor",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the top contributor to {entity}?",
                    "Which author publishes most with {entity}?",
                    "Who is the leading researcher at {entity}?"
                ],
                "englishQuestionTemplates": [
                    "Who is the top contributor to {entity}?",
                    "Which author publishes most with {entity}?",
                    "Who is the leading researcher at {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?contributorName WHERE {
                    ?publication schema:publisher {entity} .
                    ?publication schema:author|schema:contributor ?contributor .
                    ?contributor schema:name ?contributorName .
                    }
                    GROUP BY ?contributor ?contributorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "publication-with-most-authors",
                "category": "scholarly",
                "questionTemplates": [
                    "Which publication has the most authors?",
                    "What paper has the largest research team?",
                    "Which work has the most collaborators?"
                ],
                "englishQuestionTemplates": [
                    "Which publication has the most authors?",
                    "What paper has the largest research team?",
                    "Which work has the most collaborators?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:name ?title .
                    ?publication schema:author ?author .
                    }
                    GROUP BY ?publication ?title
                    ORDER BY DESC(COUNT(?author))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "most-productive-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the most productive author?",
                    "Which researcher has published the most work?",
                    "Who has the highest publication count?"
                ],
                "englishQuestionTemplates": [
                    "Who is the most productive author?",
                    "Which researcher has published the most work?",
                    "Who has the highest publication count?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    ?author schema:name ?authorName .
                    ?publication schema:author ?author .
                    }
                    GROUP BY ?author ?authorName
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "most-collaborative-author",
                "category": "scholarly",
                "questionTemplates": [
                    "Who is the most collaborative author?",
                    "Which researcher works with the most co-authors?",
                    "Who has the most research partners?"
                ],
                "englishQuestionTemplates": [
                    "Who is the most collaborative author?",
                    "Which researcher works with the most co-authors?",
                    "Who has the most research partners?"
                ],
                "sparqlTemplate": """
                    SELECT ?authorName WHERE {
                    ?author schema:name ?authorName .
                    ?publication schema:author ?author .
                    ?publication schema:author ?coauthor .
                    FILTER(?author != ?coauthor)
                    }
                    GROUP BY ?author ?authorName
                    ORDER BY DESC(COUNT(DISTINCT ?coauthor))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "publications-by-year-trend",
                "category": "scholarly",
                "questionTemplates": [
                    "Which year had the most publications?",
                    "What was the most productive year for research publications?",
                    "In which year were the most papers published?"
                ],
                "englishQuestionTemplates": [
                    "Which year had the most publications?",
                    "What was the most productive year for research publications?",
                    "In which year were the most papers published?"
                ],
                "sparqlTemplate": """
                    SELECT ?year WHERE {
                    ?publication schema:datePublished ?fullDate .
                    BIND(SUBSTR(STR(?fullDate), 0, 5) AS ?year)
                    }
                    GROUP BY ?year
                    ORDER BY DESC(COUNT(?publication))
                    LIMIT 1
                """,
                "complexity": "advanced"
            },
            {
                "id": "most-diverse-publication",
                "category": "scholarly",
                "questionTemplates": [
                    "Which publication covers the most diverse topics?",
                    "What paper addresses the widest range of subjects?",
                    "Which research work has the most varied themes?"
                ],
                "englishQuestionTemplates": [
                    "Which publication covers the most diverse topics?",
                    "What paper addresses the widest range of subjects?",
                    "Which research work has the most varied themes?"
                ],
                "sparqlTemplate": """
                    SELECT ?title WHERE {
                    ?publication schema:name ?title .
                    ?publication schema:about ?topic .
                    }
                    GROUP BY ?publication ?title
                    ORDER BY DESC(COUNT(DISTINCT ?topic))
                    LIMIT 1
                """,
                "complexity": "advanced"
            }
        ]
        
        # Use scholarly templates for GESIS KG
        return scholarly_templates

    def generate_dataset(self, size=1000, complexity_distribution=None, include_variations=True, 
                    validate_queries=False, max_attempts_per_template=15):
        """
        Generate dataset based on GESIS knowledge graph
        
        Args:
            size (int): Total number of question-query pairs to generate
            complexity_distribution (dict): Distribution of complexity levels
            include_variations (bool): Whether to include variations of questions
            validate_queries (bool): Whether to validate SPARQL queries
            max_attempts_per_template (int): Maximum number of attempts to instantiate a template
            
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
        
        # Track problematic templates for reporting
        failed_templates = {}
        success_templates = {}
        
        # Generate questions for each complexity level
        for complexity, count in counts_by_complexity.items():
            successful_generations = 0
            eligible_templates = [t for t in self.templates if t["complexity"] == complexity]
            
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            # Try to generate the required number for this complexity
            while successful_generations < count and len(dataset) < size:
                # Randomly select a template for this complexity level
                template = random.choice(eligible_templates)
                
                # Track attempts for this template
                template_id = template["id"]
                if template_id not in success_templates:
                    success_templates[template_id] = 0
                if template_id not in failed_templates:
                    failed_templates[template_id] = 0
                
                # Try to instantiate this template up to max_attempts
                attempts = 0
                success = False
                
                while attempts < max_attempts_per_template and not success:
                    attempts += 1
                    try:
                        # Use the discovery-based approach to instantiate the template
                        instance = self.instantiate_template_with_discovery(template)
                        
                        if instance:
                            # Success! Add the question-query pair
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
                            successful_generations += 1
                            success_templates[template_id] += 1
                            success = True
                    except Exception as e:
                        print(f"Error instantiating template {template['id']} (attempt {attempts}): {e}")
                
                # If we've tried max_attempts and still failed, record this template as problematic
                if not success:
                    failed_templates[template_id] += 1
        
        # Report template success and failure rates
        print("\nTemplate success/failure statistics:")
        for template_id in set(success_templates.keys()) | set(failed_templates.keys()):
            success_count = success_templates.get(template_id, 0)
            failure_count = failed_templates.get(template_id, 0)
            total = success_count + failure_count
            success_rate = (success_count / total * 100) if total > 0 else 0
            print(f"  - {template_id}: {success_count} successes, {failure_count} failures ({success_rate:.1f}% success rate)")
        
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
        if validate_queries:
            filtered_dataset = []
            
            for item in dataset:
                try:
                    # Execute the query to validate it
                    results = self.sparql_exec.execute_query(item["sparql"], return_format="dict")
                    filtered_dataset.append(item)
                except Exception as e:
                    print(f"Invalid SPARQL query for id {item['id']}: {e}")
            
            return filtered_dataset
        
        return dataset

    def instantiate_template_with_discovery(self, template):
        """
        Instantiate a template using a discovery-based approach that guarantees valid placeholder values
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Extract placeholders from the template
        placeholders = self.extract_placeholders(template)
        
        # Special handling for templates without placeholders (like "most-collaborative-author")
        if not placeholders:
            print(f"Template {template['id']} has no placeholders, using direct instantiation")
            return self.instantiate_template_without_placeholders(template)
        
        # Special handling for keyword-based templates
        if "keyword" in template["id"] and "value" in placeholders:
            # For this template, use the pre-extracted keywords directly
            # rather than trying to discover them via SPARQL
            return self.instantiate_keyword_template(template)
        
        # Create a discovery query that includes all placeholders in the SELECT clause
        discovery_query = self.create_discovery_query(template, placeholders)
        
        if not discovery_query:
            print(f"Could not create discovery query for template: {template['id']}")
            return self.instantiate_template(template)
        
        # Quick validation of the discovery query
        if "??" in discovery_query:
            print(f"Error: Discovery query contains double question marks!")
            print(f"Query: {discovery_query}")
            return self.instantiate_template(template)
        
        # Execute the discovery query
        try:
            print(f"Executing discovery query for template {template['id']}...")
            results = self.sparql_exec.execute_query(discovery_query)
            
            if not results:
                print(f"No valid combinations found for template: {template['id']}")
                print("Query: ", discovery_query)
                return self.instantiate_template(template)
                
            print(f"Found {len(results)} valid combinations for template: {template['id']}")
                
            # Randomly select one complete valid combination of values
            selected = random.choice(results)
            
            # Create a mapping of placeholders to their values from the selected combination
            replacements = {}
            
            # Extract values for each placeholder
            for placeholder in placeholders:
                # Skip if placeholder doesn't exist in result
                if placeholder not in selected:
                    print(f"Warning: Placeholder {placeholder} not found in query results")
                    continue
                
                value = selected[placeholder]
                
                # Skip if value is None
                if value is None:
                    print(f"Warning: Placeholder {placeholder} has None value")
                    continue
                    
                # Try to get the label for entity placeholders
                if placeholder.startswith('entity'):
                    entity_uri = str(value)
                    
                    # Look for a label variable for this entity
                    label_var = f"{placeholder}Label"
                    if label_var in selected and selected[label_var] is not None:
                        entity_label = str(selected[label_var])
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
                    if "year" in template["id"] or "year" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                    elif "keyword" in template["id"] or "keyword" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"'  # Include quotes for string literal
                        }
                    elif "topic" in template["id"] or "topic" in template["questionTemplates"][0].lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str,
                            "sparqlValue": f'"{value_str}"'  # Include quotes for string literal
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
            
            # Check if all placeholders have valid replacements
            if set(replacements.keys()) != set(placeholders):
                missing = set(placeholders) - set(replacements.keys())
                print(f"Missing valid values for placeholders: {missing}")
                return self.instantiate_template(template)
                
            # Randomly select one of the question templates
            question_idx = random.randrange(len(template["questionTemplates"]))
            question_template = template["questionTemplates"][question_idx]
            english_question_template = template["englishQuestionTemplates"][question_idx]
            
            # Apply replacements to the question template
            question = question_template.strip()
            english_question = english_question_template.strip()
            sparql = template["sparqlTemplate"].strip()
            
            # Replace placeholders in question and query
            for placeholder, replacement in replacements.items():
                # Create a pattern that can handle whitespace around the placeholder
                pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
                
                # Replace in question
                replacement_text = replacement.get("label", replacement.get("value", ""))
                # Add quotes around entity placeholders, but not other placeholders like 'value'
                if placeholder.startswith('entity'):
                    quoted_replacement = f"'{replacement_text}'"
                    question = re.sub(pattern, quoted_replacement, question)
                    english_question = re.sub(pattern, quoted_replacement, english_question)
                else:
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
            
            # Replace all prefixed URIs with full URIs
            for prefix, uri in self.prefixes.items():
                pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
                sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
            
            # Format the SPARQL query for readability
            sparql = self.format_sparql(sparql)
            
            return {"question": question, "englishQuestion": english_question, "sparql": sparql}
                
        except Exception as e:
            print("Query: ", discovery_query)
            print(f"Error executing discovery query for template {template['id']}: {e}")
            # Fall back to the old method
            return self.instantiate_template(template)

    def instantiate_template_without_placeholders(self, template):
        """
        Special handler for templates without placeholders (like aggregation queries)
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query
        """
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Use the templates as is (no placeholders to replace)
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}
    def instantiate_keyword_template(self, template):
        """
        Special handler for keyword-based templates using pre-extracted keywords
        
        Args:
            template (dict): The template to instantiate
            
        Returns:
            dict: The instantiated question and SPARQL query or None if failed
        """
        # Get a keyword from our pre-extracted list
        keyword = self.select_keyword_value()
        
        # Apply the keyword to the template
        replacements = {"value": keyword}
        
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace the placeholder in question and query
        pattern = r"{[\s]*value[\s]*}"
        
        # Replace in question
        replacement_text = keyword.get("label", keyword.get("value", ""))
        # For keyword templates, the quotes are already included in the template
        # so we don't need to add them here
        question = re.sub(pattern, replacement_text, question)
        english_question = re.sub(pattern, replacement_text, english_question)
        
        # Replace in SPARQL
        sparql_value = keyword.get("sparqlValue", f'"{keyword["value"]}"')
        
        sparql = re.sub(pattern, sparql_value, sparql)
        
        # Replace all prefixed URIs with full URIs
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            sparql = re.sub(pattern, r'<' + uri + r'\1>', sparql)
        
        # Format the SPARQL query for readability
        sparql = self.format_sparql(sparql)
        
        return {"question": question, "englishQuestion": english_question, "sparql": sparql}

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
        
        # Special handling for keyword-based templates
        if "keyword" in template["id"] and "value" in placeholders:
            # For these templates, we'll use our pre-extracted keywords
            # rather than trying to discover them from the SPARQL endpoint
            return None
        
        # Extract the WHERE clause more carefully
        # First normalize the template by removing extra whitespace
        normalized_template = re.sub(r'\s+', ' ', sparql_template)
        
        # Find the WHERE clause - look for WHERE { ... } but be careful about nested braces
        where_start = normalized_template.find('WHERE {')
        if where_start == -1:
            print(f"Error: Could not find WHERE clause in template: {template['id']}")
            return None
        
        # Find the matching closing brace
        brace_count = 0
        where_content_start = where_start + len('WHERE {')
        where_end = where_content_start
        
        for i, char in enumerate(normalized_template[where_content_start:], where_content_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                if brace_count == 0:
                    where_end = i
                    break
                brace_count -= 1
        
        if where_end == where_content_start:
            print(f"Error: Could not find end of WHERE clause in template: {template['id']}")
            return None
            
        where_clause = normalized_template[where_content_start:where_end].strip()
        
        # Replace placeholders with variables in the WHERE clause
        modified_where = where_clause
        for placeholder in placeholders:
            # Handle quoted placeholders first
            quoted_pattern = r'"{\s*' + re.escape(placeholder) + r'\s*}"'
            modified_where = re.sub(quoted_pattern, f"?{placeholder}", modified_where)
            
            # Then handle regular placeholders
            regular_pattern = r'{\s*' + re.escape(placeholder) + r'\s*}'
            modified_where = re.sub(regular_pattern, f"?{placeholder}", modified_where)
        
        # Build SELECT clause with only the placeholder variables we need
        select_vars = []
        
        # Add all placeholder variables to SELECT clause
        for placeholder in placeholders:
            select_vars.append(f"?{placeholder}")
            # For entity placeholders, also select label if available
            if placeholder.startswith('entity'):
                select_vars.append(f"?{placeholder}Label")
        
        # Construct the discovery query step by step
        select_clause = "SELECT DISTINCT " + " ".join(select_vars)
        where_clause_with_optionals = f"WHERE {{ {modified_where}"
        
        # Add OPTIONAL label patterns for entity placeholders
        optional_clauses = []
        for placeholder in placeholders:
            if placeholder.startswith('entity'):
                optional_clauses.append(f"OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label }}")
                optional_clauses.append(f"OPTIONAL {{ ?{placeholder} <https://schema.org/name> ?{placeholder}Label }}")
        
        # Combine all parts
        if optional_clauses:
            discovery_query = f"{select_clause} {where_clause_with_optionals} {' '.join(optional_clauses)} }} LIMIT 100"
        else:
            discovery_query = f"{select_clause} {where_clause_with_optionals} }} LIMIT 100"
        
        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            discovery_query = re.sub(pattern, r'<' + uri + r'\1>', discovery_query)
        
        # Final cleanup - remove any double spaces and ensure proper formatting
        discovery_query = re.sub(r'\s+', ' ', discovery_query).strip()
        
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
        
        # Randomly select one of the question templates
        question_idx = random.randrange(len(template["questionTemplates"]))
        question_template = template["questionTemplates"][question_idx]
        english_question_template = template["englishQuestionTemplates"][question_idx]
        
        # Apply replacements to the question template
        question = question_template.strip()
        english_question = english_question_template.strip()
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
            # Add quotes around entity placeholders, but not other placeholders like 'value'
            if placeholder.startswith('entity'):
                quoted_replacement = f"'{replacement_text}'"
                question = re.sub(pattern, quoted_replacement, question)
                english_question = re.sub(pattern, quoted_replacement, english_question)
            else:
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
        # Check first question template - all should have the same placeholders
        question_template = template["questionTemplates"][0].strip()
        english_question = template["englishQuestionTemplates"][0].strip()
        sparql_template = template["sparqlTemplate"].strip()
        
        # Use a pattern that matches content between curly braces
        # This pattern is more restrictive to avoid matching SPARQL syntax
        pattern = r'{\s*([a-zA-Z][a-zA-Z0-9_]*)\s*}'
        
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
                replacement = self.select_entity_from_endpoint(template)
                
                if not replacement:
                    # Select entity based on template type
                    if "publication" in template["id"]:
                        # For publication templates, select a CreativeWork entity
                        replacement = self.select_entity_by_type("schema:CreativeWork")
                    elif "person" in template["id"]:
                        # For person templates, select a Person entity
                        replacement = self.select_entity_by_type("schema:Person")
                    elif "organization" in template["id"]:
                        # For organization templates, select an Organization entity
                        replacement = self.select_entity_by_type("schema:Organization")
                    else:
                        # Default to any entity
                        replacement = self.select_random_entity()
                
                # Fallback to any entity if specific type not found
                if not replacement:
                    replacement = self.select_random_entity()
            
            # Handle value placeholders
            elif placeholder == "value" or placeholder.endswith("Value"):
                replacement = self.select_value_from_endpoint(template, placeholder)
                
                # If we didn't get a replacement, use predefined values
                if not replacement:
                    if "year" in template["id"]:
                        # For year, use a year
                        replacement = self.select_year_value()
                    elif "keyword" in template["id"] or "topic" in template["id"]:
                        # For keywords or topics, use a keyword
                        replacement = self.select_keyword_value()
                    else:
                        replacement = self.select_random_value(template)
            
            # Handle property placeholders
            elif placeholder.startswith('property'):
                replacement = self.select_scholarly_property(template, placeholder)
            
            # If we couldn't find a replacement, return None
            if not replacement:
                print(f"Could not find replacement for placeholder: {placeholder}")
                return None
            
            replacements[placeholder] = replacement
        
        return replacements

    def select_entity_from_endpoint(self, template):
        """
        Select an entity from the SPARQL endpoint that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            
        Returns:
            dict: Selected entity info or None if not found
        """
        sparql_template = template["sparqlTemplate"]
        
        # Extract the predicate pattern for the entity
        # Look for patterns like: {entity} predicate ?object
        predicate_match = re.search(r'{\s*entity\s*}\s+([^\s.{}<>]+)\s+', sparql_template)
        
        if not predicate_match:
            # Try the inverse pattern: ?subject predicate {entity}
            predicate_match = re.search(r'([^\s.{}<>]+)\s+{\s*entity\s*}', sparql_template)
            if predicate_match:
                # This is an inverse relationship
                predicate = predicate_match.group(1)
                
                # Handle RDF/SPARQL prefixes
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
                    
                # Create the query to find valid objects for this predicate
                query = f"""
                    SELECT DISTINCT ?entity ?label
                    WHERE {{
                        ?subj <{predicate_uri}> ?entity .
                        OPTIONAL {{ ?entity rdfs:label ?label }}
                        OPTIONAL {{ ?entity <https://schema.org/name> ?label }}
                    }}
                    LIMIT 50
                """
                
                try:
                    # Execute query against the endpoint
                    results = self.sparql_exec.execute_query(query)
                    
                    if not results:
                        return None
                        
                    # Randomly select one entity from the results
                    selected = random.choice(results)
                    entity_uri = selected["entity"]
                    
                    # Use label if available, otherwise extract from URI
                    if "label" in selected and selected["label"]:
                        entity_label = selected["label"]
                    else:
                        entity_label = self.extract_label_from_uri(entity_uri)
                        
                    return {
                        "value": self.shorten_uri(entity_uri),
                        "label": entity_label,
                        "uri": entity_uri
                    }
                    
                except Exception as e:
                    print(f"Error selecting entity from endpoint: {e}")
                    return None
        
        if not predicate_match:
            return None
            
        predicate = predicate_match.group(1)
        
        # Handle RDF/SPARQL prefixes
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
            
        # Create the query to find valid subjects for this predicate
        query = f"""
            SELECT DISTINCT ?entity ?label
            WHERE {{
                ?entity <{predicate_uri}> ?obj .
                OPTIONAL {{ ?entity rdfs:label ?label }}
                OPTIONAL {{ ?entity <https://schema.org/name> ?label }}
            }}
            LIMIT 50
        """
        
        try:
            # Execute query against the endpoint
            results = self.sparql_exec.execute_query(query)
            
            if not results:
                return None
                
            # Randomly select one entity from the results
            selected = random.choice(results)
            entity_uri = selected["entity"]
            
            # Use label if available, otherwise extract from URI
            if "label" in selected and selected["label"]:
                entity_label = selected["label"]
            else:
                entity_label = self.extract_label_from_uri(entity_uri)
                
            return {
                "value": self.shorten_uri(entity_uri),
                "label": entity_label,
                "uri": entity_uri
            }
            
        except Exception as e:
            print(f"Error selecting entity from endpoint: {e}")
            return None

    def select_value_from_endpoint(self, template, placeholder):
        """
        Select a value from the SPARQL endpoint that fits the template
        
        Args:
            template (dict): The template containing the sparqlTemplate
            placeholder (str): The name of the placeholder
            
        Returns:
            dict: Selected value info or None if not found
        """
        # For year values in publications
        if "publications-by-year" in template["id"]:
            # Extract a list of years from the endpoint
            query = """
                SELECT DISTINCT ?year
                WHERE {
                    ?publication <https://schema.org/datePublished> ?date .
                    BIND(SUBSTR(STR(?date), 0, 5) AS ?year)
                }
                ORDER BY ?year
            """
            
            try:
                results = self.sparql_exec.execute_query(query)
                if results:
                    # Pick a random year from results
                    year_value = str(random.choice(results)["year"])
                    return {
                        "value": year_value,
                        "label": year_value,
                        "sparqlValue": f'"{year_value}"'
                    }
            except Exception as e:
                print(f"Error querying for years: {e}")
        
        # For keyword values in keyword-based queries
        elif "keyword" in template["id"] or "topic" in template["id"]:
            # Use our pre-extracted keywords
            return self.select_keyword_value()
            
        return None

    def select_entity_by_type(self, type_value):
        """
        Select a random entity of a specific type
        
        Args:
            type_value (str): Type value (e.g. schema:CreativeWork)
            
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
        
        # Fallback to predefined scholarly entities
        # This ensures we always have something workable for the GESIS KG
        scholarly_entities = [
            {"value": "schema:Dataset1", "label": "Dataset on Social Science Research", 
             "uri": "https://data.gesis.org/gesiskg/resource/dataset-001", "type": "schema:Dataset"},
            {"value": "schema:Publication1", "label": "Analysis of Social Media Usage", 
             "uri": "https://data.gesis.org/gesiskg/resource/publication-001", "type": "schema:CreativeWork"},
            {"value": "schema:Author1", "label": "Dr. Jane Smith", 
             "uri": "https://data.gesis.org/gesiskg/resource/person-001", "type": "schema:Person"},
            {"value": "schema:Organization1", "label": "GESIS - Leibniz Institute for the Social Sciences", 
             "uri": "https://data.gesis.org/gesiskg/resource/organization-001", "type": "schema:Organization"},
            {"value": "schema:Journal1", "label": "Journal of Social Science Research", 
             "uri": "https://data.gesis.org/gesiskg/resource/journal-001", "type": "schema:Periodical"}
        ]
        
        print("Warning: Using fallback scholarly entities")
        return random.choice(scholarly_entities)

    def select_scholarly_property(self, template, placeholder):
        """
        Select a property appropriate for scholarly templates
        
        Args:
            template (dict): The template being instantiated
            placeholder (str): The property placeholder name
            
        Returns:
            dict: Selected property
        """
        # Define common scholarly properties
        scholarly_properties = {
            "author": {"value": "schema:author", "label": "author", 
                      "uri": "https://schema.org/author"},
            "title": {"value": "schema:name", "label": "name", 
                     "uri": "https://schema.org/name"},
            "date": {"value": "schema:datePublished", "label": "date published", 
                    "uri": "https://schema.org/datePublished"},
            "publisher": {"value": "schema:publisher", "label": "publisher", 
                         "uri": "https://schema.org/publisher"},
            "topic": {"value": "schema:about", "label": "about", 
                     "uri": "https://schema.org/about"},
            "citation": {"value": "schema:citation", "label": "citation", 
                        "uri": "https://schema.org/citation"},
            "contributor": {"value": "schema:contributor", "label": "contributor", 
                           "uri": "https://schema.org/contributor"},
            "keywords": {"value": "schema:keywords", "label": "keywords", 
                        "uri": "https://schema.org/keywords"}
        }
        
        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "author" in template["id"] or "author" in placeholder:
                prop = self.find_property_by_name("author")
                if prop:
                    return prop
                
            elif "title" in template["id"] or "title" in placeholder:
                prop = self.find_property_by_name("name")
                if prop:
                    return prop
                
            elif "date" in template["id"] or "date" in placeholder:
                prop = self.find_property_by_name("datePublished")
                if prop:
                    return prop
                
            elif "publisher" in template["id"] or "publisher" in placeholder:
                prop = self.find_property_by_name("publisher")
                if prop:
                    return prop
                
            elif "topic" in template["id"] or "topic" in placeholder:
                prop = self.find_property_by_name("about")
                if prop:
                    return prop
                
            elif "citation" in template["id"] or "citation" in placeholder:
                prop = self.find_property_by_name("citation")
                if prop:
                    return prop
        
        # If we don't have the property in schema info, use our predefined ones
        if "author" in template["id"] or "author" in placeholder:
            return scholarly_properties["author"]
            
        elif "title" in template["id"] or "title" in placeholder:
            return scholarly_properties["title"]
            
        elif "date" in template["id"] or "date" in placeholder:
            return scholarly_properties["date"]
            
        elif "publisher" in template["id"] or "publisher" in placeholder:
            return scholarly_properties["publisher"]
            
        elif "topic" in template["id"] or "topic" in placeholder:
            return scholarly_properties["topic"]
            
        elif "citation" in template["id"] or "citation" in placeholder:
            return scholarly_properties["citation"]
            
        # Fallback to any property if we can't find a specific match
        if "properties" in self.schema_info and self.schema_info["properties"]:
            return random.choice(self.schema_info["properties"])
            
        # Last resort - return title as default
        return scholarly_properties["title"]

    def select_year_value(self):
        """
        Select a realistic year value for scholarly publications
        
        Returns:
            dict: Year value object
        """
        years = list(range(1990, 2025))
        value = random.choice(years)
        return {"value": str(value), "label": str(value), "sparqlValue": f'"{value}"'}

    def select_keyword_value(self):
        """
        Select a keyword value for searching scholarly publications
        
        Returns:
            dict: Keyword value object
        """
        # Use the pre-extracted keywords if available
        if self.extracted_keywords:
            value = random.choice(self.extracted_keywords)
        else:
            # Fallback to predefined keywords
            print("Using fallback keywords")
            value = random.choice(self.fallback_keywords)
            
        return {"value": value, "label": value, "sparqlValue": f'"{value}"'}

    def select_random_value(self, template):
        """
        Select a random appropriate value
        
        Args:
            template (dict): The template being instantiated
            
        Returns:
            dict: Selected value
        """
        # Special handling for scholarly data
        if template.get("category") == "scholarly":
            if "year" in template["id"]:
                return self.select_year_value()
            elif "keyword" in template["id"] or "topic" in template["id"]:
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

    def extract_label_from_uri(self, uri):
        """
        Extract a human-readable label from a URI
        
        Args:
            uri (str): URI to extract label from
            
        Returns:
            str: Human-readable label
        """
        return gesis_entity_label(uri)

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
            # Remove all spaces from URIs
            return uri.replace(" ", "")
        
        # Fix all URIs first by removing spaces
        sparql = re.sub(r'<[^>]+>', clean_uri, sparql)
        
        # Now proceed with other formatting
        sparql = re.sub(r'PREFIX\s+\w+:\s+<[^>]+>\s*', '', sparql)
        sparql = re.sub(r'\s+', ' ', sparql)
        
        # Format spaces around keywords properly
        sparql = re.sub(r'(?i)\bSELECT\b', 'SELECT', sparql)
        sparql = re.sub(r'(?i)\bWHERE\b', ' WHERE ', sparql)
        sparql = re.sub(r'(?i)\bFILTER\b', ' FILTER ', sparql)
        sparql = re.sub(r'(?i)\bORDER BY\b', ' ORDER BY ', sparql)
        sparql = re.sub(r'(?i)\bLIMIT\b', ' LIMIT ', sparql)
        sparql = re.sub(r'(?i)\bGROUP BY\b', ' GROUP BY ', sparql)
        sparql = re.sub(r'(?i)\bHAVING\b', ' HAVING ', sparql)
        sparql = re.sub(r'(?i)\bCOUNT\b', 'COUNT', sparql)
        sparql = re.sub(r'(?i)\bAS\b', ' AS ', sparql)
        sparql = re.sub(r'(?i)\bDISTINCT\b', 'DISTINCT ', sparql)
        sparql = re.sub(r'(?i)\bUNION\b', ' UNION ', sparql)
        sparql = re.sub(r'(?i)\bOPTIONAL\b', ' OPTIONAL ', sparql)
        
        # Format braces
        sparql = re.sub(r'\s*{\s*', ' { ', sparql)
        sparql = re.sub(r'\s*}\s*', ' } ', sparql)
        
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