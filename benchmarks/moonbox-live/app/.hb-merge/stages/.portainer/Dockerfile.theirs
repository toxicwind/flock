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
