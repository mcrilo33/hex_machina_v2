import re


def safe_artifact_key(s: str) -> str:
    """Sanitize artifact key to only contain lowercase letters, numbers, and dashes."""
    s = s.lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s
