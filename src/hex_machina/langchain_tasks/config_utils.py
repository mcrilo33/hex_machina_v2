"""
Configuration utilities for LangChain tasks.

This module provides shared utilities for processing configuration files,
including environment variable substitution.
"""

import os
from typing import Any


def resolve_env_vars(obj: Any) -> Any:
    """Recursively resolve environment variables in config values.

    Args:
        obj: Configuration object (dict, list, str, or other)

    Returns:
        Object with environment variables resolved

    Examples:
        >>> resolve_env_vars({"api_key": "${MY_API_KEY}"})
        {"api_key": "actual_key_value"}

        >>> resolve_env_vars("${MY_VAR}")
        "actual_var_value"
    """
    if isinstance(obj, dict):
        return {k: resolve_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_env_vars(item) for item in obj]
    elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
        env_var = obj[2:-1]  # Remove ${ and }
        return os.getenv(env_var, obj)  # Return original if env var not found
    else:
        return obj
