#!/bin/sh
# Fast environment setup - source this at start of every session
: ${GITHUB_PAT:?"GITHUB_PAT must be exported"}
export PYTHONPATH="/mnt/agents/output/.pip:$PYTHONPATH"
export PIP_TARGET="/mnt/agents/output/.pip"
export PATH="/mnt/agents/output/.pip/bin:$PATH"
