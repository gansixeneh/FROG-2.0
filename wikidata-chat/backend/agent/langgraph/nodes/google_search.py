# backend/agent/langgraph/nodes/google_search.py
from datetime import datetime
from google import genai
from google.genai import types
import os
import requests
from ..utils.state import WikidataGraphRAGState

class GoogleSearchNode:
    """Node for searching the internet using Google Search as a fallback"""
    
    def __init__(self):
        pass
        
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
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            return response.url
        except Exception as e:
            # If HEAD request fails, try with GET
            try:
                response = requests.get(
                    proxy_url,
                    allow_redirects=True,
                    timeout=5,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    },
                    stream=True,  # To avoid downloading the full content
                )
                # Close the connection without reading the content
                response.close()
                return response.url
            except Exception:
                # If both methods fail, return the original URL
                return proxy_url
        
    def __call__(self, state: WikidataGraphRAGState) -> WikidataGraphRAGState:
        # Start timing
        start_time = datetime.now()
        
        # Log start
        if hasattr(state, 'visualizer') and state.visualizer:
            knowledge_source = getattr(state, 'knowledge_source', 'wikidata')
            source_name = "curriculum knowledge base" if knowledge_source == "curriculum" else "Wikidata"
            state.visualizer.log_event(
                "Google Search Node", 
                "start",
                {"question": state.translated_question, "reason": f"{source_name} methods failed"},
                start_time=start_time
            )
            
        try:
            # Initialize Google Genai client with the same API key as Gemini
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("Gemini API key not found in environment variables")

            client = genai.Client(api_key=api_key)

            # Execute the search query using Gemini's built-in search capability
            search_start_time = datetime.now()
            
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Google Search Node",
                    "executing search",
                    {"query": state.translated_question},
                    start_time=search_start_time
                )
                
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=state.translated_question,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearchRetrieval())]
                ),
            )

            # Process and format the results
            search_results = []

            if hasattr(response, "candidates") and len(response.candidates) > 0:
                candidate = response.candidates[0]

                # Extract text content
                text_content = (
                    candidate.content.parts[0].text
                    if candidate.content and candidate.content.parts
                    else ""
                )

                # Extract search citations if available
                citations = []
                urls_to_resolve = []

                # First, collect all the proxy URLs
                if (
                    hasattr(candidate, "grounding_metadata")
                    and candidate.grounding_metadata
                ):
                    grounding_chunks = getattr(
                        candidate.grounding_metadata, "grounding_chunks", []
                    )
                    for chunk in grounding_chunks:
                        if hasattr(chunk, "web") and chunk.web:
                            web_info = chunk.web
                            url = getattr(web_info, "uri", "")
                            title = getattr(web_info, "title", "")
                            domain = getattr(web_info, "domain", "")

                            # Check if this is a proxy URL
                            if url and "vertexaisearch.cloud.google.com" in url:
                                urls_to_resolve.append(
                                    {
                                        "proxy_url": url,
                                        "title": title or domain,
                                        "domain": domain,
                                    }
                                )

                # Resolve the proxy URLs to their final destinations
                for url_info in urls_to_resolve:
                    try:
                        final_url = self._resolve_redirect_url(url_info["proxy_url"])
                        citations.append({"title": url_info["title"], "url": final_url})
                    except Exception as e:
                        # If we can't resolve the URL, use the original
                        citations.append(
                            {
                                "title": url_info["title"],
                                "url": url_info["proxy_url"],
                                "error": str(e),
                            }
                        )

                search_results = {"content": text_content, "citations": citations}
                
            search_end_time = datetime.now()
            
            # Log search results
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Google Search Node",
                    "search results",
                    {
                        "has_content": bool(search_results.get("content")),
                        "citation_count": len(search_results.get("citations", [])) if search_results else 0
                    },
                    start_time=search_start_time,
                    end_time=search_end_time
                )
                
            # Update state with results
            state.google_search_result = search_results
            state.approach_used = "google_search"
            
            # Prepare context for answer generation
            if search_results and search_results.get("content"):
                context_str = f'Based on web search results: {search_results["content"]}'
                if search_results.get("citations"):
                    context_str += "\n\nSources:\n"
                    for citation in search_results["citations"]:
                        context_str += f"- {citation.get('title', 'Unknown')}: {citation.get('url', '')}\n"
                state.context_str = context_str
            else:
                state.context_str = "I couldn't find information to answer this question from web search."
                
        except Exception as e:
            if hasattr(state, 'visualizer') and state.visualizer:
                state.visualizer.log_event(
                    "Google Search Node",
                    "search error",
                    {"error": str(e)}
                )
                
            if state.verbose > 0:
                print(f"Error in Google search: {e}")
                
            state.context_str = "I couldn't find information to answer this question."
            state.approach_used = "google_search_failed"
            
        # End timing
        end_time = datetime.now()
        
        # Log completion
        if hasattr(state, 'visualizer') and state.visualizer:
            state.visualizer.log_event(
                "Google Search Node", 
                "end", 
                None,
                start_time=start_time,
                end_time=end_time
            )
            
        return state