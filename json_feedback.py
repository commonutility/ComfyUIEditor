import json
from typing import Dict, Any, Optional
from json_handler import JsonHandler
from claude_client import ClaudeClient

def validate_and_refine_workflow(workflow_json: str) -> Dict[str, Any]:
    """
    Validate the workflow JSON and refine it if necessary.

    Args:
        workflow_json: JSON string to validate and refine

    Returns:
        Dict containing the refined JSON
    """
    error_log: Optional[str] = None

    print(f"\nVALIDATION_IN_JSONFEEDBACK")

    try:
        # Validate the workflow JSON
        workflow = JsonHandler.validate_workflow_json(workflow_json)
        return workflow
    except ValueError as e:
        error_log = str(e)
        print(f"\nVALIDATION_IN_JSONFEEDBACK")
        print(f"Validation error: {error_log}")

    # If validation fails, refine the workflow
    try:
        workflow = json.loads(workflow_json)
        refined_workflow = refine_workflow(workflow, error_log)
        return refined_workflow
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {str(e)}")

def refine_workflow(workflow: Dict[str, Any], error_log: Optional[str]) -> Dict[str, Any]:
    """
    Refine the workflow JSON to correct validation errors.

    Args:
        workflow: Dictionary containing the workflow JSON
        error_log: String containing validation errors

    Returns:
        Dict containing the refined JSON
    """
    if error_log:
        print(f"\nRefining workflow based on errors: {error_log}")
        # Initialize ClaudeClient with your API key
        claude_client = ClaudeClient(api_key="your_anthropic_api_key")

        # Use Claude to refine the workflow
        refined_workflow = claude_client.refine_workflow_with_claude(workflow, error_log)
        return refined_workflow

    return workflow
