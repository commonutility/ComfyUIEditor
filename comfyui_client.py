import requests
import json
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import os

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"

    def check_connection(self) -> Tuple[bool, str]:
        """Check if ComfyUI is accessible and return status with message"""
        try:
            response = requests.get(f"{self.base_url}/object_info", timeout=5)
            if response.status_code == 200:
                return True, "ComfyUI is running and accessible"
            return False, f"ComfyUI returned unexpected status: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to ComfyUI. Please ensure ComfyUI is running on port 8188"
        except requests.exceptions.Timeout:
            return False, "Connection to ComfyUI timed out. Please check if it's responding"
        except Exception as e:
            return False, f"Unexpected error connecting to ComfyUI: {str(e)}"

    def execute_workflow(self, workflow: Dict[Any, Any]) -> Optional[str]:
        """
        Execute a workflow in ComfyUI and return the path to the generated image

        Args:
            workflow: The workflow dictionary to execute

        Returns:
            Optional[str]: Path to the generated image if successful, None otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs("outputs", exist_ok=True)

            print("\nExecuting workflow in ComfyUI...")

            # Check ComfyUI connection first
            is_connected, message = self.check_connection()
            if not is_connected:
                print(f"\nError: {message}")
                print("\nPlease ensure:")
                print("1. ComfyUI is running locally on port 8188")
                print("2. Required model checkpoints are installed")
                print("3. Your GPU has sufficient memory available")
                return None

            print("ComfyUI connection verified successfully")

            # Queue the prompt
            queue_url = f"{self.base_url}/prompt"
            print(f"Queueing workflow at: {queue_url}")

            try:
                response = requests.post(queue_url, json={"prompt": workflow}, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"\nError queueing workflow: {str(e)}")
                return None

            prompt_id = response.json()['prompt_id']
            print(f"Workflow queued successfully with prompt ID: {prompt_id}")

            # Poll for completion
            retry_count = 0
            max_retries = 60  # 1 minute timeout
            while retry_count < max_retries:
                try:
                    history_url = f"{self.base_url}/history"
                    history = requests.get(history_url, timeout=5).json()

                    if prompt_id in history:
                        if 'outputs' in history[prompt_id]:
                            outputs = history[prompt_id]['outputs']

                            # Find the first SaveImage node output
                            for node_id, node_output in outputs.items():
                                if 'images' in node_output:
                                    image_data = node_output['images'][0]
                                    image_filename = image_data['filename']
                                    image_url = f"{self.base_url}/view?filename={image_filename}"

                                    print(f"Retrieving generated image from: {image_url}")
                                    image_response = requests.get(image_url, timeout=10)

                                    if image_response.status_code == 200:
                                        output_path = f"outputs/comfyui_{image_filename}"
                                        with open(output_path, 'wb') as f:
                                            f.write(image_response.content)
                                        print(f"\nImage saved to: {output_path}")
                                        return output_path

                                    print(f"Error retrieving image: {image_response.status_code}")
                                    return None

                            print("No image output found in workflow results")
                            return None

                        elif 'error' in history[prompt_id]:
                            error_msg = history[prompt_id]['error']
                            print(f"\nError executing workflow: {error_msg}")

                            if "CUDA out of memory" in error_msg:
                                print("\nSuggestion: Try reducing the image size or batch size in the workflow")
                            elif "checkpoint" in error_msg.lower():
                                print("\nSuggestion: Ensure all required model checkpoints are installed in ComfyUI")
                            return None

                    print("Waiting for workflow execution to complete...")
                    time.sleep(1)
                    retry_count += 1

                except requests.exceptions.RequestException as e:
                    print(f"\nError checking workflow status: {str(e)}")
                    return None

            print("\nTimeout: Workflow execution took too long")
            return None

        except Exception as e:
            print(f"\nUnexpected error executing workflow: {str(e)}")
            return None

    def get_node_types(self) -> Optional[Dict]:
        """Get available node types from ComfyUI"""
        try:
            response = requests.get(f"{self.base_url}/object_info", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting node types: {str(e)}")
            return None