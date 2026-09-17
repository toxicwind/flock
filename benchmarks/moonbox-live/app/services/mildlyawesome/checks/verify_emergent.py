import sys
import os

# Ensure we can import from repo root
sys.path.append(os.getcwd())

try:
    from emergent_api import AGENT_MANIFEST, VectorOps, CannabisOps, DayZOps
    
    print("✅ emergent_api package import: SUCCESS")
    print(f"✅ Manifest loaded with {len(AGENT_MANIFEST)} capabilities")
    for key, val in AGENT_MANIFEST.items():
        print(f"   - {key}: {val['usage_pattern']}")
        
except Exception as e:
    print(f"❌ Verification Failed: {e}")
    exit(1)
