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
        
        # Extract entity mappings from the SPARQL query
        entity_mappings = self.extract_entity_mappings_from_sparql(sparql, question)
        
        # Extract value mappings from the SPARQL query
        value_mappings = self.extract_value_mappings_from_sparql(sparql, question)
        
        # Combine all mappings
        all_mappings = {**entity_mappings, **value_mappings}
        
        # Replace placeholders in thoughts
        processed_thoughts = []
        for thought in thoughts_template:
            processed_thought = thought
            
            # Replace each placeholder with the appropriate value (label or URI based on context)
            for placeholder, mapping in all_mappings.items():
                pattern = r'\{' + re.escape(placeholder) + r'\}'
                
                # Determine whether to use URI or label based on context
                replacement_value = self.get_appropriate_replacement(thought, placeholder, mapping)
                
                processed_thought = re.sub(pattern, replacement_value, processed_thought)
            
            processed_thoughts.append(processed_thought)
        
        return processed_thoughts

    def extract_entity_mappings_from_sparql(self, sparql, question):
        """
        Extract entity mappings from SPARQL query
        
        Args:
            sparql (str): SPARQL query
            question (str): Natural language question
            
        Returns:
            dict: Mapping of placeholders to entity info
        """
        entity_mappings = {}
        
        # Find all URI patterns in the SPARQL query
        uri_pattern = r'<([^>]+)>'
        uris = re.findall(uri_pattern, sparql)
        
        # Find all prefixed names in the SPARQL query  
        prefixed_pattern = r'ns1:([a-zA-Z_][a-zA-Z0-9_]*)'
        prefixed_names = re.findall(prefixed_pattern, sparql)
        
        # Convert prefixed names to full URIs
        full_uris = []
        for name in prefixed_names:
            if "ns1" in self.prefixes:
                full_uri = f"{self.prefixes['ns1']}{name}"
                full_uris.append(full_uri)
        
        # Combine all URIs
        all_uris = uris + full_uris
        
        # Filter out property URIs (those containing 'has_' or similar patterns)
        entity_uris = [uri for uri in all_uris if not self.is_property_uri(uri)]
        
        # Create mappings for entity placeholders
        entity_counter = 0
        for uri in entity_uris:
            # Get label for this URI
            label = self.get_entity_label_from_uri(uri)
            
            # Create mapping for base 'entity' placeholder
            if entity_counter == 0:
                entity_mappings['entity'] = {
                    'uri': uri,
                    'label': label,
                    'prefixed': self.shorten_uri(uri)
                }
            
            # Create mapping for numbered entity placeholders
            entity_counter += 1
            entity_mappings[f'entity{entity_counter}'] = {
                'uri': uri,
                'label': label,
                'prefixed': self.shorten_uri(uri)
            }
        
        return entity_mappings

    def extract_value_mappings_from_sparql(self, sparql, question):
        """
        Extract value mappings from SPARQL query
        
        Args:
            sparql (str): SPARQL query
            question (str): Natural language question
            
        Returns:
            dict: Mapping of placeholders to value info
        """
        value_mappings = {}
        
        # Find numeric values
        numeric_pattern = r'\b(\d+)\b'
        numeric_values = re.findall(numeric_pattern, sparql)
        
        # Find string literals
        string_pattern = r'"([^"]+)"'
        string_values = re.findall(string_pattern, sparql)
        
        # Create mapping for 'value' placeholder
        if numeric_values:
            value_mappings['value'] = {
                'value': numeric_values[0],
                'label': numeric_values[0]
            }
        elif string_values:
            value_mappings['value'] = {
                'value': string_values[0],
                'label': string_values[0]
            }
        
        return value_mappings

    def is_property_uri(self, uri):
        """
        Check if a URI is a property URI
        
        Args:
            uri (str): URI to check
            
        Returns:
            bool: True if it's a property URI
        """
        # Common property indicators
        property_indicators = ['has_', 'is_', 'also_known_as', 'belongs_to']
        
        for indicator in property_indicators:
            if indicator in uri:
                return True
                
        return False

    def get_entity_label_from_uri(self, uri):
        """
        Get human-readable label for an entity URI
        
        Args:
            uri (str): Entity URI
            
        Returns:
            str: Human-readable label
        """
        # Try to get label from graph if available
        if self.graph:
            try:
                query = f"""
                    SELECT ?label WHERE {{
                        <{uri}> rdfs:label ?label .
                    }}
                    LIMIT 1
                """
                results = list(self.graph.query(query))
                if results and results[0][0]:
                    return str(results[0][0])
            except Exception:
                pass
        
        # Fallback to extracting from URI
        return self.extract_label_from_uri(uri)

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

    def get_entities_and_properties(self, question, sparql):
        """
        Extract entities and properties from question and query and get their labels
        
        Args:
            question (str): Natural language question
            sparql (str): SPARQL query
            
        Returns:
            tuple: (entity_matches, property_matches) dictionaries
        """
        entity_matches = {}
        property_matches = {}
        
        # Extract entity URIs from the SPARQL query
        uri_pattern = r'<([^>]+)>'
        entity_uris = re.findall(uri_pattern, sparql)
        
        # For each entity URI, get its label using rdfs:label
        for uri in entity_uris:
            # Skip property URIs
            if "has_" in uri or "#" in uri:
                continue
                
            # Query for entity label
            if self.graph:
                try:
                    query = f"""
                        SELECT ?label WHERE {{
                            <{uri}> rdfs:label ?label .
                        }}
                        LIMIT 1
                    """
                    results = list(self.graph.query(query))
                    if results and results[0][0]:
                        label = str(results[0][0])
                        
                        # Try to find this entity in the question
                        entity_name = self.extract_label_from_uri(uri)
                        if entity_name.lower() in question.lower() or label.lower() in question.lower():
                            # Use the label or extract from URI
                            entity_key = label if label else entity_name
                            
                            # Get entity description if available
                            description = self.get_entity_description(uri)
                            
                            if entity_key not in entity_matches:
                                entity_matches[entity_key] = []
                                
                            entity_matches[entity_key].append({
                                "id": uri.split('/')[-1],
                                "label": label if label else entity_name,
                                "description": description,
                                "url": f"//www.wikidata.org/wiki/{uri.split('/')[-1]}"
                            })
                except Exception as e:
                    print(f"Error getting label for entity {uri}: {e}")
            
            # If we couldn't get a label from the graph, use the URI
            if not entity_matches:
                entity_name = self.extract_label_from_uri(uri)
                entity_matches[entity_name] = [{
                    "id": uri.split('/')[-1],
                    "label": entity_name,
                    "description": "",
                    "url": f"//www.wikidata.org/wiki/{uri.split('/')[-1]}"
                }]
        
        # Extract property URIs from the SPARQL query
        property_uris = [uri for uri in entity_uris if "has_" in uri or "#" in uri]
        
        # For each property URI, get its label
        for uri in property_uris:
            # Query for property label
            if self.graph:
                try:
                    query = f"""
                        SELECT ?label WHERE {{
                            <{uri}> rdfs:label ?label .
                        }}
                        LIMIT 1
                    """
                    results = list(self.graph.query(query))
                    if results and results[0][0]:
                        label = str(results[0][0])
                        
                        # Use the label or extract from URI
                        prop_key = label if label else self.extract_label_from_uri(uri)
                        
                        # Get property description if available
                        description = self.get_property_description(uri)
                        
                        if prop_key not in property_matches:
                            property_matches[prop_key] = []
                            
                        property_matches[prop_key].append({
                            "id": uri.split('/')[-1],
                            "label": label if label else self.extract_label_from_uri(uri),
                            "description": description,
                            "url": f"//www.wikidata.org/wiki/Property:{uri.split('/')[-1]}"
                        })
                except Exception as e:
                    print(f"Error getting label for property {uri}: {e}")
            
            # If we couldn't get a label from the graph, use the URI
            if not property_matches:
                prop_name = self.extract_label_from_uri(uri)
                # Convert has_credits to "credits"
                if prop_name.startswith("has_"):
                    prop_name = prop_name[4:]
                property_matches[prop_name] = [{
                    "id": uri.split('/')[-1],
                    "label": prop_name,
                    "description": "",
                    "url": f"//www.wikidata.org/wiki/Property:{uri.split('/')[-1]}"
                }]
        
        return entity_matches, property_matches

    # ... rest of the methods remain the same ...
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
                            # Generate chain of thoughts for the question-query pair
                            thoughts = self.generate_chain_of_thoughts(instance["question"], instance["sparql"], template)
                            
                            # Get entity matches and property matches
                            entity_matches, property_matches = self.get_entities_and_properties(instance["question"], instance["sparql"])
                            
                            # Create the dataset entry with additional fields
                            entry = {
                                "id": f"q{id_counter}",
                                "question": instance["question"],
                                "sparql": instance["sparql"],
                                "category": template["category"],
                                "complexity": template["complexity"],
                                "templateId": template["id"],
                                "thoughts": thoughts,
                                "entities": list(entity_matches.keys()),
                                "properties": list(property_matches.keys()),
                                "entities_matches": entity_matches,
                                "properties_matches": property_matches
                            }
                            
                            dataset.append(entry)
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
                                    
                                    # Generate chain of thoughts for the variation
                                    var_thoughts = self.generate_chain_of_thoughts(variation, instance["sparql"], template)
                                    
                                    # Get entity matches and property matches for the variation
                                    var_entity_matches, var_property_matches = self.get_entities_and_properties(variation, instance["sparql"])
                                    
                                    dataset.append({
                                        "id": f"q{id_counter}",
                                        "question": variation,
                                        "sparql": instance["sparql"],
                                        "category": template["category"],
                                        "complexity": template["complexity"],
                                        "templateId": template["id"],
                                        "isVariation": True,
                                        "thoughts": var_thoughts,
                                        "entities": list(var_entity_matches.keys()),
                                        "properties": list(var_property_matches.keys()),
                                        "entities_matches": var_entity_matches,
                                        "properties_matches": var_property_matches
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

    def get_entity_description(self, uri):
        """
        Get description for an entity
        
        Args:
            uri (str): Entity URI
            
        Returns:
            str: Entity description or empty string
        """
        if not self.graph:
            return ""
            
        try:
            # Try to get a description using common properties
            for desc_prop in ["rdfs:comment", "schema:description", "dcterms:description"]:
                query = f"""
                    SELECT ?desc WHERE {{
                        <{uri}> {desc_prop} ?desc .
                    }}
                    LIMIT 1
                """
                results = list(self.graph.query(query))
                if results and results[0][0]:
                    return str(results[0][0])
            
            # Fallback - construct a simple description
            entity_type_query = f"""
                SELECT ?type WHERE {{
                    <{uri}> a ?type .
                }}
                LIMIT 1
            """
            type_results = list(self.graph.query(entity_type_query))
            if type_results and type_results[0][0]:
                type_uri = str(type_results[0][0])
                type_label = self.extract_label_from_uri(type_uri)
                return f"{type_label}"
                
            return ""
        except Exception as e:
            print(f"Error getting description for entity {uri}: {e}")
            return ""

    def get_property_description(self, uri):
        """
        Get description for a property
        
        Args:
            uri (str): Property URI
            
        Returns:
            str: Property description or empty string
        """
        if not self.graph:
            return ""
            
        try:
            # Try to get a description using common properties
            for desc_prop in ["rdfs:comment", "schema:description", "dcterms:description"]:
                query = f"""
                    SELECT ?desc WHERE {{
                        <{uri}> {desc_prop} ?desc .
                    }}
                    LIMIT 1
                """
                results = list(self.graph.query(query))
                if results and results[0][0]:
                    return str(results[0][0])
            
            # For properties, create a description based on domain and range
            domain_query = f"""
                SELECT ?domain WHERE {{
                    <{uri}> rdfs:domain ?domain .
                }}
                LIMIT 1
            """
            domain_results = list(self.graph.query(domain_query))
            
            range_query = f"""
                SELECT ?range WHERE {{
                    <{uri}> rdfs:range ?range .
                }}
                LIMIT 1
            """
            range_results = list(self.graph.query(range_query))
            
            if domain_results and domain_results[0][0] and range_results and range_results[0][0]:
                domain_uri = str(domain_results[0][0])
                range_uri = str(range_results[0][0])
                domain_label = self.extract_label_from_uri(domain_uri)
                range_label = self.extract_label_from_uri(range_uri)
                return f"property that links {domain_label} to {range_label}"
                
            return ""
        except Exception as e:
            print(f"Error getting description for property {uri}: {e}")
            return ""

    def instantiate_template_with_discovery(self, template):
        """
        Instantiate a template using a discovery-based approach that guarantees valid placeholder values
        
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
        
        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':(\w+)\b'
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
        
        # Randomly select one of the question templates
        question_template = random.choice(template["questionTemplates"]).strip()
        sparql = template["sparqlTemplate"].strip()
        
        # Replace placeholders in question and query
        for placeholder, replacement in replacements.items():
            # Create a pattern that can handle whitespace around the placeholder
            pattern = r"{[\s]*" + re.escape(placeholder) + r"[\s]*}"
            
            # Replace in question
            replacement_text = replacement.get("label", replacement.get("value", ""))
            question = re.sub(pattern, replacement_text, question_template)
            
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
                    question_templates_text = ' '.join(template["questionTemplates"]).lower()
                    
                    if "research-group" in template["id"] or placeholder == "entity1" and "research" in question_templates_text:
                        replacement = self.select_entity_by_type("ns1:research_lab")
                    elif "evaluation" in template["id"] or placeholder in ["entity1", "entity2", "entity3"] and "evaluation" in question_templates_text:
                        replacement = self.select_entity_by_type("ns1:evaluation")
                    elif "category" in template["id"] or placeholder in ["entity2", "entity3"] and "categor" in question_templates_text:
                        replacement = self.select_entity_by_type("ns1:course_category")
                    else:
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
                    question_templates_text = ' '.join(template["questionTemplates"]).lower()
                    
                    if "credits" in template["id"] or "credits" in question_templates_text:
                        # For credit-related templates, use realistic credit values
                        replacement = self.select_credit_value()
                    elif "code" in template["id"] or "code" in question_templates_text:
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
        
        # Get the combined text of all question templates
        question_templates_text = ' '.join(template["questionTemplates"]).lower()
        
        # First check if our schema info has this property
        if "properties" in self.schema_info:
            # Try to find a matching property from the schema
            if "credit" in template["id"] or "credit" in placeholder or "credit" in question_templates_text:
                prop = self.find_property_by_name("has_credits")
                if prop:
                    return prop
                
            elif "prerequisite" in template["id"] or "prerequisite" in placeholder or "prerequisite" in question_templates_text:
                prop = self.find_property_by_name("has_prerequisite_course")
                if prop:
                    return prop
                
            elif "code" in template["id"] or "code" in placeholder or "code" in question_templates_text:
                prop = self.find_property_by_name("has_course_code")
                if prop:
                    return prop
                
            elif "evaluation" in template["id"] or "evaluation" in placeholder or "evaluation" in question_templates_text:
                prop = self.find_property_by_name("has_evaluation_method")
                if prop:
                    return prop
                
            elif "research" in template["id"] or "research" in placeholder or "research" in question_templates_text:
                prop = self.find_property_by_name("has_research_group")
                if prop:
                    return prop
                
            elif "category" in template["id"] or "category" in placeholder or "category" in question_templates_text:
                prop = self.find_property_by_name("has_course_category")
                if prop:
                    return prop
                
            elif "nickname" in template["id"] or "nickname" in placeholder or "nickname" in question_templates_text:
                prop = self.find_property_by_name("also_known_as")
                if prop:
                    return prop
        
        # If we don't have the property in schema info, use our predefined ones
        if "credit" in template["id"] or "credit" in placeholder or "credit" in question_templates_text:
            return university_properties["credits"]
            
        elif "prerequisite" in template["id"] or "prerequisite" in placeholder or "prerequisite" in question_templates_text:
            return university_properties["prerequisite"]
            
        elif "code" in template["id"] or "code" in placeholder or "code" in question_templates_text:
            return university_properties["code"]
            
        elif "evaluation" in template["id"] or "evaluation" in placeholder or "evaluation" in question_templates_text:
            return university_properties["evaluation"]
            
        elif "research" in template["id"] or "research" in placeholder or "research" in question_templates_text:
            return university_properties["research"]
            
        elif "category" in template["id"] or "category" in placeholder or "category" in question_templates_text:
            return university_properties["category"]
            
        elif "nickname" in template["id"] or "nickname" in placeholder or "nickname" in question_templates_text:
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