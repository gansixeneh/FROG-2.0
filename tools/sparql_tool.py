from typing import Optional, Dict, Any, List, Tuple
from langchain_core.tools import BaseTool
from SPARQLWrapper import SPARQLWrapper, JSON
import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TriplePattern:
    """Represents a SPARQL triple pattern with subject, predicate, and object."""
    subject: str
    predicate: str
    obj: str
    is_wdt_pattern: bool = False
    pattern_type: str = None


class QueryParser:
    """Parser for SPARQL queries to extract and manipulate components."""
    
    @staticmethod
    def extract_query_parts(query: str) -> Tuple[str, str, str, str]:
        """
        Extract the different parts of a SPARQL query.
        
        Args:
            query: The SPARQL query string
            
        Returns:
            Tuple containing (before_select, select_vars, where_content, after_where)
        """
        # Extract the SELECT part and the WHERE clause
        select_match = re.search(r'SELECT\s+(.*?)\s+WHERE\s*\{', query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return "", "", "", query  # Not a standard SELECT query
        
        select_vars = select_match.group(1).strip()
        before_select = query[:select_match.start()]
        
        # Find the opening and closing braces of the WHERE clause
        where_start_index = query.find('{')
        if where_start_index == -1:
            return before_select, select_vars, "", query[select_match.end():]
        
        # Find the closing brace, accounting for nested braces
        where_end_index = -1
        brace_count = 1
        for i in range(where_start_index + 1, len(query)):
            if query[i] == '{':
                brace_count += 1
            elif query[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    where_end_index = i
                    break
        
        if where_end_index == -1:
            return before_select, select_vars, "", query[select_match.end():]
        
        # Extract the WHERE clause content
        where_content = query[where_start_index + 1:where_end_index].strip()
        after_where = query[where_end_index + 1:]
        
        return before_select, select_vars, where_content, after_where
    
    @staticmethod
    def parse_triple_patterns(where_content: str) -> List[str]:
        """
        Parse the WHERE clause content into pattern strings.
        
        Args:
            where_content: The content of the WHERE clause
            
        Returns:
            A list of pattern strings
        """
        patterns = []
        current_pattern = ""
        brace_level = 0
        in_filter = False
        
        i = 0
        while i < len(where_content):
            char = where_content[i]
            
            # Check for FILTER keyword
            if i + 6 < len(where_content) and where_content[i:i+6].upper() == "FILTER":
                in_filter = True
            
            # Check for opening brace
            if char == '{':
                brace_level += 1
            
            # Check for closing brace
            elif char == '}':
                brace_level -= 1
                if brace_level == 0:
                    in_filter = False
            
            # Add character to current pattern
            current_pattern += char
            
            # Check for pattern end
            if char == '.' and brace_level == 0 and not in_filter:
                # Remove trailing dot
                current_pattern = current_pattern[:-1].strip()
                if current_pattern:
                    patterns.append(current_pattern)
                current_pattern = ""
            
            i += 1
        
        # Add the last pattern if not empty
        if current_pattern.strip():
            patterns.append(current_pattern.strip())
        
        return patterns
    
    @staticmethod
    def analyze_triple_pattern(pattern: str) -> Optional[TriplePattern]:
        """
        Analyze a triple pattern string to extract its components.
        
        Args:
            pattern: The triple pattern string
            
        Returns:
            A TriplePattern object or None if not recognized
        """
        # Pattern 1: Entity -> Property -> Variable (wd:Q142 wdt:P35 ?president)
        wdt_entity_match = re.search(r'(wd:Q\d+)\s+(wdt:P\d+)\s+(\?[a-zA-Z0-9_]+)', pattern)
        if wdt_entity_match:
            return TriplePattern(
                subject=wdt_entity_match.group(1),
                predicate=wdt_entity_match.group(2),
                obj=wdt_entity_match.group(3),
                is_wdt_pattern=True,
                pattern_type="entity_to_var"
            )
        
        # Pattern 2: Variable -> Property -> Entity (?mountain wdt:P31 wd:Q8502)
        wdt_var_to_entity_match = re.search(r'(\?[a-zA-Z0-9_]+)\s+(wdt:P\d+)\s+(wd:Q\d+)', pattern)
        if wdt_var_to_entity_match:
            return TriplePattern(
                subject=wdt_var_to_entity_match.group(1),
                predicate=wdt_var_to_entity_match.group(2),
                obj=wdt_var_to_entity_match.group(3),
                is_wdt_pattern=True,
                pattern_type="var_to_entity"
            )
        
        # Pattern 3: Variable -> Property -> Variable (?mountain wdt:P4552 ?height)
        wdt_var_to_var_match = re.search(r'(\?[a-zA-Z0-9_]+)\s+(wdt:P\d+)\s+(\?[a-zA-Z0-9_]+)', pattern)
        if wdt_var_to_var_match:
            return TriplePattern(
                subject=wdt_var_to_var_match.group(1),
                predicate=wdt_var_to_var_match.group(2),
                obj=wdt_var_to_var_match.group(3),
                is_wdt_pattern=True,
                pattern_type="var_to_var"
            )
        
        # Return the pattern as-is if it doesn't match any recognized pattern
        return None


class ReferenceEnhancer:
    """Handles enhancing SPARQL queries with reference information."""
    
    @staticmethod
    def generate_reference_patterns(pattern: TriplePattern, counter: int) -> Tuple[List[str], List[str]]:
        """
        Generate reference patterns for a triple pattern.
        
        Args:
            pattern: The TriplePattern object
            counter: A counter to ensure unique variable names
            
        Returns:
            Tuple of (reference_patterns, new_select_vars)
        """
        statement_var = f"?statement{counter}"
        ref_url_var = f"?refUrl{counter}"
        ref_date_var = f"?refDate{counter}"
        
        # Extract property ID from predicate (remove the 'wdt:' prefix)
        property_id = pattern.predicate[4:]
        
        ref_patterns = [
            f"{pattern.subject} p:{property_id} {statement_var}",
            f"{statement_var} ps:{property_id} {pattern.obj}",
            f"OPTIONAL {{",
            f"  {statement_var} prov:wasDerivedFrom ?reference{counter}",
            f"  OPTIONAL {{ ?reference{counter} pr:P854 {ref_url_var} }}",
            f"  OPTIONAL {{ ?reference{counter} pr:P813 {ref_date_var} }}",
            f"}}"
        ]
        
        new_select_vars = [ref_url_var, ref_date_var]
        
        return ref_patterns, new_select_vars


class QueryFormatter:
    """Provides functionality to format and standardize SPARQL queries."""
    
    @staticmethod
    def format_query(query: str) -> str:
        """
        Format a SPARQL query to standardize its structure.
        
        Args:
            query: The SPARQL query string to format
            
        Returns:
            A formatted SPARQL query string
        """
        # Extract query parts
        before_select, select_vars, where_content, after_where = QueryParser.extract_query_parts(query)
        
        # If not a standard SELECT query, return as is with minimal formatting
        if not where_content:
            return query.strip()
        
        # Parse the WHERE clause into patterns
        pattern_strings = QueryParser.parse_triple_patterns(where_content)
        
        # Format the SELECT clause
        formatted_select = f"SELECT {select_vars}"
        
        # Format the WHERE clause
        formatted_where = "WHERE {\n"
        
        # Format each pattern
        for pattern in pattern_strings:
            # Determine indentation level based on pattern content
            indent = "  "
            if pattern.strip().startswith("OPTIONAL") or pattern.strip().startswith("SERVICE"):
                formatted_where += f"{indent}{pattern} .\n"
            elif pattern.strip() == "}" or pattern.strip() == "{":
                formatted_where += f"{indent}{pattern}\n"
            else:
                formatted_where += f"{indent}{pattern} .\n"
        
        formatted_where += "}"
        
        # Format content after WHERE clause
        formatted_after = after_where.strip()
        
        # Combine the parts
        formatted_query = before_select.strip()
        if formatted_query and not formatted_query.endswith("\n"):
            formatted_query += "\n"
        
        formatted_query += formatted_select + "\n" + formatted_where
        
        if formatted_after:
            formatted_query += "\n" + formatted_after
        
        # Fix any double periods
        formatted_query = formatted_query.replace("..", ".")
        formatted_query = formatted_query.replace(". .", ".")
        
        return formatted_query


class ExecuteSPARQLTool(BaseTool):
    """Tool for executing SPARQL queries against Wikidata with reference enhancement."""
    
    name: str = "execute_sparql"
    description: str = """Execute a SPARQL query against Wikidata.
    
    Args:
        query: The complete SPARQL query string to execute
        limit: Maximum number of results to return (default: 5)
        include_references: Whether to automatically enhance the query to include references (default: True)
    
    Returns:
        The query results or error information if the query fails
    """
    
    def __init__(self):
        super().__init__()
        # These are not Pydantic fields, just instance attributes
        self._endpoint = "https://query.wikidata.org/sparql"
        self._sparql = SPARQLWrapper(self._endpoint)
        self._sparql.setReturnFormat(JSON)
        # Set a user agent to be respectful to the Wikidata service
        self._sparql.addCustomHttpHeader("User-Agent", "LangChain Wikidata Agent/1.0")
    
    def _run(self, query: str, limit: int = 5, include_references: bool = True, format_query: bool = True) -> Dict[str, Any]:
        """
        Execute a SPARQL query against Wikidata
        
        Args:
            query: The SPARQL query string
            limit: Maximum number of results to return (default: 5)
            include_references: Whether to automatically enhance the query to include references (default: True)
            format_query: Whether to format and standardize the query before execution (default: True)
            
        Returns:
            The query results or error information
        """
        try:
            # Convert limit to integer explicitly to avoid float notation
            limit_value = int(limit)
            
            # Enhance the query to include references if requested
            if include_references:
                query = self._enhance_query_with_references(query)
            
            # Add limit if not already present in the query
            if "LIMIT" not in query.upper():
                query += f" LIMIT {limit_value}"
            
            # Format the query if requested
            if format_query:
                query = QueryFormatter.format_query(query)
            
            # Execute the query
            self._sparql.setQuery(query)
            results = self._sparql.query().convert()
            
            return self._process_results(results, query)
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e).split('\n')[0],
                "query": query
            }
    
    def _process_results(self, results: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Process and format the query results.
        
        Args:
            results: The raw query results
            query: The query that was executed
            
        Returns:
            Processed results with more readable format
        """
        processed_results = []
        
        if "results" in results and "bindings" in results["results"]:
            bindings = results["results"]["bindings"]
            
            for binding in bindings:
                processed_binding = {}
                for key, value in binding.items():
                    # Format dates if they look like ISO format
                    if 'date' in key.lower() and value.get("value", "").endswith('Z'):
                        try:
                            date_value = value.get("value", "")
                            # Parse ISO 8601 date
                            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                            # Format as a readable date
                            processed_binding[key] = dt.strftime("%B %d, %Y")
                        except (ValueError, TypeError):
                            # If conversion fails, keep the original value
                            processed_binding[key] = value.get("value", "")
                    else:
                        processed_binding[key] = value.get("value", "")
                
                processed_results.append(processed_binding)
            
            return {
                "success": True,
                "results": processed_results,
                "count": len(processed_results),
                "raw_results": bindings,  # Include raw results for reference
                "enhanced_query": query  # Include the enhanced query in the response
            }
        else:
            # Handle other types of results
            return {
                "success": True,
                "results": results,
                "count": 1,
                "enhanced_query": query
            }
    
    def _enhance_query_with_references(self, query: str) -> str:
        """
        Enhance a SPARQL query to include reference information
        
        Args:
            query: The original SPARQL query
            
        Returns:
            An enhanced query that includes reference information
        """
        # Extract query parts
        before_select, select_vars, where_content, after_where = QueryParser.extract_query_parts(query)
        
        # If not a standard SELECT query, return as is
        if not where_content:
            return query
        
        # Parse the WHERE clause into patterns
        pattern_strings = QueryParser.parse_triple_patterns(where_content)
        
        # Process each pattern and identify wdt: patterns
        enhanced_patterns = []
        new_select_vars = []
        counter = 1
        
        for pattern_str in pattern_strings:
            # Keep the original pattern
            enhanced_patterns.append(pattern_str)
            
            # Analyze the pattern
            triple_pattern = QueryParser.analyze_triple_pattern(pattern_str)
            
            # Skip non-wdt patterns
            if not triple_pattern or not triple_pattern.is_wdt_pattern:
                continue
            
            # Generate reference patterns
            ref_patterns, vars_to_add = ReferenceEnhancer.generate_reference_patterns(triple_pattern, counter)
            enhanced_patterns.extend(ref_patterns)
            new_select_vars.extend(vars_to_add)
            counter += 1
        
        # Update the SELECT clause to include new variables
        if new_select_vars:
            for var in new_select_vars:
                if var not in select_vars:
                    select_vars += f" {var}"
        
        # Rebuild the query
        enhanced_query = self._rebuild_query(before_select, select_vars, enhanced_patterns, after_where)
        
        return enhanced_query
    
    def _rebuild_query(self, before_select: str, select_vars: str, patterns: List[str], after_where: str) -> str:
        """
        Rebuild the query from its components.
        
        Args:
            before_select: Content before the SELECT clause
            select_vars: Variables in the SELECT clause
            patterns: List of pattern strings for the WHERE clause
            after_where: Content after the WHERE clause
            
        Returns:
            The rebuilt query string
        """
        # Build the SELECT clause
        select_clause = f"SELECT {select_vars} WHERE {{"
        
        # Build the query with proper formatting
        enhanced_query = before_select + select_clause + "\n"
        
        # Add each pattern with proper formatting
        for i, pattern in enumerate(patterns):
            if pattern.startswith("OPTIONAL {") or pattern.startswith("FILTER"):
                enhanced_query += f"  {pattern}"
            elif pattern.strip().startswith("{") or pattern.strip().startswith("}"):
                enhanced_query += f"  {pattern}"
            else:
                enhanced_query += f"  {pattern} ."
            
            # Add newline after each pattern
            if i < len(patterns) - 1:
                enhanced_query += "\n"
        
        enhanced_query += "\n}" + after_where
        
        # Fix any double periods
        enhanced_query = enhanced_query.replace("..}", ".}")
        enhanced_query = enhanced_query.replace(".. ", ". ")
        
        return enhanced_query

if __name__ == '__main__':
    x = ExecuteSPARQLTool()
    query = """
    SELECT ?president ?presidentLabel WHERE {
      wd:Q142 wdt:P35 ?president.
      ?president rdfs:label ?presidentLabel.
      FILTER(LANG(?presidentLabel) = "en")
    }
    """
    result = x._run(query)
    print(result)