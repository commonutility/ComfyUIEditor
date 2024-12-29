import sys
import argparse
from config import Config
from claude_client import ClaudeClient
from json_handler import JsonHandler
from comfyui_client import ComfyUIClient

def process_workflow(description: str) -> None:
    """Process a single workflow description and generate the JSON file"""
    try:
        config = Config()
        if not config.validate():
            print("Error: Configuration is invalid. Please check your environment variables.")
            sys.exit(1)

        # Initialize clients
        claude_client = ClaudeClient(config.get_api_key())
        comfyui_client = ComfyUIClient()

        # Check ComfyUI connection first
        is_connected, message = comfyui_client.check_connection()
        if not is_connected:
            print(f"\nWarning: {message}")
            print("\nTo use ComfyUI:")
            print("1. Download and run ComfyUI locally from: https://github.com/comfyanonymous/ComfyUI")
            print("2. Ensure ComfyUI is running on port 8188")
            print("\nWill generate and save the workflow JSON, but cannot execute it in ComfyUI.")
        else:
            print("\nComfyUI connection successful!")

        print("\nGenerating workflow...")
        workflow_json = claude_client.generate_workflow(description)

        # Validate the generated JSON
        print("\nValidating workflow JSON...")
        workflow = JsonHandler.validate_workflow_json(workflow_json)
        print("✓ JSON validation successful")

        # Save the workflow
        print("\nSaving workflow...")
        filepath = JsonHandler.save_workflow(workflow, description)
        print(f"✓ Workflow saved to: {filepath}")

        # Only try to execute if ComfyUI is available
        if is_connected:
            print("\nExecuting workflow in ComfyUI...")
            output_path = comfyui_client.execute_workflow(workflow)

            if output_path:
                print(f"✓ Generated image saved to: {output_path}")
            else:
                print("\nWarning: Failed to execute workflow in ComfyUI. The workflow JSON has been saved and can be imported manually.")

    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

def test_workflow():
    """Run a test workflow to verify functionality"""
    print("\n=== Running Test Workflow ===")
    test_description = "Create a simple workflow that generates a photo of a mountain landscape"
    try:
        process_workflow(test_description)
        print("\n✓ Test workflow completed successfully")
        return True
    except Exception as e:
        print(f"\n✗ Test workflow failed: {str(e)}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='ComfyUI Workflow Generator')
    parser.add_argument('--description', '-d', help='Workflow description to process')
    parser.add_argument('--test', action='store_true', help='Run test workflow')
    args = parser.parse_args()

    if args.test:
        test_workflow()
        return

    if args.description:
        # Non-interactive mode
        process_workflow(args.description)
        return

    # Interactive mode
    print("""ComfyUI Workflow Generator
=========================

This tool generates ComfyUI workflows from text descriptions using Claude AI.
Requirements:
1. ANTHROPIC_API_KEY environment variable must be set
2. ComfyUI must be running locally on port 8188 (optional, for workflow execution)

If ComfyUI is not running, workflows will still be generated and saved as JSON files.
You can import these files manually into ComfyUI later.
""")

    print("\nPlease describe the ComfyUI workflow you want to create.")
    print("Example: 'Create a workflow that generates a photo of a mountain landscape at sunset'")
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