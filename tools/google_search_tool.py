from langchain_core.tools import BaseTool
from google import genai
from google.genai import types
import os


class GoogleSearchTool(BaseTool):
    name: str = "google_search"
    description: str = """Search the internet using Google Search.
    Use this tool ONLY as a fallback when Wikidata doesn't have the information or when querying recent events.
    
    Args:
        query: The search query to execute
        
    Returns:
        Search results with relevant information from the web
    """
    
    def _run(self, query: str):
        """
        Execute a Google search query
        
        Args:
            query: The search query
            
        Returns:
            Search results with information from the web
        """
        try:
            # Initialize Google Genai client with the same API key as Gemini
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return {
                    "success": False,
                    "error": "Gemini API key not found in environment variables",
                    "results": []
                }
                
            client = genai.Client(api_key=api_key)
            
            # Execute the search query using Gemini's built-in search capability
            response = client.models.generate_content(
                model='gemini-2.0-flash',
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(
                        google_search=types.GoogleSearchRetrieval()
                    )]
                )
            )
            
            # Process and format the results
            search_results = []
            
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Extract text content
                text_content = candidate.content.parts[0].text if candidate.content and candidate.content.parts else ""
                
                # Extract search citations if available
                citations = []
                if hasattr(candidate, 'tool_calls') and candidate.tool_calls:
                    for tool_call in candidate.tool_calls:
                        if hasattr(tool_call, 'search_citations') and tool_call.search_citations:
                            for citation in tool_call.search_citations:
                                citations.append({
                                    "title": citation.title if hasattr(citation, 'title') else "",
                                    "url": citation.url if hasattr(citation, 'url') else "",
                                    "snippet": citation.snippet if hasattr(citation, 'snippet') else ""
                                })
                
                search_results = {
                    "content": text_content,
                    "citations": citations
                }
            
            return {
                "success": True,
                "query": query,
                "results": search_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }