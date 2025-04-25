"""
Run example queries to demonstrate the Wikidata Query Agent.
This script runs a set of predefined questions through the agent
and displays the results.
"""

import os
import json
from dotenv import load_dotenv
from graph import WikidataQueryAgent
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

# Load environment variables
load_dotenv()

# Set up rich console
console = Console()

# Sample questions
EXAMPLE_QUESTIONS = [
    "Who is the current president of France?",
    "What is the capital of Japan and what is its population?",
    "List the spouses of Albert Einstein",
    "Which mountains in the Himalayas are higher than 8000 meters?",
    "What books did Isaac Asimov write?",
    "Who won the Nobel Prize in Physics in 2020?"
]

def main():
    """Run example questions through the Wikidata Query Agent."""
    # Get API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[bold red]Error:[/bold red] No Gemini API key found in environment variables.")
        console.print("Please set the GEMINI_API_KEY environment variable or create a .env file.")
        return
    
    # Initialize agent
    console.print(Panel.fit("[bold]Initializing Wikidata Query Agent[/bold]", 
                           title="Setup", 
                           border_style="blue"))
    agent = WikidataQueryAgent(api_key)
    
    # Process each example question
    for i, question in enumerate(EXAMPLE_QUESTIONS, 1):
        console.print(f"\n[bold cyan]Example {i}:[/bold cyan] {question}")
        console.print("[yellow]Processing...[/yellow]")
        
        try:
            # Query the agent
            result = agent.query(question)
            
            # Display query
            query_syntax = Syntax(result['sparql_query'], "sparql", theme="monokai", line_numbers=True)
            console.print(Panel(query_syntax, title="Generated SPARQL Query", border_style="green"))
            
            # Display results
            if result['success'] and result['results']:
                table = Table(title=f"Query Results ({result['result_count']} total)")
                
                # Determine columns dynamically from the first result
                if result['results']:
                    columns = list(result['results'][0].keys())
                    for col in columns:
                        table.add_column(col, style="cyan")
                    
                    # Add rows
                    for res in result['results'][:5]:  # Show only first 5 results
                        table.add_row(*[str(res.get(col, "")) for col in columns])
                    
                    console.print(table)
                    
                    if result['result_count'] > 5:
                        console.print(f"[dim]...and {result['result_count'] - 5} more results[/dim]")
                else:
                    console.print("[yellow]Query successful but returned no results.[/yellow]")
            else:
                console.print("[bold red]Query failed to execute or returned no results.[/bold red]")
            
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {str(e)}")
        
        # Add a separator between examples
        if i < len(EXAMPLE_QUESTIONS):
            console.print("\n" + "-" * 80)
    
    console.print("\n[bold green]All examples processed![/bold green]")

if __name__ == "__main__":
    main()