# Artifact Sync Workflows

## Overview

Two workflows for syncing locally-generated artifacts to production:

1. **GitHub Releases** (default) - For GitHub Actions CI/CD
2. **Direct Server Sync** (dedicated server) - For Portainer on dedicated hardware

---

## Workflow 1: GitHub Releases (CI/CD)

**Use when**: Deploying via GitHub Actions to any container platform

```bash
# 1. Generate artifacts locally
./tools/generate-artifacts.sh

# 2. Upload to GitHub Releases
./tools/sync-to-production.sh

# 3. GitHub Actions automatically:
#    - Downloads artifacts from release
#    - Builds Docker image
#    - Pushes to GHCR
#    - Triggers Portainer webhook
```

**Dockerfile** automatically downloads from latest release during build.

---

## Workflow 2: Direct Server Sync (Recommended for Dedicated Server)

**Use when**: Portainer running on dedicated server with filesystem access

### Setup (One-time)

```bash
# 1. On dedicated server, create artifact directory
ssh user@your-server.com
sudo mkdir -p /opt/effusion-artifacts/lv-images
sudo chown $USER:$USER /opt/effusion-artifacts

# 2. On local machine, configure deployment
cp .env.deploy.example .env.deploy
# Edit .env.deploy with your server details

# 3. Test SSH connection
ssh -i ~/.ssh/id_rsa user@your-server.com "echo 'Connection OK'"
```

### Daily Workflow

```bash
# 1. Generate artifacts locally (expensive operation)
./tools/generate-artifacts.sh

# 2. Sync to dedicated server
source .env.deploy
./tools/sync-to-server.sh

# 3. Portainer automatically uses new artifacts via volume bind
```

### docker-compose.yml Configuration

```yaml
services:
  effusion-labs:
    volumes:
      # Bind mount from server filesystem
      - /opt/effusion-artifacts/lv-images:/usr/share/nginx/html/content/projects/lv-images/generated:ro
```

**Benefits**:

- No Docker rebuild required
- Instant artifact updates
- No GitHub storage limits
- Direct rsync (faster than release upload)

---

## Comparison

| Feature | GitHub Releases | Direct Server Sync |
|---------|----------------|-------------------|
| Speed | Slower (upload + build) | Faster (rsync only) |
| Rebuild | Required | Not required |
| Storage | 2GB limit per file | Unlimited |
| Best for | CI/CD pipelines | Dedicated servers |

---

## Quick Reference

```bash
# Generate artifacts
./tools/generate-artifacts.sh

# Sync to GitHub (CI/CD)
./tools/sync-to-production.sh

# Sync to dedicated server
source .env.deploy && ./tools/sync-to-server.sh
```
