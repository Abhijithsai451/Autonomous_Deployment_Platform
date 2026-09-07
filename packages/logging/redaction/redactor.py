import re
from typing import Any, Dict

SENSITIVE_KEYS = {
    "authorization",
    "x-api-key",
    "password",
    "secret",
    "token",
    "bearer",
    "oauth_token",
    "api_key",
    "private_key",
}

REDACTED_VALUE = "[SECRET VALUE]"

def mask_sensitive_data(val: Any)-> Any:
    if isinstance(val, dict):
        return {
            k: (REDACTED_VALUE if k.lower() in SENSITIVE_KEYS else mask_sensitive_data(v))
            for k, v in val.items()
        }
    elif isinstance(val, list):
        return [mask_sensitive_data(item) for item in val]
    return val

def redact_sensitive_middleware(logger: Any, method_name: str, event_dict: Dict[str, Any])-> Dict[str, Any]:
    """ StructLog processor to strip out sensitive data keys from event dictionaries"""
    return mask_sensitive_data(event_dict)