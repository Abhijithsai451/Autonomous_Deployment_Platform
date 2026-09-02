from typing import Dict, Any

from apps.agent_runtime.tools.base import BaseTool


class JSONTransformerTool(BaseTool):
    """
    Tool which performs the basic JSON transformations (filtering, key mapping, and merging)
    """
    name: str = "json_transformer"
    description: str = "Transforms, extracts, and remaps structured JSON data."
    version: str = "1.0.0"

    def _run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        source_data = parameters.get("data", {})
        target_keys = parameters.get("select_keys", [])
        key_mappings = parameters.get("remap_keys", {})

        if not isinstance(source_data, dict):
            raise ValueError("Input 'data' parameter must be a JSON object (dict).")

        # 1. Key Filtering
        if target_keys:
            filtered_data = {k: v for k, v in source_data.items() if k in target_keys}
        else:
            filtered_data = dict(source_data)

        # 2. Key Remapping
        transformed_data = {}
        for key, value in filtered_data.items():
            mapped_key = key_mappings.get(key, key)
            transformed_data[mapped_key] = value

        return {
            "transformed_data": transformed_data,
            "keys_processed": len(transformed_data),
        }

class TaskReaderTool(BaseTool):
    """
    Local tool that parses and validates raw task execution payloads.
    """

    name: str = "task_reader"
    description: str = "Reads, validates, and normalizes raw agent task parameters."
    version: str = "1.0.0"

    def _run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        raw_payload = parameters.get("payload", {})
        required_fields = parameters.get("required_fields", [])

        if not isinstance(raw_payload, dict):
            raise ValueError("Parameter 'payload' must be a valid dictionary.")

        # Check required fields
        missing_fields = [field for field in required_fields if field not in raw_payload]
        if missing_fields:
            raise ValueError(f"Missing required fields in payload: {', '.join(missing_fields)}")

        return {
            "normalized_payload": raw_payload,
            "is_valid": True,
            "field_count": len(raw_payload),
        }