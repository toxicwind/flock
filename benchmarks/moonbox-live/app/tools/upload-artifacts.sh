#!/bin/bash
set -euo pipefail

# CHRONOS FORGE :: Artifact Uploader
# Uploads the bundle pointed to by artifacts/LATEST_BUNDLE to GitHub Releases.
# Tag: artifacts-latest (Floating tag strategy)

LOG_TAG="[artifact-upload]"
REPO="toxicwind/effusion_labs_final"
TAG="artifacts-latest"

log() {
    echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") ${LOG_TAG} $1"
}

# Ensure we're in repo root
cd "$(git rev-parse --show-toplevel)"

if [ ! -f "artifacts/LATEST_BUNDLE" ]; then
    log "ERROR: artifacts/LATEST_BUNDLE marker not found. Run tools/generate-artifacts.sh first."
    exit 1
fi

BUNDLE_PATH=$(cat artifacts/LATEST_BUNDLE)
if [ ! -f "$BUNDLE_PATH" ]; then
    log "ERROR: Bundle file $BUNDLE_PATH does not exist."
    exit 1
fi

BUNDLE_NAME=$(basename "$BUNDLE_PATH")

if [ -z "${GITHUB_TOKEN:-}" ]; then
    log "ERROR: GITHUB_TOKEN is not set."
    exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
    log "ERROR: gh CLI not found."
    exit 1
fi

log "Targeting repository: ${REPO}"
log "Uploading ${BUNDLE_NAME} to release tag: ${TAG}"

# Ensure release exists
if ! gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    log "Release ${TAG} not found. Creating it..."
    gh release create "$TAG" --repo "$REPO" --title "Artifacts Bundle (Latest)" --notes "Automated artifact bundle." --prerelease || true
fi

# Upload asset (clobber existing)
log "Uploading asset..."
gh release upload "$TAG" "$BUNDLE_PATH" --repo "$REPO" --clobber

# Also upload SHA256 if present
if [ -f "${BUNDLE_PATH}.sha256" ]; then
    log "Uploading checksum..."
    gh release upload "$TAG" "${BUNDLE_PATH}.sha256" --repo "$REPO" --clobber
fi

log "Upload complete: https://github.com/${REPO}/releases/tag/${TAG}"
