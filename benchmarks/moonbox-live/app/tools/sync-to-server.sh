#!/bin/bash
set -euo pipefail

# Dedicated Server Artifact Sync
# Syncs locally-generated artifacts to dedicated server for Portainer deployment

echo "🚀 Syncing artifacts to dedicated server..."

# Configuration (set these via environment or .env)
SERVER_HOST="${DEPLOY_SERVER_HOST:-your-server.com}"
SERVER_USER="${DEPLOY_SERVER_USER:-deploy}"
SERVER_PATH="${DEPLOY_SERVER_PATH:-/opt/effusion-artifacts}"
SSH_KEY="${DEPLOY_SSH_KEY:-$HOME/.ssh/id_rsa}"

# Check if artifacts exist
if [ ! -d "src/content/projects/lv-images/generated" ]; then
  echo "❌ No artifacts found. Run ./tools/generate-artifacts.sh first"
  exit 1
fi

# 1. Sync artifacts via rsync
echo "📤 Syncing to ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}..."

rsync -avz --delete \
  -e "ssh -i ${SSH_KEY}" \
  src/content/projects/lv-images/generated/ \
  "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/lv-images/"

echo "✅ Artifacts synced successfully"

# 2. Trigger Portainer stack update (optional)
if [[ -n "${PORTAINER_WEBHOOK:-}" ]]; then
  echo "🔄 Triggering Portainer redeploy..."
  curl --fail --retry 3 --retry-delay 2 -X POST "$PORTAINER_WEBHOOK"
  echo "✅ Portainer redeploy triggered"
else
  echo "⚠️  PORTAINER_WEBHOOK not set"
  echo ""
  echo "Manual redeploy steps:"
  echo "1. SSH to server: ssh ${SERVER_USER}@${SERVER_HOST}"
  echo "2. Navigate to stack: cd /opt/effusion-labs"
  echo "3. Restart stack: docker-compose up -d --force-recreate"
fi

echo ""
echo "🎉 Sync complete!"
echo "Artifacts available at: ${SERVER_HOST}:${SERVER_PATH}/lv-images/"
