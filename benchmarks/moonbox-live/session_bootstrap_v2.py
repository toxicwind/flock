#!/usr/bin/env python3
"""session_bootstrap_v2.py - Load working autohook_v9."""
import sys, os
sys.path.insert(0, "/mnt/agents/output")

# Purge any broken autohook from memory
if "subprocess" in sys.modules:
    del sys.modules["subprocess"]
import subprocess

# Load clean autohook v9
try:
    import autohook_v9
    print("§AUTOHOOK_V9_ACTIVE§")
except Exception as e:
    print(f"§AUTOHOOK_FAIL§ {e}")

# Load Morphe graft
try:
    sys.path.insert(0, "/mnt/agents/output/morphe-autohook-core")
    from morphe.kernel import MorpheIPythonPatcher
    MorpheIPythonPatcher.install()
except Exception as e:
    print(f"§MORPHE_FAIL§ {e}")

print("§BOOTSTRAP_DONE§")
