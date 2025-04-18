import os
from dotenv import load_dotenv
from agent import WikidataAgent

def main():
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Get API key from environment or input
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        gemini_api_key = input("Enter your Gemini API key: ")
    
    # Initialize the agent
    print("Initializing Wikidata Agent...")
    agent = WikidataAgent(gemini_api_key)
    
    # Example questions
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
                response = agent.query(user_input)
                print(f"\nAnswer: {response}")
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again with a different question.")

if __name__ == "__main__":
    main()