#!/usr/bin/env python3
"""Persistent chat system using kernel execute API instead of WezTerm."""
import urllib.request, json, time, os

CHAT_FILE = "/mnt/agents/output/AGENT_CHAT.jsonl"

def send(agent, msg):
    entry = {"t": time.time(), "agent": agent, "msg": msg}
    with open(CHAT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def read():
    if not os.path.exists(CHAT_FILE):
        return []
    with open(CHAT_FILE) as f:
        return [json.loads(l) for l in f if l.strip()]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        send(sys.argv[1], sys.argv[2])
    else:
        for entry in read()[-10:]:
            print(f"[{entry['t']:.0f}] {entry['agent']}: {entry['msg']}")
