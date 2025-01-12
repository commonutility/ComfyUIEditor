import anthropic
from typing import Dict, Any
import json
from json_feedback import validate_and_refine_workflow

class ClaudeClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(api_key=api_key)

    def _extract_json_from_response(self, text: str) -> str:
        """Extract JSON from Claude's response by looking for the first { and last }"""
        try:
            start = text.find('{')
            end = text.rindex('}') + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON object found in response")
            json_str = text[start:end]
            # Validate it's proper JSON
            json.loads(json_str)
            return json_str
        except Exception as e:
            print(f"Failed to extract JSON: {str(e)}")
            print(f"Response text: {text[:200]}...")  # Print first 200 chars
            raise ValueError("Could not extract valid JSON from response")

    def generate_workflow(self, description: str) -> str:
        """
        Generate a ComfyUI workflow JSON based on the provided description

        Args:
            description: User's description of the desired workflow

        Returns:
            str: JSON string containing the generated workflow
        """
        print(f"\nGenerating workflow for description: {description}")

        # Create the prompt template without f-strings
        example_workflow = '''
{
    "nodes": {
        "1": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "mountain landscape",
                "clip": ["4", 1]
            }
        }
    },
    "connections": {
        "3": {
            "inputs": {
                "positive": ["1", 0]
            }
        }
    }
}'''

        # Build the prompt with proper string formatting
        prompt = (
            f"You are a ComfyUI workflow generator. Generate a valid JSON workflow for this description: {description}\n\n"
            "IMPORTANT: Your response must contain ONLY the JSON object with no additional text, markdown formatting, or explanations.\n\n"
            "The workflow MUST include these required node types with their mandatory inputs:\n\n"
            "1. CLIPTextEncode:\n"
            '   - inputs: {\n'
            '       "text": "prompt text" (string),\n'
            '       "clip": [node_id, output_index] (list)\n'
            '   }\n\n'
            "2. KSampler:\n"
            '   - inputs: {\n'
            '       "seed": (integer),\n'
            '       "steps": (integer),\n'
            '       "cfg": (number),\n'
            '       "sampler_name": (string),\n'
            '       "scheduler": (string),\n'
            '       "denoise": (number between 0-1),\n'
            '       "model": [node_id, output_index],\n'
            '       "positive": [node_id, output_index],\n'
            '       "negative": [node_id, output_index],\n'
            '       "latent_image": [node_id, output_index]\n'
            '   }\n\n'
            "3. VAEDecode:\n"
            '   - inputs: {\n'
            '       "samples": [node_id, output_index],\n'
            '       "vae": [node_id, output_index]\n'
            '   }\n\n'
            "4. SaveImage:\n"
            '   - inputs: {\n'
            '       "images": [node_id, output_index],\n'
            '       "filename_prefix": (string, optional)\n'
            '   }\n\n'
            "All node connections must use the format: [source_node_id, output_index]\n"
            "Each node must have a unique numeric ID and include class_type and inputs fields.\n\n"
            f"Example workflow structure:\n{example_workflow}\n\n"
            "Remember: Return ONLY the JSON object with no additional text."
        )

        try:
            print("Sending request to Claude API...")
            response = self.client.messages.create(
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
            workflow_json = self._extract_json_from_response(response.content[0].text)

            # Validate and refine the workflow JSON
            refined_workflow = validate_and_refine_workflow(workflow_json)

            return json.dumps(refined_workflow)

        except anthropic.APIError as e:
            print(f"Claude API Error: {str(e)}")
            if "rate limit" in str(e).lower():
                raise Exception("Rate limit exceeded. Please try again in a few minutes.")
            raise Exception(f"Error calling Claude API: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error while generating workflow: {str(e)}")