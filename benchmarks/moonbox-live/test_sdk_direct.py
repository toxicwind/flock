#!/usr/bin/env python3
"""Direct SDK test — uses config from portal-overlay, hits real gateway."""
import json, os, sys
sys.path.insert(0, "/mnt/agents/output")

# Read portal-overlay config directly
with open("/mnt/portal-overlay/.agent-gw.json") as f:
    cfg = json.load(f)

os.environ["KIMI_API_KEY"] = cfg.get("api_key", "")
os.environ["KIMI_BASE_URL"] = cfg.get("base_url", "")

from agent_gw_fixed import AgentGwClient, StorageFullError, QuotaError, APIError

print("=" * 60)
print("SDK DIRECT TEST")
print("=" * 60)

with AgentGwClient() as client:
    print(f"Base URL: {client.base_url}")
    print(f"Chat ID:  {client.kimi_chat_id}")
    print(f"API Key:  {client.api_key[:12]}...{client.api_key[-8:]}")
    print()

    # 1. list_models (lightweight)
    print("--- 1. list_models ---")
    try:
        models = client.list_models(timeout=15)
        print(f"SUCCESS: {json.dumps(models, indent=2)[:500]}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

    # 2. A tool call that might hit storage limits
    print("\n--- 2. generate_image (small, fast) ---")
    try:
        r = client.tools.generate_image(
            description="A small red circle on white background",
            ratio="1:1",
            resolution="1K",
            timeout=60
        )
        print(f"ToolResponse: {r}")
        print(f"is_success={r.is_success}, is_storage_full={r.is_storage_full}")
        r.raise_for_status()
        print(f"Result text: {r.text[:200]}")
    except StorageFullError as e:
        print(f"STORAGE FULL DETECTED: {e}")
    except QuotaError as e:
        print(f"QUOTA ERROR: {e}")
    except APIError as e:
        print(f"API ERROR: {e.status_code} — {e}")
    except Exception as e:
        print(f"UNEXPECTED: {type(e).__name__}: {e}")

    # 3. Compare with BROKEN SDK behavior
    print("\n--- 3. BROKEN SDK simulation ---")
    # Simulate what the OLD SDK does with a plain-string error
    from agent_gw_fixed import ToolResponse
    raw_error = "storage quota exceeded"
    old_behavior = {"is_success": True, "result": {"user": [{"text": raw_error}]}}
    print(f"OLD SDK would return: is_success=True, text='{raw_error}'")
    
    new_behavior = ToolResponse(raw_error)
    print(f"NEW SDK returns:      is_success={new_behavior.is_success}, is_storage_full={new_behavior.is_storage_full}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
