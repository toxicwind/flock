#!/bin/bash
set -euo pipefail

# CHRONOS FORGE :: Artifact Generator
# Bundles site output and lv-images data into a versioned artifact.
# Generates checksums and manifest.

echo "🎨 Generating artifacts locally..."

# Configuration
ARTIFACT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
ARTIFACT_ID="bundle-$(date +%Y%m%d-%H%M%S)"
TARGET_DIR="artifacts/${ARTIFACT_ID}"
BUNDLE_NAME="lv-bundle.tar.gz" # Fixed name inside the folder, but folder is versioned
MANIFEST_FILE="${TARGET_DIR}/manifest.json"

# 1. Clean & Prepare
mkdir -p "$TARGET_DIR"

# 2. Run Generation (Expensive)
# Check if build:offline needs to run or if we assume it's done
# For strictness, we run it here or warn. CHRONOS-FORGE says "runs expensive generative tasks locally"
echo "📸 Checking pre-requisites..."
if [ ! -d "src/content/projects/lv-images/generated" ]; then
  echo "⚠️  No generated images found. Running crawl..."
  bun run crawl:pages
fi

echo "🏗️  Ensuring site build..."
# We assume 'bun run build:site' or 'build:offline' has run.
# But let's run a safe build to be sure we have _site
if [ ! -d "_site" ]; then
    bun run build:offline
fi

# 3. Assemble Artifacts
echo "📦 Assembling bundle..."
mkdir -p "$TARGET_DIR/content"
cp -r src/content/projects/lv-images/generated "$TARGET_DIR/content/"

mkdir -p "$TARGET_DIR/site"
# Copy critical site assets if needed, but primarily we want the whole _site for deployment?
# Usually we want the *whole* _site for hosting.
cp -r _site/* "$TARGET_DIR/site/"

# 4. Generate Manifest
GIT_SHA=$(git rev-parse HEAD)
echo "📝 Generating manifest..."

cat > "$MANIFEST_FILE" <<EOF
{
  "id": "$ARTIFACT_ID",
  "timestamp": "$ARTIFACT_DATE",
  "git_sha": "$GIT_SHA",
  "contents": [
    "content/generated",
    "site"
  ]
}
EOF

# 5. Create Tarball
echo "🗜️  Compressing..."
# Create a single tarball OF the target dir content, placed in artifacts/
# We name it with ID to be unique
FINAL_BUNDLE="artifacts/${ARTIFACT_ID}.tar.gz"
tar -czf "$FINAL_BUNDLE" -C "$TARGET_DIR" .

# 6. Checksums
echo "checksum: $(sha256sum "$FINAL_BUNDLE" | cut -d' ' -f1)" >> "${FINAL_BUNDLE}.sha256"

# 7. Update Markers
echo "$FINAL_BUNDLE" > artifacts/LATEST_BUNDLE
echo "$ARTIFACT_ID" > artifacts/LATEST_ID

# Cleanup expanded dir
rm -rf "$TARGET_DIR"

echo "✅ Artifact Generated: $FINAL_BUNDLE"
echo "👉 Marked as LATEST_BUNDLE"
