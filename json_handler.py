import json
from typing import Dict, Any, List
from datetime import datetime
import os

class JsonHandler:
    # Required node types for text-to-image workflow
    REQUIRED_NODE_TYPES = {
        'CLIPTextEncode',
        'KSampler', 
        'VAEDecode',
        'SaveImage'
    }

    # Node-specific required inputs
    NODE_INPUT_REQUIREMENTS = {
        'KSampler': {
            'required_inputs': {
                'seed': int,
                'steps': int,
                'cfg': (int, float),
                'sampler_name': str,
                'scheduler': str,
                'denoise': (int, float),
                'model': list,
                'positive': list,
                'negative': list,
                'latent_image': list
            }
        },
        'CLIPTextEncode': {
            'required_inputs': {
                'text': str,
                'clip': list
            }
        },
        'VAEDecode': {
            'required_inputs': {
                'samples': list,
                'vae': list
            }
        },
        'SaveImage': {
            'required_inputs': {
                'images': list
            }
        }
    }

    # Basic schema for node structure
    NODE_SCHEMA = {
        'required_fields': {'class_type', 'inputs'},
        'optional_fields': {'id', 'type'}
    }

    @staticmethod
    def validate_node_inputs(node_id: str, node: Dict[str, Any]) -> None:
        """Validate inputs for specific node types"""
        node_type = node['class_type']
        if node_type in JsonHandler.NODE_INPUT_REQUIREMENTS:
            requirements = JsonHandler.NODE_INPUT_REQUIREMENTS[node_type]
            required_inputs = requirements['required_inputs']

            for input_name, expected_type in required_inputs.items():
                if input_name not in node['inputs']:
                    raise ValueError(f"Node {node_id} ({node_type}) missing required input: {input_name}")

                input_value = node['inputs'][input_name]

                # Handle multiple allowed types
                if isinstance(expected_type, tuple):
                    if not any(isinstance(input_value, t) for t in expected_type):
                        raise ValueError(
                            f"Node {node_id} ({node_type}) input '{input_name}' "
                            f"must be one of types {expected_type}, got {type(input_value)}"
                        )
                elif not isinstance(input_value, expected_type):
                    raise ValueError(
                        f"Node {node_id} ({node_type}) input '{input_name}' "
                        f"must be of type {expected_type}, got {type(input_value)}"
                    )

    @staticmethod
    def validate_connections(nodes: Dict[str, Any], connections: Dict[str, Any]) -> None:
        """Validate that connections reference valid nodes and outputs"""
        for target_id, connection_info in connections.items():
            if target_id not in nodes:
                raise ValueError(f"Connection references non-existent target node: {target_id}")

            if not isinstance(connection_info, dict) or 'inputs' not in connection_info:
                raise ValueError(f"Invalid connection structure for node {target_id}")

            for input_name, connection in connection_info['inputs'].items():
                if not isinstance(connection, list) or len(connection) != 2:
                    raise ValueError(
                        f"Invalid connection format for node {target_id}, "
                        f"input {input_name}: expected [node_id, output_index]"
                    )
                source_id, output_index = connection
                if str(source_id) not in nodes:
                    raise ValueError(
                        f"Connection from non-existent source node {source_id} "
                        f"to node {target_id}"
                    )

    @staticmethod
    def validate_workflow_json(workflow_json: str) -> Dict[Any, Any]:
        """
        Validate the workflow JSON string against ComfyUI schema requirements

        Args:
            workflow_json: JSON string to validate

        Returns:
            Dict containing the parsed JSON

        Raises:
            ValueError: If JSON is invalid or doesn't meet schema requirements
        """
        try:
            workflow = json.loads(workflow_json)

            # Basic structure validation
            if not isinstance(workflow, dict):
                raise ValueError("Workflow must be a JSON object")

            required_keys = ["nodes", "connections"]
            missing_keys = [key for key in required_keys if key not in workflow]
            if missing_keys:
                raise ValueError(f"Workflow missing required keys: {missing_keys}")

            # Validate nodes
            nodes = workflow['nodes']
            if not isinstance(nodes, dict):
                raise ValueError("'nodes' must be a dictionary")

            # Check for required node types
            found_node_types = set()
            for node_id, node in nodes.items():
                # Validate node structure
                missing_fields = JsonHandler.NODE_SCHEMA['required_fields'] - set(node.keys())
                if missing_fields:
                    raise ValueError(f"Node {node_id} missing required fields: {missing_fields}")

                found_node_types.add(node['class_type'])

                # Validate node-specific inputs
                JsonHandler.validate_node_inputs(node_id, node)

            missing_types = JsonHandler.REQUIRED_NODE_TYPES - found_node_types
            if missing_types:
                raise ValueError(f"Workflow missing required node types: {missing_types}")

            # Validate connections
            connections = workflow['connections']
            if not isinstance(connections, dict):
                raise ValueError("'connections' must be a dictionary")

            JsonHandler.validate_connections(nodes, connections)

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