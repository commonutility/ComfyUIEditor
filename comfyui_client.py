import requests
import json
import time
import socket
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import os
import re
from urllib.parse import urlparse

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        """
        Initialize the ComfyUI client

        Args:
            host: The hostname where ComfyUI is running (default: 127.0.0.1)
            port: The port number ComfyUI is listening on (default: 8188)
        """
        # Handle different host formats
        if host.startswith(('http://', 'https://')):
            parsed = urlparse(host)
            self.host = parsed.hostname or "127.0.0.1"
            self.port = parsed.port or port
        else:
            self.host = host
            self.port = port

        # Normalize localhost to 127.0.0.1
        if self.host in ('localhost', '0.0.0.0'):
            self.host = '127.0.0.1'

        self.base_url = f"http://{self.host}:{self.port}"
        # Add headers for CORS and debugging
        self.headers = {
            'Origin': 'http://127.0.0.1:8188',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def _test_port_connection(self) -> Tuple[bool, str]:
        """Test raw TCP connection to the port"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            print(f"\nTesting TCP connection to {self.host}:{self.port}")
            result = sock.connect_ex((self.host, self.port))
            sock.close()

            if result == 0:
                print("TCP connection successful!")
                return True, "Port is open and accepting connections"
            else:
                error_msg = f"Port {self.port} is not accepting connections (Error code: {result})"
                print(f"TCP connection failed: {error_msg}")
                return False, error_msg
        except Exception as e:
            error_msg = f"Error testing port connection: {str(e)}"
            print(f"TCP connection error: {error_msg}")
            return False, error_msg

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Make HTTP request with detailed logging"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        print(f"\nMaking {method} request to: {url}")
        print(f"Headers: {self.headers}")
        if 'json' in kwargs:
            print(f"Request body: {json.dumps(kwargs['json'], indent=2)}")

        try:
            response = requests.request(
                method,
                url,
                headers=self.headers,
                timeout=10,
                **kwargs
            )
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response content: {response.text[:200]}...") # Print first 200 chars of response
            return response
        except Exception as e:
            print(f"Request failed: {str(e)}")
            return None

    def check_connection(self) -> Tuple[bool, str]:
        """Check if ComfyUI is accessible and return status with message"""
        max_retries = 3
        retry_delay = 2  # seconds

        # First test raw TCP connection
        port_accessible, port_message = self._test_port_connection()
        if not port_accessible:
            print(f"\nPort connection test failed: {port_message}")
            print("\nPlease verify:")
            print(f"1. ComfyUI is running and accessible at: {self.base_url}")
            print("2. No firewall is blocking the connection")
            print("3. The correct host and port are being used")
            return False, port_message

        # Try different API endpoints that ComfyUI exposes
        endpoints_to_try = ['object_info', '', 'prompt']

        for attempt in range(max_retries):
            print(f"\nConnection attempt {attempt + 1}/{max_retries}")

            for endpoint in endpoints_to_try:
                try:
                    response = self._make_request('GET', endpoint)

                    if response and response.status_code == 200:
                        print(f"Successfully connected to ComfyUI API at endpoint: /{endpoint}")
                        return True, "ComfyUI is running and accessible"

                    print(f"Endpoint /{endpoint} returned status: {response.status_code if response else 'No response'}")

                except Exception as e:
                    print(f"Error trying endpoint /{endpoint}: {str(e)}")

            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

        return False, "Failed to connect to ComfyUI after trying multiple endpoints"

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
                response = self._make_request('POST', 'prompt', json={"prompt": workflow})
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
                    history = self._make_request('GET', 'history').json()

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
                                    image_response = self._make_request('GET', f"view?filename={image_filename}")

                                    if image_response and image_response.status_code == 200:
                                        output_path = f"outputs/comfyui_{image_filename}"
                                        with open(output_path, 'wb') as f:
                                            f.write(image_response.content)
                                        print(f"\nImage saved to: {output_path}")
                                        return output_path

                                    print(f"Error retrieving image: {image_response.status_code if image_response else 'No response'}")
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
            response = self._make_request('GET', 'object_info')
            if response and response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting node types: {str(e)}")
            return None