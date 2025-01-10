import logging
import requests
import json
import websocket
from typing import Dict, Any, Optional
import uuid
import os
import socket
from urllib import request

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188, use_preloaded_json: bool = False, preloaded_json_path: str = "outputs/working_scale.json"):
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/ws"
        self.client_id = str(uuid.uuid4())
        self.use_preloaded_json = use_preloaded_json
        self.preloaded_json_path = preloaded_json_path

        self.server_address = "127.0.0.1:8188"

    def check_connection(self) -> tuple[bool, str]:
        """Check if ComfyUI is accessible"""
        try:
            requests.get(f"{self.base_url}/history", timeout=5)
            return True, "ComfyUI is running and accessible"
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to ComfyUI. Please ensure ComfyUI is running on port 8188"
        except Exception as e:
            return False, f"Error connecting to ComfyUI: {str(e)}"

    def queue_prompt(self, prompt: Dict[Any,Any]) -> Optional[str]:
        """Queue a prompt for execution in ComfyUI"""
        try:
            p = {"prompt": prompt}
            data = json.dumps(p).encode('utf-8')
            print("\ndata",type(data), data)
            req = request.Request(f"{self.base_url}/prompt", data=data, headers={'Content-Type': 'application/json'})
            with request.urlopen(req) as response:
                if response.status == 200:
                    print("successfully")
                    response_data = json.loads(response.read().decode('utf-8'))
                    return response_data.get('prompt_id')
                else:
                    print(f"Error: Received non-200 status code: {response.status}")
                    print(f"Response headers: {response.headers}")
                    print(f"Response content: {response.read().decode('utf-8')}")
                    return None
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

    def execute_workflow(self, workflow: Dict[Any, Any], preloaded: bool = False) -> Optional[str]:
        """Execute a workflow and return the path to the generated image"""
        try:
            os.makedirs("outputs", exist_ok=True)

            # Create a socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.base_url.split("//")[1].split(":")[0], int(self.base_url.split(":")[-1])))

            # Create a dummy environ and rfile
            environ = {}
            rfile = sock.makefile('rb', -1)

            # Connect to WebSocket with headers
            ws = websocket.WebSocket()
            ws.connect(f"{self.ws_url}?clientId={self.client_id}", header={"Origin": self.base_url})

            # Convert workflow dictionary to JSON string
            workflow_json = json.dumps(workflow)

            print("workflow json\n", workflow_json)

            # Queue the prompt
            # workflow json returns a Error:500 internal server, shou
            prompt_id = self.queue_prompt(workflow)
            if not prompt_id:
                print("RETURNED NONE")
                return None

            # Wait for execution to complete
            while True:
                print("\n...")
                try:
                    out = ws.recv()
                    if isinstance(out, str):
                        print("\nReceived WebSocket message:", out)
                        message = json.loads(out)
                        if message['type'] == 'status':
                            queue_remaining = message['data']['status']['exec_info']['queue_remaining']
                            print(f"Queue remaining: {queue_remaining}")
                            if queue_remaining == 0:
                                print("\nExecution completed")
                                break
                except Exception as e:
                    logging.error(f"Error receiving WebSocket message: {str(e)}")
                    continue

            print("\nExecution completed")

            # Get results
            history = self.get_history(prompt_id)
            if not history or 'outputs' not in history:
                return None

            # Find and save the first image output
            for node_output in history['outputs'].values():
                print("\nNODE OUTPUT", node_output)
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
            logging.error(f"Error executing workflow: {str(e)}")
            return None
        finally:
            if 'ws' in locals():
                try:
                    ws.close()
                except Exception as e:
                    logging.error(f"Error closing WebSocket: {str(e)}")
            if 'sock' in locals():
                try:
                    sock.close()
                except Exception as e:
                    logging.error(f"Error closing socket: {str(e)}")

    def test_preloaded_json(self) -> None:
        """Test the ComfyUI API calls with a preloaded JSON"""
        if self.use_preloaded_json and self.preloaded_json_path:
            print("Testing ComfyUI with preloaded JSON...")
            try:
                with open(self.preloaded_json_path, 'r') as f:
                    workflow = json.load(f)
                result = self.execute_workflow(workflow)
                if result:
                    print(f"Preloaded JSON test successful. Image saved at: {result}")
                else:
                    print("Preloaded JSON test failed.")
            except Exception as e:
                print(f"Error testing preloaded JSON: {str(e)}")