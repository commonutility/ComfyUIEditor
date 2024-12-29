import json
from typing import Dict, Any
from datetime import datetime
import os

class JsonHandler:
    @staticmethod
    def validate_workflow_json(workflow_json: str) -> Dict[Any, Any]:
        """
        Validate the workflow JSON string and convert it to a dictionary

        Args:
            workflow_json: JSON string to validate

        Returns:
            Dict containing the parsed JSON

        Raises:
            ValueError: If JSON is invalid or missing required fields
        """
        try:
            workflow = json.loads(workflow_json)

            # Basic validation of ComfyUI workflow structure
            if not isinstance(workflow, dict):
                raise ValueError("Workflow must be a JSON object")

            # Check for required top-level keys
            required_keys = ["nodes", "connections"]
            missing_keys = [key for key in required_keys if key not in workflow]
            if missing_keys:
                raise ValueError(f"Workflow missing required keys: {missing_keys}")

            return workflow

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")

    @staticmethod
    def save_workflow(workflow: Dict[Any, Any], description: str) -> str:
        """
        Save the workflow to a JSON file with a timestamp-based filename

        Args:
            workflow: Workflow dictionary to save
            description: Original workflow description for the filename

        Returns:
            Path to the saved file
        """
        # Create a filename-safe version of the description
        safe_description = "".join(c for c in description[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_description = safe_description.replace(' ', '_')

        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create filename
        filename = f"workflow_{timestamp}_{safe_description}.json"

        # Ensure the output directory exists with proper permissions
        os.makedirs("outputs", exist_ok=True)
        filepath = os.path.join("outputs", filename)

        # Save the file with pretty printing for better readability
        try:
            with open(filepath, 'w') as f:
                json.dump(workflow, f, indent=2)
            print(f"\nWorkflow JSON saved successfully to: {filepath}")
            return filepath
        except Exception as e:
            print(f"\nError saving workflow JSON: {str(e)}")
            raise