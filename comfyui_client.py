import requests
import json
import websocket
from typing import Dict, Any, Optional
import uuid
import os

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = str(uuid.uuid4())

    def check_connection(self) -> tuple[bool, str]:
        """Check if ComfyUI is accessible"""
        try:
            requests.get(f"{self.base_url}/history", timeout=5)
            return True, "ComfyUI is running and accessible"
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to ComfyUI. Please ensure ComfyUI is running on port 8188"
        except Exception as e:
            return False, f"Error connecting to ComfyUI: {str(e)}"

    def queue_prompt(self, prompt: Dict[str, Any]) -> Optional[str]:
        """Queue a prompt for execution in ComfyUI"""
        try:
            response = requests.post(
                f"{self.base_url}/prompt",
                json={"prompt": prompt, "client_id": self.client_id},
                timeout=10
            )
            return response.json().get('prompt_id') if response.status_code == 200 else None
        except Exception as e:
            print(f"Error queueing prompt: {str(e)}")
            return None

    def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """Get execution history for a prompt"""
        try:
            response = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=5)
            return response.json().get(prompt_id) if response.status_code == 200 else None
        except Exception as e:
            print(f"Error getting history: {str(e)}")
            return None

    def get_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> Optional[bytes]:
        """Download an image from ComfyUI"""
        try:
            params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
            response = requests.get(f"{self.base_url}/view", params=params, timeout=10)
            return response.content if response.status_code == 200 else None
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
            return None

    def execute_workflow(self, workflow: Dict[Any, Any]) -> Optional[str]:
        """Execute a workflow and return the path to the generated image"""
        try:
            os.makedirs("outputs", exist_ok=True)

            # Connect to WebSocket
            ws = websocket.WebSocket()
            ws.connect(f"{self.ws_url}?clientId={self.client_id}")

            # Queue the prompt
            prompt_id = self.queue_prompt(workflow)
            if not prompt_id:
                return None

            # Wait for execution to complete
            while True:
                try:
                    out = ws.recv()
                    if isinstance(out, str):
                        message = json.loads(out)
                        if message['type'] == 'executing' and message['data']['node'] is None:
                            break
                except Exception:
                    continue

            # Get results
            history = self.get_history(prompt_id)
            if not history or 'outputs' not in history:
                return None

            # Find and save the first image output
            for node_output in history['outputs'].values():
                if 'images' in node_output and node_output['images']:
                    image = node_output['images'][0]
                    image_data = self.get_image(
                        filename=image['filename'],
                        subfolder=image.get('subfolder', ''),
                        folder_type=image.get('type', 'output')
                    )

                    if image_data:
                        output_path = f"outputs/comfyui_{image['filename']}"
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                        return output_path

            return None

        except Exception as e:
            print(f"Error executing workflow: {str(e)}")
            return None
        finally:
            if 'ws' in locals():
                try:
                    ws.close()
                except:
                    pass