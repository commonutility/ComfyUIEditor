import json
from typing import Dict, Any, Optional
from json_handler import JsonHandler
from claude_client import ClaudeClient
from config import Config

def validate_and_refine_workflow(workflow_json: str) -> Dict[str, Any]:
    """
    Validate the workflow JSON and refine it if necessary.

    Args:
        workflow_json: JSON string to validate and refine

    Returns:
        Dict containing the refined JSON
    """
    error_log: Optional[str] = None

    print(f"\nREFINING_IN_JSONFEEDBACK")

    try:
        # Validate the workflow JSON
        workflow = JsonHandler.validate_workflow_json(workflow_json)
        return workflow
    except ValueError as e:
        error_log = str(e)
        print(f"Validation error: {error_log}")

    # If validation fails, refine the workflow
    try:
        workflow = json.loads(workflow_json)
        
        # Retrieve the API key using Config
        config = Config()
        api_key = config.get_api_key()
        
        # Initialize ClaudeClient with the API key
        claude_client = ClaudeClient(api_key)
        
        refined_workflow = refine_workflow(workflow, error_log, claude_client)
        return refined_workflow
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")

def refine_workflow(workflow: Dict[str, Any], error_log: Optional[str], claude_client: ClaudeClient) -> Dict[str, Any]:
    """
    Refine the workflow JSON to correct validation errors.

    Args:
        workflow: Dictionary containing the workflow JSON
        error_log: String containing validation errors
        claude_client: Instance of ClaudeClient

    Returns:
        Dict containing the refined JSON
    """
    if error_log:
        print(f"\nRefining workflow based on errors: {error_log}")
        
        prompt = (
            "You previously generated a ComfyUI workflow JSON, but it contains some errors. "
            "Here is the workflow JSON:\n\n"
            f"{json.dumps(workflow, indent=2)}\n\n"
            "And here are the errors:\n\n"
            f"{error_log}\n\n"
            "Please correct the errors and provide a refined JSON workflow. "
            "IMPORTANT: Your response must contain ONLY the JSON object with no additional text, markdown formatting, or explanations."
        )

        try:
            print("Sending [REFINE] request to Claude API...")
            response = claude_client.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                timeout=30
            )

            print("Received response from Claude API")

            if not response.content or not response.content[0].text:
                raise Exception("Empty response received from Claude API")

            # Extract and validate JSON from the response
            refined_workflow_json = claude_client._extract_json_from_response(response.content[0].text)
            refined_workflow = json.loads(refined_workflow_json)
            return refined_workflow

        except anthropic.APIError as e:
            print(f"Claude API Error: {str(e)}")
            if "rate limit" in str(e).lower():
                raise Exception("Rate limit exceeded. Please try again in a few minutes.")
            raise Exception(f"Error calling Claude API: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error while generating workflow: {str(e)}")

    return workflow
