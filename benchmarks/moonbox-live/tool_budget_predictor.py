#!/usr/bin/env python3
"""
Tool Budget Predictor v1
Predicts when tool budget will reset based on observed patterns.
"""
import json, os, time, subprocess

LOG_FILE = "/mnt/agents/output/budget_log.json"

def log_budget_event(event_type, details=None):
    entry = {
        "timestamp": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "event": event_type,
        "details": details or {},
        "pid": os.getpid(),
    }
    try:
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except:
        pass

def predict_reset():
    """Predict next budget reset based on historical data."""
    try:
        with open(LOG_FILE) as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except:
        entries = []
    
    if len(entries) < 2:
        return {"confidence": "low", "prediction": "unknown", "reason": "insufficient data"}
    
    # Find gaps between turns (when budget resets)
    resets = []
    for i in range(1, len(entries)):
        if entries[i]["event"] == "turn_start" and entries[i-1]["event"] == "turn_end":
            gap = entries[i]["timestamp"] - entries[i-1]["timestamp"]
            resets.append(gap)
    
    if not resets:
        return {"confidence": "low", "prediction": "unknown", "reason": "no reset pattern found"}
    
    avg_gap = sum(resets) / len(resets)
    min_gap = min(resets)
    max_gap = max(resets)
    
    # Predict next reset
    last_end = entries[-1]["timestamp"] if entries[-1]["event"] == "turn_end" else time.time()
    predicted = last_end + avg_gap
    
    return {
        "confidence": "medium" if len(resets) >= 3 else "low",
        "predicted_reset": predicted,
        "predicted_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(predicted)),
        "avg_gap_min": avg_gap / 60,
        "min_gap_min": min_gap / 60,
        "max_gap_min": max_gap / 60,
        "sample_size": len(resets),
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "predict":
        print(json.dumps(predict_reset(), indent=2))
    else:
        log_budget_event("turn_start", {"args": sys.argv[1:]})
        print(f"Logged turn_start at {time.strftime('%H:%M:%S')}")
