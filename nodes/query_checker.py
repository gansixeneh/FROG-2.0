from typing import Dict, Any, Literal
import google.generativeai as genai
from tools.sparql_tool import WikidataSPARQLTool

class QueryChecker:
    """Node for checking and validating SPARQL queries."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.sparql_tool = WikidataSPARQLTool()
        
    def check_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check a SPARQL query and decide whether to use it or regenerate
        
        Args:
            state: Current state with 'generated_query' key
            
        Returns:
            Updated state with query validation results and decision
        """
        question = state.get("question", "")
        query = state.get("generated_query", "")
        
        # Execute the query
        result = self.sparql_tool.execute(query)
        
        success = result.get("success", False)
        result_count = result.get("count", 0)
        results = result.get("results", [])
        
        # Get labels for URIs in results for better human-readable feedback
        all_uris = []
        for res in results:
            for key, value in res.items():
                if value.startswith("http://www.wikidata.org/entity/"):
                    all_uris.append(value)
        
        uri_labels = self.sparql_tool.get_labels_for_uris(all_uris)
        
        # Add labels to results for context
        results_with_labels = []
        for res in results:
            res_with_labels = {}
            for key, value in res.items():
                res_with_labels[key] = value
                if value in uri_labels:
                    res_with_labels[f"{key}_label"] = uri_labels[value]
            results_with_labels.append(res_with_labels)
        
        # Check if the query is valid and results are satisfactory
        if not success:
            error = result.get("error", "Unknown error")
            feedback = f"The query failed with error: {error}. Please fix the SPARQL syntax."
            decision = "regenerate"
        elif result_count == 0:
            feedback = "The query executed successfully but returned no results. Please adjust the query to return relevant results."
            decision = "regenerate"
        else:
            # Use Gemini to evaluate if the results actually answer the question
            evaluation_prompt = f"""
            Question: {question}
            
            SPARQL Query:
            {query}
            
            Query Results (first {min(5, len(results_with_labels))} of {result_count}):
            {results_with_labels[:5]}
            
            Do these results correctly answer the original question? Evaluate based on:
            1. Are the results relevant to the question?
            2. Do they contain the information needed to answer the question?
            3. Is the query constructed properly to capture the intent of the question?
            
            Respond with:
            - "satisfied" if the results adequately answer the question
            - "regenerate" if the query needs to be modified, with specific feedback on what's wrong
            
            Format your response as:
            DECISION: [satisfied or regenerate]
            FEEDBACK: [your feedback if regenerate, or "Results look good." if satisfied]
            """
            
            evaluation = self.model.generate_content(evaluation_prompt)
            evaluation_text = evaluation.text
            
            # Parse the decision and feedback
            decision = "regenerate"  # Default
            feedback = ""
            
            if "DECISION:" in evaluation_text:
                decision_line = [line for line in evaluation_text.split('\n') if "DECISION:" in line][0]
                decision_text = decision_line.split("DECISION:")[1].strip().lower()
                if "satisfied" in decision_text:
                    decision = "satisfied"
                else:
                    decision = "regenerate"
            
            if "FEEDBACK:" in evaluation_text:
                feedback_start = evaluation_text.find("FEEDBACK:") + len("FEEDBACK:")
                feedback = evaluation_text[feedback_start:].strip()
        
        return {
            **state,
            "query_results": results_with_labels,
            "result_count": result_count,
            "query_success": success,
            "feedback": feedback,
            "decision": decision
        }

    def decide_next_step(self, state: Dict[str, Any]) -> Literal["continue", "regenerate"]:
        """Determine the next step based on the query checker's decision."""
        decision = state.get("decision", "regenerate")
        
        if decision == "satisfied":
            return "continue"
        else:
            return "regenerate"

    def __call__(self, state):
        """Make the class callable for langgraph."""
        return self.check_query(state)