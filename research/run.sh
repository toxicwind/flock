#!/bin/bash
set -e
export NVIDIA_API_KEY="${NVIDIA_API_KEY:-$(grep NVIDIA_API_KEY .env.keys 2>/dev/null | cut -d= -f2)}"
if [ -z "$NVIDIA_API_KEY" ]; then echo "[ERROR] Set NVIDIA_API_KEY"; exit 1; fi

MODE="${1:-single}"
case "$MODE" in
  single) cd cmd/benchmark && go run . -effort max -max-tokens 16384 ;;
  discover) cd cmd/benchmark && go run . -discover ;;
  benchmark) cd cmd/benchmark && go run . -benchmark ;;
  nuclei) nuclei -t templates/inkling-api-test.yaml -u https://integrate.api.nvidia.com/v1 -j -o results/nuclei.jsonl ;;
  *) echo "Usage: $0 [single|discover|benchmark|nuclei]" ;;
esac
