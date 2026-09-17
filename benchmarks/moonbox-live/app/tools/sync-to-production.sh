#!/bin/bash
set -euo pipefail

# CHRONOS FORGE :: Sync to Production
# Orchestrator script: Generates artifacts (if missing), uploads them, and triggers Portainer.

echo "🚀 Syncing to Production..."

# 1. Generate Artifacts if needed
if [ ! -f "artifacts/LATEST_BUNDLE" ]; then
    echo "⚙️  Generating artifacts..."
    ./tools/generate-artifacts.sh
else
    echo "ℹ️  Using existing artifacts (run generate-artifacts.sh to refresh)"
fi

# 2. Upload Artifacts
echo "u001b[34m📤 Uploading artifacts...\u001b[0m"
./tools/upload-artifacts.sh

# 3. Trigger Portainer
if [[ -n "${PORTAINER_WEBHOOK:-}" ]]; then
  echo "u001b[35m🔄 Triggering Portainer redeploy...\u001b[0m"
  curl --fail --retry 3 --retry-delay 2 -X POST "$PORTAINER_WEBHOOK"
  echo "✅ Portainer redeploy triggered"
else
  echo "⚠️  PORTAINER_WEBHOOK not set. Skipping trigger."
fi

echo "🎉 Sync flow complete."
