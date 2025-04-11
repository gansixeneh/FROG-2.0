from typing import Dict, List, Any, Optional
import re
import logging

logger = logging.getLogger(__name__)

class EvaluationUtils:
    """Utilities for evaluating answer quality."""
    
    @staticmethod
    def evaluate_answer_completeness(answer: str, expected_entities: List[str]) -> float:
        """
        Evaluate the completeness of an answer based on expected entities.
        
        Parameters:
        -----------
        answer : str
            The answer text
        expected_entities : List[str]
            List of entity labels expected to be found in the answer
            
        Returns:
        --------
        float
            Completeness score between 0.0 and 1.0
        """
        if not answer or not expected_entities:
            return 0.0
            
        # Count how many expected entities are mentioned in the answer
        mentioned_count = sum(1 for entity in expected_entities if entity.lower() in answer.lower())
        
        # Calculate completeness score
        return mentioned_count / len(expected_entities)
    
    @staticmethod
    def evaluate_result_correctness(results: List[Dict[str, Any]], expected_values: Dict[str, Any]) -> float:
        """
        Evaluate correctness of query results against expected values.
        
        Parameters:
        -----------
        results : List[Dict[str, Any]]
            Query results
        expected_values : Dict[str, Any]
            Expected values for specific fields
            
        Returns:
        --------
        float
            Correctness score between 0.0 and 1.0
        """
        if not results or not expected_values:
            return 0.0
            
        # Count matches for each expected value
        match_count = 0
        
        for field, expected in expected_values.items():
            for result in results:
                if field in result and str(result[field]).lower() == str(expected).lower():
                    match_count += 1
                    break
        
        # Calculate correctness score
        return match_count / len(expected_values)
    
    @staticmethod
    def evaluate_sparql_quality(query: str) -> float:
        """
        Evaluate the quality of a SPARQL query based on best practices.
        
        Parameters:
        -----------
        query : str
            SPARQL query
            
        Returns:
        --------
        float
            Quality score between 0.0 and 1.0
        """
        if not query:
            return 0.0
        
        score = 1.0
        deductions = []
        
        # Check for common issues
        if "LIMIT" not in query.upper():
            score -= 0.1
            deductions.append("No LIMIT clause")
            
        if "SERVICE wikibase:label" not in query:
            score -= 0.2
            deductions.append("No label service")
            
        # Check for proper prefixes
        prefixes = ["wd:", "wdt:", "wikibase:"]
        missing_prefixes = [p for p in prefixes if p not in query]
        if missing_prefixes:
            score -= 0.1 * len(missing_prefixes)
            deductions.append(f"Missing prefixes: {', '.join(missing_prefixes)}")
            
        # Check for FILTER usage
        if "FILTER" not in query:
            score -= 0.05
            deductions.append("No FILTER clauses")
            
        # Check for variable naming
        if re.search(r'\?[^a-zA-Z0-9_]', query):
            score -= 0.1
            deductions.append("Invalid variable names")
            
        # Log deductions
        if deductions:
            logger.debug(f"SPARQL quality deductions: {', '.join(deductions)}")
            
        return max(0.0, score)
    
    @staticmethod
    def evaluate_answer_relevance(question: str, answer: str) -> float:
        """
        Simple heuristic for evaluating answer relevance to the question.
        
        Parameters:
        -----------
        question : str
            The original question
        answer : str
            The provided answer
            
        Returns:
        --------
        float
            Relevance score between 0.0 and 1.0
        """
        if not question or not answer:
            return 0.0
        
        # Extract keywords from the question (simple approach)
        question_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', question.lower()))
        answer_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', answer.lower()))
        
        # Remove common stop words
        stop_words = {"the", "and", "that", "what", "who", "where", "when", "how", "which", "this", "with"}
        question_keywords = question_words - stop_words
        
        if not question_keywords:
            return 0.5  # Default value if no meaningful keywords found
        
        # Count keyword matches
        matches = question_keywords.intersection(answer_words)
        match_ratio = len(matches) / len(question_keywords)
        
        # Adjust score - even with no matches, give a minimum score of 0.3
        return 0.3 + (0.7 * match_ratio)