import anthropic
from typing import Dict, Any
import json

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
        prompt = f"""You are a ComfyUI workflow generator. Generate a valid JSON workflow for this description: {description}

IMPORTANT: Your response must contain ONLY the JSON object with no additional text, markdown formatting, or explanations.

The workflow must follow this exact structure:
{{
    "nodes": {{
        "1": {{
            "id": 1,
            "type": "CLIPTextEncode",
            "class_type": "CLIPTextEncode",
            "inputs": {{
                "text": "your prompt here",
                "clip": ["5", 0]
            }}
        }},
        "2": {{
            "id": 2,
            "type": "KSampler",
            "class_type": "KSampler",
            "inputs": {{
                "seed": 5567465765,
                "steps": 20,
                "cfg": 7,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1,
                "model": ["4", 0],
                "positive": ["1", 0],
                "negative": ["3", 0],
                "latent_image": ["6", 0]
            }}
        }}
    }},
    "connections": {{
        "2": {{
            "inputs": {{
                "positive": ["1", 0]
            }}
        }}
    }}
}}

Include these essential nodes for text-to-image:
1. CLIPTextEncode for the prompt
2. KSampler for image generation
3. VAEDecode for processing
4. SaveImage for output

Remember: Return ONLY the JSON object with no additional text."""

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
            return workflow_json

        except anthropic.APIError as e:
            print(f"Claude API Error: {str(e)}")
            if "rate limit" in str(e).lower():
                raise Exception("Rate limit exceeded. Please try again in a few minutes.")
            raise Exception(f"Error calling Claude API: {str(e)}")
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error while generating workflow: {str(e)}")