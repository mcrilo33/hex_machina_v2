import json


def make_json_safe(val):
    """Ensure a value is JSON serializable, otherwise return its string representation."""
    try:
        json.dumps(val)
        return val
    except Exception:
        return str(val)
