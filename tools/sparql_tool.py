from typing import Optional, Dict, Any, ClassVar
from langchain_core.tools import BaseTool
from SPARQLWrapper import SPARQLWrapper, JSON
import re

class ExecuteSPARQLTool(BaseTool):
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
        
    def _run(self, query: str, limit: int = 5, include_references: bool = True) -> Dict[str, Any]:
        """
        Execute a SPARQL query against Wikidata
        
        Args:
            query: The SPARQL query string
            limit: Maximum number of results to return (default: 5)
            include_references: Whether to automatically enhance the query to include references (default: True)
            
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
            
            return query
            
            self._sparql.setQuery(query)
            results = self._sparql.query().convert()
            
            # Process results to make them more readable
            processed_results = []
            
            if "results" in results and "bindings" in results["results"]:
                bindings = results["results"]["bindings"]
                
                for binding in bindings:
                    processed_binding = {}
                    for key, value in binding.items():
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
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e).split('\n')[0],
                "query": query
            }
            
    def _enhance_query_with_references(self, query: str) -> str:
        """
        Enhance a SPARQL query to include reference information
        
        Args:
            query: The original SPARQL query
            
        Returns:
            An enhanced query that includes reference information
        """
        # Extract the SELECT part and the WHERE clause
        select_match = re.search(r'SELECT\s+(.*?)\s+WHERE\s*\{', query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return query  # Not a standard SELECT query, return as is
            
        select_vars = select_match.group(1).strip()
        
        # Find the opening and closing braces of the WHERE clause
        where_start_index = query.find('{')
        if where_start_index == -1:
            return query  # Can't find the WHERE clause start
            
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
            return query  # Can't find matching closing brace
            
        # Extract the WHERE clause content
        where_content = query[where_start_index + 1:where_end_index].strip()
        
        # Process the WHERE clause content to handle triple patterns
        # First, normalize whitespace and ensure each clause ends with a period
        normalized_content = re.sub(r'\s+', ' ', where_content)
        normalized_content = re.sub(r'([^\.;])\s*\n\s*', r'\1 ', normalized_content)
        
        # Split by periods but preserve FILTER expressions
        triple_patterns = []
        current = ""
        in_filter = False
        in_optional = False
        brace_level = 0
        
        for i, char in enumerate(normalized_content):
            current += char
            
            if char == '{':
                brace_level += 1
                if normalized_content[i-8:i].upper().strip() == "OPTIONAL":
                    in_optional = True
            elif char == '}':
                brace_level -= 1
                if brace_level == 0 and in_optional:
                    in_optional = False
            
            # Add a section when we hit a period outside of a FILTER or nested block
            if char == '.' and brace_level == 0 and not in_filter:
                if current.strip():
                    triple_patterns.append(current.strip())
                current = ""
        
        # Add final section if not empty
        if current.strip():
            triple_patterns.append(current.strip())
        
        # Process each triple pattern and identify wdt: patterns
        enhanced_patterns = []
        new_select_vars = []
        counter = 1
        
        for pattern in triple_patterns:
            # Keep the original pattern
            enhanced_patterns.append(pattern)
            
            # Pattern 1: Subject is a Wikidata entity (wd:Q...)
            # Example: wd:Q142 wdt:P35 ?president
            wdt_entity_match = re.search(r'(wd:Q\d+)\s+(wdt:P\d+)\s+(\?[a-zA-Z0-9_]+)', pattern)
            
            # Pattern 2: Subject is a variable
            # Example: ?mountain wdt:P31 wd:Q8502
            wdt_var_to_entity_match = re.search(r'(\?[a-zA-Z0-9_]+)\s+(wdt:P\d+)\s+(wd:Q\d+)', pattern)
            
            # Pattern 3: Subject and object are both variables
            # Example: ?mountain wdt:P4552 ?height
            wdt_var_to_var_match = re.search(r'(\?[a-zA-Z0-9_]+)\s+(wdt:P\d+)\s+(\?[a-zA-Z0-9_]+)', pattern)
            
            # Handle Pattern 1: wd:Q142 wdt:P35 ?president
            if wdt_entity_match:
                subject = wdt_entity_match.group(1)
                predicate = wdt_entity_match.group(2)
                object_var = wdt_entity_match.group(3)
                
                statement_var = f"?statement{counter}"
                ref_url_var = f"?refUrl{counter}"
                ref_date_var = f"?refDate{counter}"
                
                new_select_vars.extend([ref_url_var, ref_date_var])
                
                # Generate reference patterns
                ref_patterns = [
                    f"{subject} p:{predicate[4:]} {statement_var}",
                    f"{statement_var} ps:{predicate[4:]} {object_var}",
                    f"OPTIONAL {{",
                    f"  {statement_var} prov:wasDerivedFrom ?reference{counter} .",
                    f"  OPTIONAL {{ ?reference{counter} pr:P854 {ref_url_var} }} # Reference URL",
                    f"  OPTIONAL {{ ?reference{counter} pr:P813 {ref_date_var} }} # Reference date",
                    f"}}"
                ]
                
                enhanced_patterns.extend(ref_patterns)
                counter += 1
            
            # Handle Pattern 2: ?mountain wdt:P31 wd:Q8502
            elif wdt_var_to_entity_match:
                subject_var = wdt_var_to_entity_match.group(1)
                predicate = wdt_var_to_entity_match.group(2)
                object_entity = wdt_var_to_entity_match.group(3)
                
                statement_var = f"?statement{counter}"
                ref_url_var = f"?refUrl{counter}"
                ref_date_var = f"?refDate{counter}"
                
                new_select_vars.extend([ref_url_var, ref_date_var])
                
                # Generate reference patterns
                ref_patterns = [
                    f"{subject_var} p:{predicate[4:]} {statement_var}",
                    f"{statement_var} ps:{predicate[4:]} {object_entity}",
                    f"OPTIONAL {{",
                    f"  {statement_var} prov:wasDerivedFrom ?reference{counter} .",
                    f"  OPTIONAL {{ ?reference{counter} pr:P854 {ref_url_var} }} # Reference URL",
                    f"  OPTIONAL {{ ?reference{counter} pr:P813 {ref_date_var} }} # Reference date",
                    f"}}"
                ]
                
                enhanced_patterns.extend(ref_patterns)
                counter += 1
                
            # Handle Pattern 3: ?mountain wdt:P4552 ?height
            elif wdt_var_to_var_match:
                subject_var = wdt_var_to_var_match.group(1)
                predicate = wdt_var_to_var_match.group(2)
                object_var = wdt_var_to_var_match.group(3)
                
                statement_var = f"?statement{counter}"
                ref_url_var = f"?refUrl{counter}"
                ref_date_var = f"?refDate{counter}"
                
                new_select_vars.extend([ref_url_var, ref_date_var])
                
                # Generate reference patterns
                ref_patterns = [
                    f"{subject_var} p:{predicate[4:]} {statement_var}",
                    f"{statement_var} ps:{predicate[4:]} {object_var}",
                    f"OPTIONAL {{",
                    f"  {statement_var} prov:wasDerivedFrom ?reference{counter} .",
                    f"  OPTIONAL {{ ?reference{counter} pr:P854 {ref_url_var} }} # Reference URL",
                    f"  OPTIONAL {{ ?reference{counter} pr:P813 {ref_date_var} }} # Reference date",
                    f"}}"
                ]
                
                enhanced_patterns.extend(ref_patterns)
                counter += 1
        
        # Update the SELECT clause to include new variables
        if new_select_vars:
            for var in new_select_vars:
                if var not in select_vars:
                    select_vars += f" {var}"
        
        # Rebuild the query
        before_select = query[:select_match.start()]
        select_clause = f"SELECT {select_vars} WHERE {{"
        after_where = query[where_end_index + 1:]
        
        # Join the patterns with proper separators
        joined_patterns = ""
        for i, pattern in enumerate(enhanced_patterns):
            joined_patterns += "\n  " + pattern
            # Add period after each pattern except the last one or if it's an OPTIONAL block
            if i < len(enhanced_patterns) - 1 and not pattern.endswith("}"):
                if not pattern.endswith("."):
                    joined_patterns += " ."
            
        enhanced_query = before_select + select_clause + joined_patterns + "\n}" + after_where
        
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