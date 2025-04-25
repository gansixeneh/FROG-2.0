import os
import argparse
from dotenv import load_dotenv
from graph import WikidataQueryAgent
from evaluate import evaluate_wikidata_agent

def main():
    parser = argparse.ArgumentParser(description="Wikidata Agent CLI")
    parser.add_argument("--mode", choices=["interactive", "evaluate"], default="interactive",
                       help="Run mode: interactive for CLI, evaluate for batch testing")
    parser.add_argument("--test-data", type=str, default="dataset/qald_9_plus/qald_9_plus_test_wikidata.json",
                       help="Path to test data (for evaluate mode)")
    parser.add_argument("--output", type=str, default="evaluation_results.json",
                       help="Path to output file (for evaluate mode)")
    args = parser.parse_args()
    
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Get API key from environment or input
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        gemini_api_key = input("Enter your Gemini API key: ")
    
    # Initialize the agent
    print("Initializing Wikidata Agent...")
    agent = WikidataQueryAgent(gemini_api_key)
    
    if args.mode == "evaluate":
        # Run evaluation
        print(f"Evaluating agent on {args.test_data}...")
        results = evaluate_wikidata_agent(agent, args.test_data, args.output)
        
        # Print summary
        print("\nEvaluation complete!")
        print(f"Results saved to {args.output}")
        print("\nAverage Metrics:")
        for key, value in results['average_metrics'].items():
            print(f"{key}: {value:.4f}")
    else:
        # Interactive mode
        example_questions = [
            "Who is the current president of France?",
            "What is the capital of Japan and what is its population?",
            "List the spouses of Albert Einstein",
            "Which mountains in the Himalayas are higher than 8000 meters?",
            "What books did Isaac Asimov write?",
            "Who won the Nobel Prize in Physics in 2020?"
        ]
        
        print("\nWikidata Agent initialized. Ask a question or type 'exit' to quit.")
        print("\nExample questions:")
        for i, question in enumerate(example_questions, 1):
            print(f"{i}. {question}")
        
        # Interactive loop
        while True:
            user_input = input("\nYour question: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            if user_input.strip():
                print("\nProcessing your question...")
                try:
                    result = agent.query(user_input)
                    
                    print(f"\nGenerated SPARQL Query:")
                    print(result['sparql_query'])
                    
                    if result['success']:
                        print("\nQuery Results:")
                        for i, item in enumerate(result['results'][:5], 1):
                            print(f"{i}. {item}")
                        
                        if result['result_count'] > 5:
                            print(f"... and {result['result_count'] - 5} more results")
                    else:
                        print(f"\nQuery Error: Failed to execute query")
                except Exception as e:
                    print(f"\nError: {str(e)}")
                    print("Please try again with a different question.")

if __name__ == "__main__":
    main()