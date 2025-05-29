import json
import random
import re
import datetime
import csv
import io
import os
from rdflib import Graph, Namespace, URIRef, Literal
from nltk.corpus import stopwords
from nltk.tokenize import RegexpTokenizer
from nltk import ngrams

class NL2SPARQLGenerator:
    """Generator for natural language to SPARQL query pairs for university courses."""
    
    def __init__(self, config, graph=None, property_retrieval=None):
        """
        Initialize the generator with knowledge graph schema information
        
        Args:
            config (dict): Configuration with prefixes, entity examples, and schema info
            graph (rdflib.Graph, optional): RDF graph for context-aware entity selection
            property_retrieval: Property retrieval system for Weaviate-based search
        """
        self.config = config
        self.prefixes = config.get("prefixes", {})
        self.entity_examples = config.get("entityExamples", [])
        self.schema_info = config.get("schemaInfo", {})
        self.templates = self.initialize_templates()
        self.property_retrieval = property_retrieval
        
        # Initialize stopwords
        self.stopwords = set(stopwords.words('english'))
        
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
        # Basic course information templates - with multiple question variations
        basic_templates = [
            {
                "id": "course-credits",
                "category": "university",
                "questionTemplates": [
                    "How many credits does the {entity} course have?",
                    "What is the credit value for {entity}?",
                    "Can you tell me the number of credits for the {entity} course?"
                ],
                "sparqlTemplate": """
                    SELECT ?value WHERE {
                      {entity} ns1:has_credits ?value .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the credit value of {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_credits' links a course to its credit value.",
                    "4. To solve this, retrieve the credit value linked to {entity} via the 'ns1:has_credits' property.",
                    "5. Construct a SPARQL query to retrieve the credit value for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-code",
                "category": "university",
                "questionTemplates": [
                    "What is the course code for {entity}?",
                    "What's the identifier or course number for {entity}?",
                    "Can you look up the course code assigned to {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?code WHERE {
                      {entity} ns1:has_course_code ?code .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the course code of {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_course_code' links courses to their unique identifiers.",
                    "4. To solve this, retrieve the course code linked to {entity} via the 'ns1:has_course_code' property.",
                    "5. Construct a SPARQL query to retrieve the course code for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-category",
                "category": "university",
                "questionTemplates": [
                    "What category does {entity} belong to?",
                    "Which subject area is {entity} classified under?",
                    "Under which category is the {entity} course listed?"
                ],
                "sparqlTemplate": """
                    SELECT ?category WHERE {
                      {entity} ns1:has_course_category ?category .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the course category of {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_course_category' links courses to their classification categories.",
                    "4. To solve this, retrieve the category linked to {entity} via the 'ns1:has_course_category' property.",
                    "5. Construct a SPARQL query to retrieve the course category for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-prerequisites",
                "category": "university",
                "questionTemplates": [
                    "What are the prerequisites for {entity}?",
                    "Which courses must be completed before taking {entity}?",
                    "What prior coursework is required for enrolling in {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?prereq WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for prerequisite courses of {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_prerequisite_course' links courses to their required prerequisites.",
                    "4. To solve this, retrieve all prerequisite courses linked to {entity} via the 'ns1:has_prerequisite_course' property.",
                    "5. Construct a SPARQL query to list all prerequisite courses for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-evaluation",
                "category": "university",
                "questionTemplates": [
                    "What evaluation methods are used for {entity}?",
                    "How are students assessed in the {entity} course?",
                    "Which assessment techniques are employed in {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?method WHERE {
                      {entity} ns1:has_evaluation_method ?method .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for all evaluation methods used in {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "4. To solve this, retrieve all entities connected to {entity} via the 'ns1:has_evaluation_method' property.",
                    "5. Construct a SPARQL query to list all evaluation methods for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-research-group",
                "category": "university",
                "questionTemplates": [
                    "Which research group is associated with {entity}?",
                    "What research lab develops or maintains the {entity} course?",
                    "Which academic research team is connected to {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?group WHERE {
                      {entity} ns1:has_research_group ?group .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for research groups associated with {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_research_group' links courses to their associated research groups.",
                    "4. To solve this, retrieve all research groups linked to {entity} via the 'ns1:has_research_group' property.",
                    "5. Construct a SPARQL query to list all research groups for {entity}."
                ],
                "complexity": "basic"
            },
            {
                "id": "course-nickname",
                "category": "university",
                "questionTemplates": [
                    "What are the alternative names or abbreviations for {entity}?",
                    "How is {entity} informally known or abbreviated?",
                    "What nicknames or short forms are used for {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?nickname WHERE {
                      {entity} ns1:also_known_as ?nickname .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for alternative names or abbreviations for {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:also_known_as' links courses to their alternative names, nicknames, or abbreviations.",
                    "4. To solve this, retrieve all alternative names linked to {entity} via the 'ns1:also_known_as' property.",
                    "5. Construct a SPARQL query to list all alternative names for {entity}."
                ],
                "complexity": "basic"
            },
        ]
        
        # Intermediate templates - with multiple question variations
        intermediate_templates = [
            {
                "id": "count-prerequisites",
                "category": "university",
                "questionTemplates": [
                    "How many prerequisites does {entity} have?",
                    "What is the total number of prerequisite courses for {entity}?",
                    "How many courses must be completed before taking {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?prereq) AS ?count) WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of prerequisite courses for {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "4. To solve this, count all prerequisite courses linked to {entity} via the 'ns1:has_prerequisite_course' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the number of prerequisites."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "count-evaluation-methods",
                "category": "university",
                "questionTemplates": [
                    "How many evaluation methods are associated with {entity}?",
                    "What is the count of assessment techniques used in {entity}?",
                    "How many different ways are students evaluated in {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?method) AS ?count) WHERE {
                      {entity} ns1:has_evaluation_method ?method .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of evaluation methods used in {entity}.",
                    "2. The entity '{entity}' represents a course in the university domain.",
                    "3. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "4. To solve this, count all evaluation methods linked to {entity} via the 'ns1:has_evaluation_method' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the number of evaluation methods."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "courses-with-credits",
                "category": "university",
                "questionTemplates": [
                    "Which courses have {value} credits?",
                    "List all courses worth {value} credit points.",
                    "What courses are valued at {value} credits?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_credits {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that have {value} credits.",
                    "2. In the ontology, 'ns1:course' represents all course entities.",
                    "3. The property 'ns1:has_credits' links courses to their credit values.",
                    "4. To solve this, identify all courses with {value} as their credit value.",
                    "5. Construct a SPARQL query that filters courses with 'ns1:has_credits' equal to {value}."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "courses-by-research-group",
                "category": "university",
                "questionTemplates": [
                    "Which courses are associated with the {entity} research group?",
                    "What courses are developed by the {entity} research team?",
                    "List all courses connected to the {entity} research lab."
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_research_group {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that are part of the '{entity}' research group.",
                    "2. The entity '{entity}' represents the research group in question.",
                    "3. The property 'ns1:has_research_group' links a course to its research group.",
                    "4. To solve this, retrieve all courses linked to '{entity}' via the 'ns1:has_research_group' property.",
                    "5. Construct a SPARQL query to list all courses associated with this research group."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "courses-by-evaluation",
                "category": "university",
                "questionTemplates": [
                    "Which courses are evaluated using {entity}?",
                    "What courses use {entity} as an assessment method?",
                    "List all courses that employ {entity} for student evaluation."
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_evaluation_method {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that use '{entity}' as an evaluation method.",
                    "2. The entity '{entity}' represents the evaluation method in question.",
                    "3. The property 'ns1:has_evaluation_method' links a course to its evaluation methods.",
                    "4. To solve this, retrieve all courses linked to '{entity}' via the 'ns1:has_evaluation_method' property.",
                    "5. Construct a SPARQL query to list all courses using this evaluation method."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "count-courses-by-category",
                "category": "university",
                "questionTemplates": [
                    "How many courses are in the {entity} category?",
                    "What is the total number of courses in the {entity} subject area?",
                    "Count all courses classified under {entity}."
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?course) AS ?count) WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_course_category {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of courses in the '{entity}' category.",
                    "2. The entity '{entity}' represents the course category in question.",
                    "3. The property 'ns1:has_course_category' links a course to its category.",
                    "4. To solve this, count all courses linked to '{entity}' via the 'ns1:has_course_category' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the number of such courses."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "courses-by-prerequisite",
                "category": "university",
                "questionTemplates": [
                    "What courses have {entity} as a prerequisite course?",
                    "Which courses require {entity} to be completed first?",
                    "List all courses that need {entity} as a prerequisite."
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that have '{entity}' as a prerequisite.",
                    "2. The entity '{entity}' represents the prerequisite course in question.",
                    "3. The property 'ns1:has_prerequisite_course' links a course to its prerequisite courses.",
                    "4. To solve this, retrieve all courses linked to '{entity}' via the 'ns1:has_prerequisite_course' property.",
                    "5. Construct a SPARQL query to list all courses with this prerequisite."
                ],
                "complexity": "intermediate"
            },
            {
                "id": "count-courses-by-prerequisite",
                "category": "university",
                "questionTemplates": [
                    "How many courses have {entity} as a prerequisite course?",
                    "What is the count of courses requiring {entity} as a prerequisite?",
                    "How many courses need {entity} to be completed first?"
                ],
                "sparqlTemplate": """
                    SELECT (COUNT(?course) AS ?count) WHERE {
                      ?course ns1:has_prerequisite_course {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the number of courses that have '{entity}' as a prerequisite.",
                    "2. The entity '{entity}' represents the prerequisite course in question.",
                    "3. The property 'ns1:has_prerequisite_course' links a course to its prerequisite courses.",
                    "4. To solve this, count all courses linked to '{entity}' via the 'ns1:has_prerequisite_course' property.",
                    "5. Construct a SPARQL query using the COUNT function to determine the number of such courses."
                ],
                "complexity": "intermediate"
            },
        ]
        
        # Advanced templates - with multiple question variations
        original_advanced_templates = [
            {
                "id": "courses-with-same-prerequisites",
                "category": "university",
                "questionTemplates": [
                    "Which courses have the same prerequisites as {entity}?",
                    "What other courses require identical prerequisites to {entity}?",
                    "Find courses sharing the same prerequisite requirements as {entity}."
                ],
                "sparqlTemplate": """
                    SELECT DISTINCT ?course WHERE {
                      {entity} ns1:has_prerequisite_course ?prereq .
                      ?course ns1:has_prerequisite_course ?prereq .
                      FILTER(?course != {entity})
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that have the same prerequisites as '{entity}'.",
                    "2. The entity '{entity}' represents the reference course.",
                    "3. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "4. To solve this, first find prerequisites of '{entity}', then find other courses with those same prerequisites.",
                    "5. Construct a SPARQL query using a pattern to match courses with identical prerequisite requirements.",
                    "6. Use FILTER to exclude '{entity}' from the results to show only other courses."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-most-credits",
                "category": "university",
                "questionTemplates": [
                    "Which course has the highest number of credits?",
                    "What is the course with the maximum credit value?",
                    "Which course offers the most credits?"
                ],
                "sparqlTemplate": """
                    SELECT ?course ?credits WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_credits ?credits .
                    }
                    ORDER BY DESC(?credits)
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the course with the highest credit value.",
                    "2. In the ontology, 'ns1:course' represents all course entities.",
                    "3. The property 'ns1:has_credits' links courses to their credit values.",
                    "4. To solve this, retrieve all courses and their credit values, then order by credits in descending order.",
                    "5. Construct a SPARQL query using ORDER BY DESC to sort by credits and LIMIT 1 to get the highest."
                ],
                "complexity": "advanced"
            },
            {
                "id": "research-group-most-courses",
                "category": "university",
                "questionTemplates": [
                    "Which research group is associated with the most courses?",
                    "What research lab develops the largest number of courses?",
                    "Which research team has created the most courses?"
                ],
                "sparqlTemplate": """
                    SELECT ?group (COUNT(?course) as ?count) WHERE {
                      ?course a ns1:course .
                      ?course ns1:has_research_group ?group .
                    }
                    GROUP BY ?group
                    ORDER BY DESC(?count)
                    LIMIT 1
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the research group with the most associated courses.",
                    "2. In the ontology, 'ns1:course' represents all course entities.",
                    "3. The property 'ns1:has_research_group' links courses to their research groups.",
                    "4. To solve this, count courses for each research group using GROUP BY and COUNT.",
                    "5. Construct a SPARQL query using GROUP BY to group by research groups and COUNT to count courses.",
                    "6. Use ORDER BY DESC to sort by count in descending order, and LIMIT 1 to return only the top research group."
                ],
                "complexity": "advanced"
            },
            {
                "id": "common-prerequisites",
                "category": "university",
                "questionTemplates": [
                    "What are the 5 most common prerequisite courses?",
                    "Which 5 courses are most frequently required as prerequisites?",
                    "List the top 5 courses that appear as prerequisites."
                ],
                "sparqlTemplate": """
                    SELECT ?prereq (COUNT(?course) as ?count) WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                    }
                    GROUP BY ?prereq
                    ORDER BY DESC(?count)
                    LIMIT 5
                """,
                "thoughtsTemplate": [
                    "1. The question asks for the most commonly used prerequisite courses.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. To solve this, count how many times each course appears as a prerequisite.",
                    "4. Construct a SPARQL query using GROUP BY to group by prerequisite courses and COUNT to count occurrences.",
                    "5. Use ORDER BY DESC to sort by count in descending order, and LIMIT 5 to return the top 5 prerequisites."
                ],
                "complexity": "advanced"
            },
        ]
        
        # Enhanced advanced templates - with multiple question variations
        enhanced_advanced_templates = [
            {
                "id": "courses-with-triple-condition",
                "category": "university",
                "questionTemplates": [
                    "What courses have {entity1} as their research group, are categorized as {entity2}, and use {entity3} as their evaluation method?",
                    "Find courses that belong to the {entity1} research team, fall under the {entity2} category, and use {entity3} for assessment.",
                    "Which courses are simultaneously part of {entity1} research group, classified as {entity2}, and evaluated through {entity3}?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_research_group {entity1} .
                      ?course ns1:has_course_category {entity2} .
                      ?course ns1:has_evaluation_method {entity3} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses that meet three criteria: research group '{entity1}', category '{entity2}', and evaluation method '{entity3}'.",
                    "2. The property 'ns1:has_research_group' links courses to their research groups.",
                    "3. The property 'ns1:has_course_category' links courses to their categories.",
                    "4. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "5. To solve this, find courses that satisfy all three conditions simultaneously.",
                    "6. Construct a SPARQL query with multiple constraints to find courses matching all three conditions."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-triple-condition-code",
                "category": "university",
                "questionTemplates": [
                    "What course has the evaluation method of {entity1} and is a {entity2} with the course code '{value}'?",
                    "Find the course that uses {entity1} for assessment, belongs to {entity2} category, and has code '{value}'.",
                    "Which course is evaluated using {entity1}, categorized as {entity2}, and identified by code '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_course_category {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for a course with evaluation method '{entity1}', category '{entity2}', and course code '{value}'.",
                    "2. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "3. The property 'ns1:has_course_category' links courses to their categories.",
                    "4. The property 'ns1:has_course_code' links courses to their unique identifiers.",
                    "5. To solve this, find the course that satisfies all three conditions.",
                    "6. Construct a SPARQL query with multiple constraints to find the course matching all conditions."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-double-evaluation-code",
                "category": "university",
                "questionTemplates": [
                    "What courses have '{entity1}' and '{entity2}' as evaluation methods and have the course code '{value}'?",
                    "Find courses that use both '{entity1}' and '{entity2}' for assessment and are coded as '{value}'.",
                    "Which courses employ '{entity1}' and '{entity2}' for evaluation and have '{value}' as their code?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_evaluation_method {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses with both '{entity1}' and '{entity2}' as evaluation methods and course code '{value}'.",
                    "2. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "3. The property 'ns1:has_course_code' links courses to their unique identifiers.",
                    "4. To solve this, find courses that have both evaluation methods and the specified course code.",
                    "5. Construct a SPARQL query with multiple evaluation method constraints and a course code constraint."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-research-eval-code",
                "category": "university",
                "questionTemplates": [
                    "What courses have the evaluation method '{entity1}' and are associated with the research group '{entity2}' and have the course code '{value}'?",
                    "Find courses that use '{entity1}' for assessment, belong to '{entity2}' research team, and have code '{value}'.",
                    "Which courses are evaluated using '{entity1}', connected to '{entity2}' research group, and identified by '{value}'?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_evaluation_method {entity1} .
                      ?course ns1:has_research_group {entity2} .
                      ?course ns1:has_course_code {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses with evaluation method '{entity1}', research group '{entity2}', and course code '{value}'.",
                    "2. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "3. The property 'ns1:has_research_group' links courses to their research groups.",
                    "4. The property 'ns1:has_course_code' links courses to their unique identifiers.",
                    "5. To solve this, find courses that satisfy all three conditions.",
                    "6. Construct a SPARQL query with constraints for evaluation method, research group, and course code."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prereq-eval-category",
                "category": "university",
                "questionTemplates": [
                    "What courses have {entity1} as a prerequisite and {entity2} as an evaluation method, and are {entity3}?",
                    "Find courses that require {entity1} as prerequisite, use {entity2} for assessment, and belong to {entity3} category.",
                    "Which courses need {entity1} completed first, employ {entity2} for evaluation, and are classified as {entity3}?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course {entity1} .
                      ?course ns1:has_evaluation_method {entity2} .
                      ?course ns1:has_course_category {entity3} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses with prerequisite '{entity1}', evaluation method '{entity2}', and category '{entity3}'.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "4. The property 'ns1:has_course_category' links courses to their categories.",
                    "5. To solve this, find courses that satisfy all three conditions.",
                    "6. Construct a SPARQL query with constraints for prerequisite, evaluation method, and category."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prerequisite-eval",
                "category": "university",
                "questionTemplates": [
                    "What courses have prerequisites that have {entity} as their evaluation method?",
                    "Find courses whose prerequisite courses use {entity} for assessment.",
                    "Which courses require completion of courses that are evaluated using {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_evaluation_method {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses whose prerequisites use '{entity}' as an evaluation method.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. The property 'ns1:has_evaluation_method' links courses to their evaluation methods.",
                    "4. To solve this, find courses with prerequisites that have '{entity}' as their evaluation method.",
                    "5. Construct a SPARQL query using a nested pattern to find courses whose prerequisites use the specified evaluation method."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prerequisite-category",
                "category": "university",
                "questionTemplates": [
                    "What courses have prerequisites with {entity} as their category?",
                    "Find courses that require completion of {entity} courses first.",
                    "Which courses have prerequisites classified under the {entity} category?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_course_category {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses whose prerequisites belong to the '{entity}' category.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. The property 'ns1:has_course_category' links courses to their categories.",
                    "4. To solve this, find courses with prerequisites that are categorized as '{entity}'.",
                    "5. Construct a SPARQL query using a nested pattern to find courses whose prerequisites are of the specified category."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prerequisite-credits",
                "category": "university",
                "questionTemplates": [
                    "What courses have prerequisites with {value} credits?",
                    "Find courses that require completion of {value}-credit courses first.",
                    "Which courses have prerequisites worth {value} credits?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_credits {value} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses whose prerequisites have {value} credits.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. The property 'ns1:has_credits' links courses to their credit values.",
                    "4. To solve this, find courses with prerequisites that have {value} as their credit value.",
                    "5. Construct a SPARQL query using a nested pattern to find courses whose prerequisites have the specified credit value."
                ],
                "complexity": "advanced"
            },
            {
                "id": "courses-with-prereq-of-prereq",
                "category": "university", 
                "questionTemplates": [
                    "What courses have prerequisites with {entity} as their prerequisites?",
                    "Find courses where {entity} is a prerequisite of their prerequisites.",
                    "Which courses require completion of courses that themselves require {entity}?"
                ],
                "sparqlTemplate": """
                    SELECT ?course WHERE {
                      ?course ns1:has_prerequisite_course ?prereq .
                      ?prereq ns1:has_prerequisite_course {entity} .
                    }
                """,
                "thoughtsTemplate": [
                    "1. The question asks for courses whose prerequisites have '{entity}' as their prerequisite.",
                    "2. The property 'ns1:has_prerequisite_course' links courses to their prerequisites.",
                    "3. To solve this, find courses with prerequisites that themselves have '{entity}' as a prerequisite.",
                    "4. This involves a two-level prerequisite relationship query.",
                    "5. Construct a SPARQL query using a nested pattern to find courses whose prerequisites have '{entity}' as their prerequisite."
                ],
                "complexity": "advanced"
            },
        ]
        
        # Combine all templates
        all_templates = basic_templates + intermediate_templates + original_advanced_templates + enhanced_advanced_templates
        
        return all_templates

    def generate_chain_of_thoughts(self, question, sparql, template):
        """
        Generate a chain of thoughts explaining how to translate the question to SPARQL
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            template (dict): Template used to generate the question-query pair
            
        Returns:
            list: List of thought steps
        """
        if "thoughtsTemplate" not in template:
            # Fallback for templates without thoughtsTemplate
            return [
                "1. The question seeks specific information from the university course knowledge graph.",
                "2. The query involves entities and relationships defined in the university domain ontology.",
                "3. Properties in the knowledge graph connect courses to their various attributes and relationships.",
                "4. The SPARQL query is constructed to retrieve the requested information efficiently.",
                "5. The result provides valuable insights for academic planning and course selection."
            ]
        
        # Get the thoughts template
        thoughts_template = template["thoughtsTemplate"]
        
        # Extract entity and property URIs from SPARQL
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Create mappings for replacement
        all_mappings = {}
        
        # Add entity mappings
        for i, uri in enumerate(entity_uris):
            key = "entity" if i == 0 else f"entity{i+1}"
            label = self._get_label_from_graph(uri)
            if not label:
                label = self.extract_label_from_uri(uri)
            
            all_mappings[key] = {
                'uri': uri,
                'label': label,
                'prefixed': self.shorten_uri(uri)
            }
        
        # Add value mappings from SPARQL
        numeric_pattern = r'\b(\d+)\b'
        numeric_values = re.findall(numeric_pattern, sparql)
        string_pattern = r'"([^"]+)"'
        string_values = re.findall(string_pattern, sparql)
        
        if numeric_values:
            all_mappings['value'] = {
                'value': numeric_values[0],
                'label': numeric_values[0]
            }
        elif string_values:
            all_mappings['value'] = {
                'value': string_values[0],
                'label': string_values[0]
            }
        
        # Replace placeholders in thoughts
        processed_thoughts = []
        for thought in thoughts_template:
            processed_thought = thought
            
            # Replace each placeholder with the appropriate value
            for placeholder, mapping in all_mappings.items():
                pattern = r'\{' + re.escape(placeholder) + r'\}'
                replacement_value = self.get_appropriate_replacement(thought, placeholder, mapping)
                processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            processed_thoughts.append(processed_thought)
        
        return processed_thoughts

    def get_appropriate_replacement(self, thought_text, placeholder, mapping):
        """
        Determine whether to use URI or label based on the context in the thought
        
        Args:
            thought_text (str): The thought text containing the placeholder
            placeholder (str): The placeholder being replaced
            mapping (dict): The mapping containing uri, label, and prefixed forms
            
        Returns:
            str: The appropriate replacement value
        """
        # Check context around the placeholder to determine appropriate replacement
        thought_lower = thought_text.lower()
        
        # Use URI/prefixed form in these contexts:
        if any(phrase in thought_lower for phrase in [
            "in the ontology",
            "represents the",
            "ns1:",
            "property '",
            "entity '",
            "via the '",
            "using",
            "through"
        ]):
            # Use prefixed form if available, otherwise full URI  
            return mapping.get('prefixed', mapping.get('uri', mapping.get('label', placeholder)))
        
        # Use label form in these contexts:
        elif any(phrase in thought_lower for phrase in [
            "categorized as",
            "belonging to", 
            "classified as",
            "of the '",
            "as a '",
            "category '",
            "group '",
            "method '",
            "course '"
        ]):
            return mapping.get('label', mapping.get('value', placeholder))
        
        # Default to label for most contexts
        return mapping.get('label', mapping.get('value', placeholder))



    def _extract_uris_from_sparql(self, sparql):
        """
        Extract entity and property URIs from SPARQL query
        
        Args:
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entity_uris, property_uris)
        """
        entity_uris = []
        property_uris = []
        
        # Extract URIs in angle brackets
        uri_pattern = r'<([^>]+)>'
        uris = re.findall(uri_pattern, sparql)
        
        # Extract prefixed names (ns1:something)
        prefixed_pattern = r'ns1:([a-zA-Z_][a-zA-Z0-9_]*)'
        prefixed_names = re.findall(prefixed_pattern, sparql)
        
        # Convert prefixed names to full URIs
        ns1_prefix = self.prefixes.get('ns1', 'http://example.org/')
        for name in prefixed_names:
            full_uri = f"{ns1_prefix}{name}"
            uris.append(full_uri)
        
        # Classify URIs as entities or properties
        for uri in uris:
            if self.is_property_uri(uri):
                property_uris.append(uri)
            else:
                entity_uris.append(uri)
        
        return entity_uris, property_uris

    def _get_label_from_graph(self, uri):
        """
        Get rdfs:label for a URI from the RDF graph
        
        Args:
            uri (str): URI to get label for
            
        Returns:
            str: Label or None if not found
        """
        if not self.graph:
            return None
            
        try:
            # Query for rdfs:label
            query = f"""
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT ?label WHERE {{
                    <{uri}> rdfs:label ?label .
                }}
                LIMIT 1
            """
            results = list(self.graph.query(query))
            if results and results[0][0]:
                return str(results[0][0])
        except Exception as e:
            print(f"Error getting label for {uri}: {e}")
        
        return None

    def is_property_uri(self, uri):
        """
        Check if a URI is a property URI
        
        Args:
            uri (str): URI to check
            
        Returns:
            bool: True if it's a property URI
        """
        # Common property indicators
        property_indicators = ['has_', 'is_', 'also_known_as']
        
        for indicator in property_indicators:
            if indicator in uri:
                return True
                
        return False

    def _preprocess_into_tokens(self, q: str) -> list[str]:
        """
        Preprocess question into tokens using NLTK RegexpTokenizer
        
        Args:
            q (str): Question string
            
        Returns:
            list[str]: List of tokens
        """
        tok_pattern = r"\w+"
        tokenizer = RegexpTokenizer(tok_pattern)
        tokenized = tokenizer.tokenize(q)
        result = []
        for tok in tokenized:
            tok = tok.lower()
            if tok not in self.stopwords:
                result.append(tok)
        return result

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """
        Generate n-grams from tokens using NLTK
        
        Args:
            tokens (list[str]): List of tokens
            max_n (int): Maximum n-gram size
            
        Returns:
            list[str]: List of n-grams
        """
        result = []
        
        # Generate unigrams, bigrams, and trigrams using NLTK
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            n_grams = ngrams(tokens, n)
            result.extend([" ".join(ng) for ng in n_grams])
        
        return result

    def _generate_ngrams(self, tokens: list[str], max_n: int = 3) -> list[str]:
        """
        Generate n-grams from tokens similar to EnterprisePropertyRetrieval
        
        Args:
            tokens (list[str]): List of tokens
            max_n (int): Maximum n-gram size
            
        Returns:
            list[str]: List of n-grams
        """
        ngrams = []
        
        # Generate unigrams, bigrams, and trigrams
        for n in range(1, min(max_n + 1, len(tokens) + 1)):
            for i in range(len(tokens) - n + 1):
                ngram = ' '.join(tokens[i:i + n])
                ngrams.append(ngram)
        
        return ngrams

    def _search_entities_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search entities using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of entity results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_entities(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching entities with Weaviate: {e}")
        
        return []

    def _search_properties_weaviate(self, query: str, k: int = 5) -> list[dict]:
        """
        Search properties using Weaviate-based approach
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            
        Returns:
            list[dict]: List of property results with scores
        """
        if self.property_retrieval:
            try:
                df_result = self.property_retrieval.search_properties(query, k=k)
                results = []
                
                for _, row in df_result.iterrows():
                    results.append({
                        'short': row.get('short', ''),
                        'label': row.get('label', ''),
                        'score': row.get('score', 0.0)
                    })
                
                return results
            except Exception as e:
                print(f"Error searching properties with Weaviate: {e}")
        
        return []

    def get_entities_and_properties(self, question, sparql):
        """
        Extract entities and properties from SPARQL query and get their labels using rdfs:label
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entities_list, properties_list, entity_matches, property_matches)
        """
        # Extract actual URIs from SPARQL query
        entity_uris, property_uris = self._extract_uris_from_sparql(sparql)
        
        # Get labels for entities and properties
        entities_list = []
        properties_list = []
        
        # Get entity labels using rdfs:label
        for uri in entity_uris:
            label = self._get_label_from_graph(uri)
            if label:
                entities_list.append(label)
        
        # Get property labels using rdfs:label  
        for uri in property_uris:
            label = self._get_label_from_graph(uri)
            if label:
                properties_list.append(label)
        
        # Get entity and property candidates for entities_matches and properties_matches
        property_candidates = entities_list + properties_list
        related_candidates = self.get_related_candidates(
            question, 
            property_candidates=property_candidates,
            threshold=0.6,
            k=5
        )
        
        # Format entity matches
        entity_matches = []
        if "entities" in related_candidates:
            for entity in related_candidates["entities"]:
                entity_matches.append({
                    "id": entity['short'],
                    "label": entity['label'],
                })
        
        # Format property matches
        property_matches = []
        if "properties" in related_candidates:
            for property in related_candidates["properties"]:
                property_matches.append({
                    "id": property['short'],
                    "label": property['label'],
                })
        
        return entities_list, properties_list, entity_matches, property_matches

    def get_related_candidates(
        self,
        q: str,
        property_candidates: list[str] = [],
        threshold: float = 0.6,
        k: int = 5,
    ) -> dict[str, list[str]]:
        """
        Get related entity and property candidates using n-grams and property candidates
        
        Args:
            q (str): Question string
            property_candidates (list[str]): List of property candidates (entities and properties)
            threshold (float): Score threshold for relevance
            k (int): Number of results per search
            
        Returns:
            dict[str, list[str]]: Dictionary with 'entities' and 'properties' lists
        """
        tokens = self._preprocess_into_tokens(q)
        ngrams = self._generate_ngrams(tokens)
        result = {"entities": [], "properties": []}

        def search(ngram, search_type, threshold=threshold):
            """Search for entities or properties and format results"""

            # Search using the appropriate method
            if search_type == "entities":
                df_res = self._search_entities_weaviate(ngram, k=k)
            else:
                df_res = self._search_properties_weaviate(ngram, k=k)
            
            # Filter by threshold and format results
            filtered_results = []
            for result_item in df_res:
                if result_item['score'] >= threshold:
                    filtered_results.append(result_item)
            
            return search_type, filtered_results

        # Search using n-grams and property candidates
        search_terms = ngrams + property_candidates
        
        for term in search_terms:
            for search_type in result.keys():
                search_result_type, df_res = search(term, search_type)
                if df_res:
                    extracted_items = [{'short': item['short'], 'label': item['label']} for item in df_res]
                    result[search_result_type].extend(extracted_items)
                    
        # Remove duplicates at the end
        for key in result.keys():
            # Convert to list of tuples, use set for deduplication, then back to dicts
            seen = set()
            unique_items = []
            for item in result[key]:
                item_tuple = (item['short'], item['label'])
                if item_tuple not in seen:
                    seen.add(item_tuple)
                    unique_items.append(item)
            result[key] = unique_items
        return result

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
            print(f"\nGenerating {count} questions for complexity level: {complexity}")
            successful_generations = 0
            eligible_templates = [t for t in self.templates if t["complexity"] == complexity]
            
            if not eligible_templates:
                print(f"Warning: No templates found for complexity level: {complexity}")
                continue
            
            while successful_generations < count and len(dataset) < size:
                print(f"  - Attempting to generate questions for complexity '{complexity}' (current count: {successful_generations}/{count})")
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
                            # Generate chain of thoughts for the question-query pair
                            thoughts = self.generate_chain_of_thoughts(instance["question"], instance["sparql"], template)
                            
                            # Get entity matches and property matches
                            entities_list, properties_list, entity_matches, property_matches = self.get_entities_and_properties(instance["question"], instance["sparql"])
                            
                            # Create the dataset entry with additional fields
                            entry = {
                                "id": f"q{id_counter}",
                                "question": instance["question"],
                                "sparql": instance["sparql"],
                                "category": template["category"],
                                "complexity": template["complexity"],
                                "templateId": template["id"],
                                "thoughts": thoughts,
                                "entities": entities_list,
                                "properties": properties_list,
                                "entities_matches": entity_matches,
                                "properties_matches": property_matches
                            }
                            
                            dataset.append(entry)
                            id_counter += 1
                            successful_generations += 1
                            
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

    def extract_credit_value(self, question):
        """
        Extract credit value from question text
        
        Args:
            question (str): Question containing credit value
            
        Returns:
            str: Credit value or "specified"
        """
        # Look for number patterns in the question
        import re
        numbers = re.findall(r'\b(\d+)\b', question)
        if numbers:
            return numbers[0]
        return "specified"

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
        
        # Create a discovery query that includes all placeholders in the SELECT clause
        discovery_query = self.create_all_placeholders_discovery_query(template, placeholders)
        
        # Execute the discovery query
        try:
            results = list(self.graph.query(discovery_query))
            
            if not results:
                print(f"No valid combinations found for template: {template['id']}")
                return None
                
            # Randomly select one complete valid combination of values
            selected = random.choice(results)
            
            # Create a mapping of placeholders to their values from the selected combination
            replacements = {}
            
            # Get the variable names from the query
            query_vars = [str(var) for var in self.graph.query(discovery_query).vars]
            
            # Map variable names from the query results to their indices
            var_indices = {}
            for i, var_name in enumerate(query_vars):
                # Remove the ? prefix from variable names
                if var_name.startswith('?'):
                    var_name = var_name[1:]
                var_indices[var_name] = i
            
            for placeholder in placeholders:
                # Get the index for this placeholder variable
                if placeholder not in var_indices:
                    print(f"Error: Placeholder {placeholder} not found in query results")
                    print(f"Available variables: {list(var_indices.keys())}")
                    return None
                    
                value_index = var_indices[placeholder]
                value = selected[value_index]
                
                # Try to get the label for entity placeholders
                if placeholder.startswith('entity'):
                    entity_uri = str(value)
                    
                    # Look for a label variable for this entity
                    label_var = f"{placeholder}Label"
                    if label_var in var_indices:
                        entity_label = str(selected[var_indices[label_var]])
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
                    if "credits" in template["id"] or "credits" in ' '.join(template["questionTemplates"]).lower():
                        replacement = {
                            "value": value_str,
                            "label": value_str
                        }
                    elif "code" in template["id"] or "code" in ' '.join(template["questionTemplates"]).lower():
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
            
            # Randomly select one of the question templates
            question_template = random.choice(template["questionTemplates"]).strip()
            question = question_template
            sparql = template["sparqlTemplate"].strip()
            
            # Replace placeholders in question and query
            for placeholder, replacement in replacements.items():
                # Create a pattern that can handle whitespace around the placeholder
                pattern = r"{\s*" + re.escape(placeholder) + r"\s*}"
                
                # Replace in question
                replacement_text = replacement.get("label", replacement.get("value", ""))
                question = re.sub(pattern, replacement_text, question_template)
                
                # Replace in SPARQL
                if "uri" in replacement:
                    # Use prefixed notation instead of full URI
                    sparql_value = replacement["value"]  # This is already the prefixed form
                elif "sparqlValue" in replacement:
                    sparql_value = replacement["sparqlValue"]
                else:
                    sparql_value = replacement["value"]
                    
                sparql = re.sub(pattern, sparql_value, sparql)
            
            # Keep prefixed URIs and add PREFIX declarations
            sparql = self.add_prefix_declarations(sparql)
            
            # Format the SPARQL query for readability
            sparql = self.format_sparql(sparql)
            
            return {"question": question, "sparql": sparql}
            
        except Exception as e:
            print(f"Error executing discovery query for template {template['id']}: {e}")
            print("Discovery query:", discovery_query)
            return None

    def create_all_placeholders_discovery_query(self, template, placeholders):
        """
        Create a discovery query that finds valid values for all placeholders by including them in SELECT
        
        Args:
            template (dict): The template to convert
            placeholders (set): Set of placeholders in the template
            
        Returns:
            str: The discovery query
        """
        # Start with basic query components
        select_vars = set()
        where_patterns = []
        sparql_template = template["sparqlTemplate"].strip()
        
        # Extract the WHERE clause from the template
        where_match = re.search(r'WHERE\s*{(.*)}', sparql_template, re.DOTALL | re.IGNORECASE)
        if not where_match:
            print(f"Error: Could not extract WHERE clause from template: {template['id']}")
            return None
            
        # Process each line in the WHERE clause
        where_clause = where_match.group(1).strip()
        for line in where_clause.split('.'):
            line = line.strip()
            if not line:
                continue
                
            # Replace placeholders with variables
            processed_line = line
            for placeholder in placeholders:
                pattern = r'{[\s]*' + re.escape(placeholder) + r'[\s]*}'
                if re.search(pattern, processed_line):
                    var_name = f"?{placeholder}"
                    processed_line = re.sub(pattern, var_name, processed_line)
                    select_vars.add(var_name)
                    
                    # For entity placeholders, also select label
                    if placeholder.startswith('entity'):
                        select_vars.add(f"?{placeholder}Label")
            
            # Find any other variables in the line
            var_pattern = r'\?(\w+)'
            for var_match in re.finditer(var_pattern, processed_line):
                var_name = f"?{var_match.group(1)}"
                select_vars.add(var_name)
            
            where_patterns.append(processed_line + '.')
        
        # Construct the SELECT clause with all unique variables
        select_clause = "SELECT DISTINCT " + " ".join(sorted(select_vars))
        
        # Construct the complete where clause
        where_clause = "\n  ".join(where_patterns)
        
        # Construct the complete discovery query
        discovery_query = f"{select_clause} WHERE {{\n  {where_clause}"
        
        # Add OPTIONAL label patterns for entity placeholders
        for placeholder in placeholders:
            if placeholder.startswith('entity'):
                discovery_query += f"\n  OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label . }}"
        
        # Close the query
        discovery_query += "\n}"
        
        # Keep prefixed URIs and add PREFIX declarations
        discovery_query = self.add_prefix_declarations(discovery_query)
        
        return discovery_query

    def extract_placeholders(self, template):
        """
        Extract all placeholders from template (text in curly braces)
        
        Args:
            template (dict): Template with question and SPARQL
            
        Returns:
            set: Set of placeholder names
        """
        placeholders = set()
        
        # For Python triple-quoted strings, we need to handle whitespace
        # Check all question templates
        for question_template in template["questionTemplates"]:
            # Use a pattern that matches only text inside curly braces
            pattern = r"{\s*([a-zA-Z0-9_]+)\s*}"
            
            # Search in question template
            for match in re.finditer(pattern, question_template.strip()):
                placeholders.add(match.group(1).strip())
        
        # Check the SPARQL template
        sparql_template = template["sparqlTemplate"].strip()
        pattern = r"{\s*([a-zA-Z0-9_]+)\s*}"
        
        # Search in SPARQL template
        for match in re.finditer(pattern, sparql_template):
            placeholders.add(match.group(1).strip())
        
        return placeholders

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
        question_templates_text = ' '.join(template["questionTemplates"]).lower()
        
        # Match the pattern where value is used in the SPARQL
        value_pattern = r'{' + placeholder + r'}'
        
        # University-specific value handling
        if "credits" in template["id"] or "credits" in question_templates_text:
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
                
        elif "code" in template["id"] or "code" in question_templates_text:
            # For course codes, find actual course codes in the data
            query = """
                SELECT DISTINCT ?code
                WHERE {
                    ?course <http://example.org/has_course_code> ?code .
                }
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
        question_templates_text = ' '.join(template["questionTemplates"]).lower()
        
        # Special handling for university course data
        if template.get("category") == "university":
            if "credit" in template["id"] or "credit" in question_templates_text:
                return self.select_credit_value()
            elif "code" in template["id"] or "code" in question_templates_text:
                return self.select_course_code_value()
            
        # Default to a generic value
        dummy_value = random.randint(1, 10)
        return {"value": str(dummy_value), "label": str(dummy_value)}

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
        
        # DON'T remove PREFIX declarations - keep them
        # sparql = re.sub(r'PREFIX\s+\w+:\s+<[^>]+>\s*', '', sparql)  # REMOVED THIS LINE
        
        # Clean up multiple spaces
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

    def add_prefix_declarations(self, sparql):
        """
        Add PREFIX declarations to SPARQL query based on used prefixes
        
        Args:
            sparql (str): SPARQL query potentially containing prefixed names
            
        Returns:
            str: SPARQL query with PREFIX declarations prepended
        """
        # Find which prefixes are actually used in the query
        used_prefixes = set()
        
        for prefix, namespace in self.prefixes.items():
            # Look for prefix usage in the query (prefix followed by colon)
            pattern = r'\b' + re.escape(prefix) + r':'
            if re.search(pattern, sparql):
                used_prefixes.add(prefix)
        
        # Build PREFIX declarations for used prefixes
        prefix_declarations = []
        for prefix in sorted(used_prefixes):  # Sort for consistent output
            namespace = self.prefixes[prefix]
            prefix_declarations.append(f"PREFIX {prefix}: <{namespace}>")
        
        # Prepend PREFIX declarations to the query
        if prefix_declarations:
            return "\n".join(prefix_declarations) + "\n" + sparql
        
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