"""
Utility script to visualize the LangGraph structure of the Wikidata Query Agent.
Generates a visual representation of the graph and saves it as an HTML file.
"""

import os
import json
from dotenv import load_dotenv
from graph import create_wikidata_graph
from langgraph.checkpoint import MemorySaver
from rich.console import Console

# Load environment variables
load_dotenv()

# Set up rich console
console = Console()

def main():
    """Generate a visualization of the Wikidata Query Agent graph."""
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] No Gemini API key found in environment variables.")
        console.print("Please set the GEMINI_API_KEY environment variable or create a .env file.")
        return
    
    console.print("[bold]Initializing Wikidata Query Graph...[/bold]")
    
    # Create graph (uncompiled for visualization)
    from langgraph.graph import StateGraph, END
    from nodes.entity_extraction import EntityExtractor
    from nodes.query_generator import QueryGenerator
    from nodes.query_checker import QueryChecker
    
    # Initialize nodes
    entity_extractor = EntityExtractor(api_key)
    query_generator = QueryGenerator(api_key)
    query_checker = QueryChecker(api_key)
    
    # Define state graph
    graph = StateGraph(dict)
    
    # Define nodes
    graph.add_node("extract_entities", entity_extractor)
    graph.add_node("generate_query", query_generator)
    graph.add_node("check_query", query_checker)
    
    # Define edges
    graph.add_edge("extract_entities", "generate_query")
    graph.add_edge("generate_query", "check_query")
    
    # Define conditional edges for the checker
    graph.add_conditional_edges(
        "check_query",
        query_checker.decide_next_step,
        {
            "continue": END,
            "regenerate": "generate_query"
        }
    )
    
    # Define the entry point
    graph.set_entry_point("extract_entities")
    
    # Save the visualization
    try:
        console.print("[yellow]Generating graph visualization...[/yellow]")
        
        graph_html = graph.get_graph().draw_mermaid_png()
        
        with open("wikidata_graph.html", "w") as f:
            f.write(f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Wikidata Query Agent Graph</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #2c3e50; }}
                    .container {{ max-width: 1200px; margin: 0 auto; }}
                    .graph {{ border: 1px solid #ddd; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Wikidata Query Agent - LangGraph Visualization</h1>
                    <div class="graph">
                        {graph_html}
                    </div>
                    <p>Generated using langgraph's visualization tools.</p>
                </div>
            </body>
            </html>
            """)
        
        console.print("[bold green]Visualization saved to wikidata_graph.html[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error generating visualization:[/bold red] {str(e)}")
        console.print("Note: This might be due to missing graphviz or other dependencies.")
        console.print("Try installing: pip install graphviz pydot")

if __name__ == "__main__":
    main()