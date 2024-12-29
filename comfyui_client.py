import requests
import json
import time
from typing import Dict, Any, Optional, Tuple
import uuid
import os
import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = str(uuid.uuid4())
        self.ws = None

    def check_connection(self) -> Tuple[bool, str]:
        """Check if ComfyUI is accessible"""
        try:
            response = requests.get(f"{self.base_url}/history", timeout=5)
            if response.status_code == 200:
                return True, "ComfyUI is running and accessible"
            return False, f"ComfyUI returned unexpected status: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to ComfyUI. Please ensure ComfyUI is running on port 8188"
        except requests.exceptions.Timeout:
            return False, "Connection to ComfyUI timed out. Please check if it's running correctly"
        except Exception as e:
            return False, f"Unexpected error connecting to ComfyUI: {str(e)}"

    def queue_prompt(self, prompt: Dict[str, Any]) -> Optional[str]:
        """Queue a prompt for execution in ComfyUI"""
        try:
            data = {
                "prompt": prompt,
                "client_id": self.client_id  # Include client_id as shown in examples
            }
            response = requests.post(
                f"{self.base_url}/prompt",
                json=data,
                timeout=10
            )

            if response.status_code != 200:
                print(f"Error queueing prompt: {response.text}")
                return None

            return response.json().get('prompt_id')

        except Exception as e:
            print(f"Error queueing prompt: {str(e)}")
            return None

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """Get an image from ComfyUI's output directory"""
        try:
            params = {
                "filename": filename,
                "subfolder": subfolder,
                "type": folder_type
            }
            response = requests.get(f"{self.base_url}/view", params=params, timeout=10)
            if response.status_code == 200:
                return response.content
            return None
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
            return None

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get the history for a specific prompt"""
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=5)
            if response.status_code == 200:
                history = response.json()
                return history.get(prompt_id)
            return None
        except Exception as e:
            print(f"Error getting history: {str(e)}")
            return None

    def execute_workflow(self, workflow: Dict[Any, Any]) -> Optional[str]:
        """
        Execute a workflow in ComfyUI and return the path to the generated image

        Args:
            workflow: The workflow dictionary to execute

        Returns:
            Optional[str]: Path to the generated image if successful, None otherwise
        """
        # First check if ComfyUI is accessible
        is_connected, message = self.check_connection()
        if not is_connected:
            print(f"\nError: {message}")
            return None

        try:
            # Ensure output directory exists
            os.makedirs("outputs", exist_ok=True)

            print("\nExecuting workflow in ComfyUI...")

            # Connect to WebSocket for real-time updates
            self.ws = websocket.WebSocket()
            self.ws.connect(f"{self.ws_url}?clientId={self.client_id}")

            # Queue the prompt and get prompt_id
            prompt_id = self.queue_prompt(workflow)
            if not prompt_id:
                return None

            print(f"Workflow queued with prompt ID: {prompt_id}")

            # Poll for completion with timeout
            start_time = time.time()
            timeout = 300  # 5 minutes timeout
            retry_count = 0
            max_retries = 3

            while True:
                if time.time() - start_time > timeout:
                    print("Timeout waiting for workflow execution")
                    return None

                try:
                    # Wait for WebSocket message
                    out = self.ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message['type'] == 'executing':
                            data = message['data']
                            if data['node'] is None and data['prompt_id'] == prompt_id:
                                # Execution is done, get the results
                                history = self.get_history(prompt_id)

                                if history and 'outputs' in history:
                                    # Find the first SaveImage node output
                                    for node_id, node_output in history['outputs'].items():
                                        if 'images' in node_output and node_output['images']:
                                            image_data = node_output['images'][0]

                                            # Download and save the image
                                            image_content = self.get_image(
                                                filename=image_data['filename'],
                                                subfolder=image_data.get('subfolder', ''),
                                                folder_type=image_data.get('type', 'output')
                                            )

                                            if image_content:
                                                output_path = f"outputs/comfyui_{image_data['filename']}"
                                                with open(output_path, 'wb') as f:
                                                    f.write(image_content)
                                                print(f"\nImage saved to: {output_path}")
                                                self.ws.close()
                                                return output_path

                                            print("Failed to download the generated image")
                                            return None

                                    print("No image output found in workflow results")
                                    return None

                                elif history and 'error' in history:
                                    print(f"\nError executing workflow: {history['error']}")
                                    return None

                except websocket.WebSocketException as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        print(f"Failed to check workflow status after {max_retries} attempts: {str(e)}")
                        return None
                    print(f"WebSocket error (attempt {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(2)
                    continue

        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to ComfyUI. Please ensure ComfyUI is running and accessible.")
            return None
        except Exception as e:
            print(f"\nUnexpected error executing workflow: {str(e)}")
            return None
        finally:
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass