#!/usr/bin/env bash
# grok — Stub wrapper for grok fork (when ready)

GROK_FORK="/home/toxic/projects/grok"

if [[ ! -d "$GROK_FORK" ]]; then
    echo "[grok] Fork not found at $GROK_FORK" >&2
    echo "[grok] Clone your fork: git clone <your-grok-fork> $GROK_FORK" >&2
    exit 1
fi

cd "$GROK_FORK" || exit 1
# TODO: Add grok-specific build/run logic here
exec echo "[grok] Not yet implemented. Add run logic to $0"
