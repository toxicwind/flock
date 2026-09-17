import json
import os

_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "manifest.json")

try:
    with open(_MANIFEST_PATH, "r") as f:
        AGENT_MANIFEST = json.load(f)
except Exception as e:
    # Fallback if json is missing during dev
    AGENT_MANIFEST = {"error": str(e)}
