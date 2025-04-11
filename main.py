from dotenv import load_dotenv
import logging
import argparse
from tools.orchestrator import EnsembleOrchestratorTool, OrchestratorInput

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enhanced Wikidata Question Answering System")
    parser.add_argument("--question", type=str, help="Question to answer")
    parser.add_argument("--language", type=str, default="en", help="Language for the answer (default: en)")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information about the answering process")
    args = parser.parse_args()
    
    # Initialize the orchestrator tool
    orchestrator = EnsembleOrchestratorTool()
    
    if args.interactive:
        # Run in interactive mode
        print("Enhanced Wikidata QA System - Interactive Mode")
        print("Type 'exit' or 'quit' to end the session")
        
        while True:
            question = input("\nQuestion: ")
            if question.lower() in ["exit", "quit"]:
                break
                
            try:
                input_data = OrchestratorInput(question=question, language=args.language)
                result = orchestrator._run(input_data)
                
                print("\nAnswer:", result["answer"])
                
                if args.verbose:
                    print("\nEntities:", ", ".join(result.get("entities", [])))
                    print("Found paths:", result.get("paths", 0))
                    if result.get("query"):
                        print("\nQuery used:", result["query"])
                    if result.get("query_explanation"):
                        print("Query approach:", result["query_explanation"])
                    if result.get("result_count"):
                        print("Results found:", result["result_count"])
                    
                print("\n" + "-" * 80)
            except Exception as e:
                logger.error(f"Error processing question: {e}")
                print(f"\nError: {str(e)}")
    
    elif args.question:
        # Run with a single question
        try:
            input_data = OrchestratorInput(question=args.question, language=args.language)
            result = orchestrator._run(input_data)
            
            print("\nQuestion:", args.question)
            print("Answer:", result["answer"])
            
            if args.verbose:
                print("\nEntities:", ", ".join(result.get("entities", [])))
                print("Found paths:", result.get("paths", 0))
                if result.get("query"):
                    print("\nQuery used:", result["query"])
                if result.get("query_explanation"):
                    print("Query approach:", result["query_explanation"])
                if result.get("result_count"):
                    print("Results found:", result["result_count"])
        except Exception as e:
            logger.error(f"Error processing question: {e}")
            print(f"Error: {str(e)}")
    
    else:
        # No question provided
        parser.print_help()

if __name__ == "__main__":
    main()