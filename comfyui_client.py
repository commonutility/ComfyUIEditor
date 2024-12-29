import requests
import json
import time
from typing import Dict, Any, Optional
import base64
from pathlib import Path
import os

class ComfyUIClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8188):
        self.base_url = f"http://{host}:{port}"
        
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
            
            # Queue the prompt
            queue_url = f"{self.base_url}/prompt"
            response = requests.post(queue_url, json={"prompt": workflow})
            
            if response.status_code != 200:
                print(f"Error queueing workflow: {response.text}")
                return None
                
            prompt_id = response.json()['prompt_id']
            
            # Poll for completion
            while True:
                history_url = f"{self.base_url}/history"
                history = requests.get(history_url).json()
                
                if prompt_id in history:
                    if 'outputs' in history[prompt_id]:
                        # Get the output image node
                        outputs = history[prompt_id]['outputs']
                        image_data = None
                        
                        # Find the first SaveImage node output
                        for node_id, node_output in outputs.items():
                            if 'images' in node_output:
                                image_data = node_output['images'][0]
                                break
                        
                        if image_data:
                            # Save the image locally
                            image_filename = image_data['filename']
                            image_url = f"{self.base_url}/view?filename={image_filename}"
                            
                            image_response = requests.get(image_url)
                            if image_response.status_code == 200:
                                output_path = f"outputs/comfyui_{image_filename}"
                                with open(output_path, 'wb') as f:
                                    f.write(image_response.content)
                                print(f"\nImage saved to: {output_path}")
                                return output_path
                        
                        print("No image output found in workflow results")
                        return None
                        
                    elif 'error' in history[prompt_id]:
                        print(f"\nError executing workflow: {history[prompt_id]['error']}")
                        return None
                        
                print("Waiting for workflow execution to complete...")
                time.sleep(1)
                
        except requests.exceptions.ConnectionError:
            print("\nError: Could not connect to ComfyUI. Please ensure ComfyUI is running and accessible.")
            return None
        except Exception as e:
            print(f"\nUnexpected error executing workflow: {str(e)}")
            return None
