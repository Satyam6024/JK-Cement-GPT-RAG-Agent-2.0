"""
Main script to test and run the RAG Agent.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from rag_agent import get_initialization_status, require_vertex_ai
from rag_agent.agent import root_agent

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def check_setup():
    """Check if the RAG agent is properly configured."""
    print("🔍 Checking RAG Agent setup...")
    
    # Check Vertex AI initialization
    is_initialized, error_msg = get_initialization_status()
    if is_initialized:
        print("✅ Vertex AI initialized successfully")
    else:
        print(f"❌ Vertex AI initialization failed: {error_msg}")
        return False
    
    # Check if agent is available
    try:
        print(f"✅ Agent '{root_agent.name}' loaded successfully")
        print(f"   Model: {root_agent.model}")
        print(f"   Tools: {len(root_agent.tools)} available")
        for i, tool in enumerate(root_agent.tools, 1):
            print(f"      {i}. {tool.__name__}")
        return True
    except Exception as e:
        print(f"❌ Agent loading failed: {str(e)}")
        return False


def interactive_mode():
    """Run the agent in interactive mode."""
    print("\n🤖 RAG Agent Interactive Mode")
    print("Type 'help' for commands, 'quit' to exit\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
                
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Send message to agent
            print("Agent: Thinking...")
            response = root_agent.send_message(user_input)
            print(f"Agent: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            logger.error(f"Interactive mode error: {str(e)}", exc_info=True)


def print_help():
    """Print help information."""
    help_text = """
📚 Available Commands and Examples:

Corpus Management:
  • "List all corpora" - See available document collections
  • "Create a corpus called 'my-docs'" - Create new corpus
  • "Show info for corpus 'my-docs'" - Get corpus details
  • "Delete corpus 'old-docs'" - Remove entire corpus

Document Management:
  • "Add this Google Drive file: https://drive.google.com/file/d/123/view"
  • "Add documents from: https://docs.google.com/document/d/456"
  • "Delete document 'doc_id' from 'my-docs'"

Querying:
  • "What is the main topic discussed in the documents?"
  • "Find information about project timelines"
  • "Search for budget information"

System Commands:
  • help - Show this help
  • quit/exit/bye - Exit the program

💡 Tips:
  • The agent will guide you through corpus creation and management
  • Always specify which corpus to query, or create one first
  • Use specific questions for better search results
"""
    print(help_text)


def test_basic_functionality():
    """Test basic agent functionality."""
    print("\n🧪 Testing basic functionality...")
    
    try:
        # Test listing corpora
        print("Testing: List corpora...")
        response = root_agent.send_message("List all available corpora")
        print(f"Response: {response[:200]}...")
        
        return True
    except Exception as e:
        print(f"❌ Basic functionality test failed: {str(e)}")
        logger.error(f"Basic test error: {str(e)}", exc_info=True)
        return False


def main():
    """Main entry point."""
    print("🚀 Starting RAG Agent...")
    
    # Check setup
    if not check_setup():
        print("\n❌ Setup check failed. Please fix the issues above before continuing.")
        return 1
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality test failed.")
        return 1
    
    print("\n✅ All checks passed! The RAG Agent is ready.")
    
    # Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Interactive mode (chat with the agent)")
    print("2. Exit")
    
    while True:
        choice = input("Enter choice (1-2): ").strip()
        
        if choice == '1':
            try:
                require_vertex_ai()  # Ensure Vertex AI is ready
                interactive_mode()
                break
            except Exception as e:
                print(f"❌ Failed to start interactive mode: {str(e)}")
                return 1
        elif choice == '2':
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())