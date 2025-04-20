// frontend/src/utils/sparqlFormatter.ts
import { spfmt } from 'sparql-formatter';

/**
 * Format a SPARQL query using the sparql-formatter library
 * 
 * @param query - The SPARQL query string to format
 * @param mode - The formatting mode ('default', 'compact', 'turtle', 'jsonld')
 * @param indentDepth - The indentation depth (number of spaces)
 * @returns Formatted SPARQL query string
 */
export const formatSparqlQuery = (
  query: string, 
  mode: 'default' | 'compact' | 'turtle' | 'jsonld' = 'default', 
  indentDepth: number = 2
): string => {
  try {
    return spfmt.format(query, mode, indentDepth);
  } catch (error) {
    console.error('Error formatting SPARQL query:', error);
    return query; // Return original query if formatting fails
  }
};

/**
 * Detect if a string contains a SPARQL query
 * 
 * @param text - The text to check
 * @returns Boolean indicating if the text appears to be a SPARQL query
 */
export const isSparqlQuery = (text: string): boolean => {
  // Check for common SPARQL keywords
  const sparqlKeywords = [
    'SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE',
    'WHERE', 'FILTER', 'OPTIONAL', 'UNION',
    'PREFIX', 'ORDER BY', 'LIMIT', 'OFFSET',
    'GROUP BY', 'HAVING', 'VALUES', 'SERVICE'
  ];
  
  const textUpper = text.toUpperCase();
  return sparqlKeywords.some(keyword => 
    textUpper.includes(keyword) && 
    // Basic check to ensure it's a query, not just text mentioning SPARQL keywords
    (textUpper.includes('WHERE') || textUpper.includes('PREFIX') || textUpper.includes('SELECT'))
  );
};