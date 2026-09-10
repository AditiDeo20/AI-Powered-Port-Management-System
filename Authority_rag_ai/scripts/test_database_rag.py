import sys
import os
import time

# Add the project root to sys.path so 'app' can be imported when running directly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.database_agent import DatabaseAgent

def main():
    print("=" * 70)
    print("Standalone Database RAG (Text-to-SQL) Tester")
    print("Type 'exit' to quit")
    print("=" * 70)
    
    print("\nInitializing Database Agent...")
    try:
        agent = DatabaseAgent()
        print("Initialization complete. Connected to Postgres.")
    except Exception as e:
        print(f"Failed to initialize Database Agent: {e}")
        return

    while True:
        question = input("\nEnter your structured data question: ").strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        print("\n" + "=" * 70)
        print("DATABASE RAG GENERATION")
        print("=" * 70)
        
        start_time = time.time()
        
        try:
            answer = agent.query(question)
        except Exception as e:
            answer = f"Error during query execution: {e}"
            
        execution_time = time.time() - start_time
        
        print("\nAnswer:\n")
        print(answer)
        
        print("\n" + "-" * 70)
        print(f"Execution Time: {execution_time:.2f}s")
        print("-" * 70)

if __name__ == "__main__":
    main()
