import anthropic
from typing import Dict, Any

class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)

    def generate_workflow(self, description: str) -> str:
        """
        Generate a ComfyUI workflow JSON based on the provided description

        Args:
            description: User's description of the desired workflow

        Returns:
            str: JSON string containing the generated workflow
        """
        prompt = f"""
        Create a ComfyUI workflow JSON based on this description: {description}

        The JSON should be valid and follow ComfyUI's format with:
        - Unique numeric IDs for nodes
        - Proper node class names
        - Valid connections between nodes
        - Appropriate input values

        Return ONLY the JSON object without any additional text or formatting.
        """

        try:
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=4096,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Return the raw text which should be a JSON string
            return response.content[0].text

        except anthropic.APIError as e:
            raise Exception(f"Error calling Claude API: {str(e)}")