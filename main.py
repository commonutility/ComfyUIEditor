import sys
import argparse
from config import Config
from claude_client import ClaudeClient
from json_handler import JsonHandler

def process_workflow(description: str) -> None:
    """Process a single workflow description and generate the JSON file"""
    try:
        config = Config()
        if not config.validate():
            print("Error: Configuration is invalid. Please check your environment variables.")
            sys.exit(1)

        # Initialize Claude client
        claude_client = ClaudeClient(config.get_api_key())

        print("\nGenerating workflow...")
        workflow_json = claude_client.generate_workflow(description)

        # Validate the generated JSON
        print("Validating workflow JSON...")
        workflow = JsonHandler.validate_workflow_json(workflow_json)

        # Save the workflow
        print("Saving workflow...")
        filepath = JsonHandler.save_workflow(workflow, description)

        print(f"\nSuccess! Workflow saved to: {filepath}")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

def main():
    # Check if description is provided as command line argument
    parser = argparse.ArgumentParser(description='ComfyUI Workflow Generator')
    parser.add_argument('--description', '-d', help='Workflow description to process')
    args = parser.parse_args()

    if args.description:
        # Non-interactive mode
        process_workflow(args.description)
        return

    # Interactive mode
    print("ComfyUI Workflow Generator")
    print("=========================")

    print("\nPlease describe the ComfyUI workflow you want to create.")
    print("Example: 'Create a workflow that loads an image, applies a blur effect, and saves the result'")
    print("\nEnter your description (or 'quit' to exit):")

    while True:
        try:
            description = input("> ").strip()

            if description.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break

            if not description:
                print("Please enter a description or 'quit' to exit.")
                continue

            process_workflow(description)
            print("\nEnter another description or 'quit' to exit:")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == "__main__":
    main()