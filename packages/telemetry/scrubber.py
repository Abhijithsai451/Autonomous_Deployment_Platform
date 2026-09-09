import re
from typing import Any, Dict

from packages.logging.redaction.redactor import SENSITIVE_KEYS

REDACTED_STRING = "SECRET VALUE"

SENSITIVE_KEYS = {
    "api_key", "apikey", "authorization", "bearer", "password",
    "secret", "token", "access_token", "refresh_token", "private_key",
    "x-api-key", "client_secret", "oauth_token"
}

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*", re.IGNORECASE),
]


def sanitize_telemetry_dict(data: Dict[str,Any])-> Dict[str,Any]:
    cleaned = {}
    for key, val in data.items():
        cleaned[key] = sanitize_value(key, val)
    return cleaned


def sanitize_value(key: str, value: Any) -> Any:
    """Scubs sensitive values based on key matching and inline pattern detection."""
    if key and str(key).lower() in SENSITIVE_KEYS:
        return REDACTED_STRING

    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                return REDACTED_STRING
        return value

    if isinstance(value, dict):
        return sanitize_telemetry_dict(value)

    if isinstance(value, list):
        return [sanitize_value("", item) for item in value]

    return value

