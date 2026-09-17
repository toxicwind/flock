<<<<<<< HEAD
# syntax=docker/dockerfile:1.7

############################
# deps layer (heavy caching)
############################
FROM node:24-bookworm AS deps
WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential python3 ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

ENV npm_config_fund=false \
    npm_config_audit=false \
    npm_config_proxy= \
    npm_config_https_proxy= \
    npm_config_http_proxy= \
    http_proxy= \
    https_proxy= \
    PUPPETEER_SKIP_DOWNLOAD=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY package*.json ./
COPY patches/ ./patches/
# postinstall needs the patch runner available during dependency install
COPY tools/apply-patches.mjs ./tools/apply-patches.mjs
COPY tools/resolve-chromium.mjs ./tools/resolve-chromium.mjs
COPY bin/install-chromium.sh ./bin/install-chromium.sh
RUN npm ci --no-audit --no-fund
RUN chmod +x bin/install-chromium.sh && \
    mkdir -p /usr/local/bin && \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0 ./bin/install-chromium.sh >/tmp/chromium-path && \
    CHROMIUM_PATH="$(tail -n1 /tmp/chromium-path)" && \
    ln -sf "$CHROMIUM_PATH" /usr/local/bin/chromium && \
    ln -sf "$CHROMIUM_PATH" /usr/local/bin/chromium-browser

############################
# build layer (production)
############################
FROM deps AS builder
WORKDIR /app

ARG COMMIT_SHA=unknown
ENV COMMIT_SHA=${COMMIT_SHA}

ENV NODE_ENV=production \
    ELEVENTY_ENV=production \
    npm_config_proxy= \
    npm_config_https_proxy= \
    npm_config_http_proxy= \
    http_proxy= \
    https_proxy= \
    PUPPETEER_SKIP_DOWNLOAD=1 \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=1 \
    PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chromium \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
COPY package*.json ./
COPY tools ./tools
COPY bin ./bin
COPY . .

# Download pre-generated artifacts (if available)
RUN mkdir -p /tmp/artifacts && \
    curl -L "https://github.com/toxicwind/effusion_labs_final/releases/latest/download/lv-bundle.tar.gz" \
    -o /tmp/lv-bundle.tar.gz 2>/dev/null || echo "No artifacts found, using baked" && \
    if [ -f /tmp/lv-bundle.tar.gz ]; then \
    mkdir -p src/content/projects/lv-images/generated && \
    tar -xzf /tmp/lv-bundle.tar.gz -C src/content/projects/lv-images/generated/ 2>/dev/null || true; \
    fi

RUN node tools/check-chromium.mjs && \
    npm run tools:check-patches && \
    NODE_OPTIONS='--max-old-space-size=8192' npm run build:offline && \
    npx vite build

############################
# runtime (tiny, static)
############################
FROM nginx:1.29-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/_site/ /usr/share/nginx/html/
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD curl --fail --silent --show-error http://127.0.0.1/ >/dev/null 2>&1 || exit 1
=======
# ─── Build stage ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Log: node version and env context
RUN node -v && npm -v && echo "🐳 STARTING ELEVENTY BUILD CONTEXT"

# Install deps
COPY package*.json ./
RUN npm ci

# Copy project files
COPY . .

# Run Eleventy build (with Tailwind plugin)
RUN echo "⚙️ Building site with Eleventy..." \
 && npx @11ty/eleventy

# ─── Runtime stage ─────────────────────────────────────────────────────────────
FROM nginx:stable-alpine

COPY --from=builder /app/_site/ /usr/share/nginx/html/
COPY .portainer/nginx.conf /etc/nginx/conf.d/default.conf
>>>>>>> broken/codex/add-dark-mode-as-default-with-light-mode-option
