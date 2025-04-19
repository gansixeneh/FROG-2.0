from langchain_core.tools import BaseTool
from google import genai
from google.genai import types
import os
import requests


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
                urls_to_resolve = []
                
                # First, collect all the proxy URLs
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    grounding_chunks = getattr(candidate.grounding_metadata, 'grounding_chunks', [])
                    for chunk in grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            web_info = chunk.web
                            url = getattr(web_info, 'uri', "")
                            title = getattr(web_info, 'title', "")
                            domain = getattr(web_info, 'domain', "")
                            
                            # Check if this is a proxy URL
                            if url and "vertexaisearch.cloud.google.com" in url:
                                urls_to_resolve.append({
                                    "proxy_url": url,
                                    "title": title or domain,
                                    "domain": domain
                                })
                
                # Resolve the proxy URLs to their final destinations
                for url_info in urls_to_resolve:
                    try:
                        final_url = self._resolve_redirect_url(url_info["proxy_url"])
                        citations.append({
                            "title": url_info["title"],
                            "url": final_url
                        })
                    except Exception as e:
                        # If we can't resolve the URL, use the original
                        citations.append({
                            "title": url_info["title"],
                            "url": url_info["proxy_url"],
                            "error": str(e)
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
    
    def _resolve_redirect_url(self, proxy_url):
        """
        Follow a redirect URL to get the final destination URL
        
        Args:
            proxy_url: The proxy URL from Vertex AI Search
            
        Returns:
            The final destination URL after following redirects
        """
        try:
            # Send a HEAD request to follow redirects without downloading content
            response = requests.head(
                proxy_url, 
                allow_redirects=True, 
                timeout=5,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            return response.url
        except Exception as e:
            # If HEAD request fails, try with GET
            try:
                response = requests.get(
                    proxy_url, 
                    allow_redirects=True, 
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    stream=True  # To avoid downloading the full content
                )
                # Close the connection without reading the content
                response.close()
                return response.url
            except Exception:
                # If both methods fail, return the original URL
                return proxy_url