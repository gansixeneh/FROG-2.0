"""
NL2SPARQL - Natural Language to SPARQL Dataset Generator - Modified for Fuseki Server

This version supports context-aware entity selection, generating queries with real entities from
the knowledge graph that match the template structure using a discovery-based approach.
"""

import json
import random
import re
import datetime
import csv
import io
from sparql import SparqlExecutor

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
        
        # Create a SPARQL executor to connect to Fuseki
        self.sparql_exec = SparqlExecutor()
    
    # ... [rest of the class, replacing all direct graph access with sparql_exec.execute_query] ...

    def create_discovery_query(self, template, placeholders):
        """
        Create a discovery query to find valid values for placeholders
        
        Args:
            template (dict): The template to use
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
            where_clause = re.sub(pattern, f"?{placeholder}", where_clause)
        
        # Build SELECT clause with all placeholders
        select_vars = []
        
        # Add the result variable from the original query
        result_var_match = re.search(r'SELECT\s+(?:\(.*\)\s+AS\s+)?(\?\w+)', sparql_template, re.IGNORECASE)
        if result_var_match:
            result_var = result_var_match.group(1)
            if "COUNT" not in result_var and "count" not in result_var:
                select_vars.append(result_var)
        
        # Add all placeholder variables to SELECT clause
        for placeholder in placeholders:
            select_vars.append(f"?{placeholder}")
            # For entity placeholders, also select label if available
            if placeholder.startswith('entity'):
                select_vars.append(f"?{placeholder}Label")
        
        # Construct the SELECT clause with all variables
        select_clause = "SELECT DISTINCT " + " ".join(select_vars)
        
        # Construct the complete discovery query
        discovery_query = f"{select_clause} WHERE {{ {where_clause}"
        
        # Add OPTIONAL label patterns for entity placeholders
        for placeholder in placeholders:
            if placeholder.startswith('entity'):
                discovery_query += f" OPTIONAL {{ ?{placeholder} rdfs:label ?{placeholder}Label . }}"
        
        # Close the query with increased LIMIT to ensure finding valid combinations
        discovery_query += " } LIMIT 1000"
        
        # Replace all prefixed URIs with full URIs for consistency
        for prefix, uri in self.prefixes.items():
            pattern = r'\b' + re.escape(prefix) + r':([a-zA-Z0-9_]+)\b'
            discovery_query = re.sub(pattern, r'<' + uri + r'\1>', discovery_query)
        
        return discovery_query
    
    def execute_discovery_query(self, query):
        """
        Execute a discovery query to find valid placeholder values
        
        Args:
            query (str): The discovery query to execute
            
        Returns:
            list: Query results
        """
        try:
            results = self.sparql_exec.execute_query(query, return_format="dict")
            return results
        except Exception as e:
            print(f"Error executing discovery query: {e}")
            return []