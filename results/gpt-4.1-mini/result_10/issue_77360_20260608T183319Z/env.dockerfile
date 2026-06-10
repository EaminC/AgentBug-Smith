# Use a named build stage for building dependencies and compiling
FROM node:20-slim AS build

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
ENV HF_TOKEN="hf_key"
# --- end inject ---

WORKDIR /app

COPY . .

# Enable corepack for pnpm
RUN corepack enable

# Install dependencies using pnpm if lockfile exists, else skip
RUN if [ -f "pnpm-lock.yaml" ]; then \
      pnpm install --frozen-lockfile && \
      pnpm run build && \
      # Install dev dependencies for testing framework (Vitest/Jest/Mocha detection)
      if grep -q vitest package.json 2>/dev/null; then \
        pnpm add -D vitest tsx; \
      elif grep -q jest package.json 2>/dev/null; then \
        pnpm add -D jest ts-jest @types/jest; \
      elif grep -q mocha package.json 2>/dev/null; then \
        pnpm add -D mocha @types/mocha chai @types/chai; \
      else \
        pnpm add -D vitest tsx; \
      fi; \
    else \
      echo "No pnpm-lock.yaml found, skipping install and build"; \
    fi

RUN node -e "console.log('preflight ok')"

# Set environment variables for API keys and URLs (ensure consistent)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Runtime stage
FROM node:24-bookworm-slim@sha256:e8e2e91b1378f83c5b2dd15f0247f34110e2fe895f6ca7719dbb780f929368eb AS runtime

WORKDIR /app

# Copy built app and node_modules from build stage
COPY --from=build /app .

# Install runtime dependencies and utilities
RUN apt-get update && apt-get install -y ca-certificates tini procps hostname curl git lsof openssl python3 && update-ca-certificates

# Fix permissions for node user
RUN chown -R node:node /app

# Enable corepack and prepare package manager as per package.json
ENV COREPACK_HOME=/usr/local/share/corepack
RUN install -d -m 0755 "$COREPACK_HOME" && corepack enable && \
    for attempt in 1 2 3 4 5; do \
      if corepack prepare "$(node -p "require('./package.json').packageManager")" --activate; then break; fi; \
      if [ "$attempt" -eq 5 ]; then exit 1; fi; \
      sleep $((attempt * 2)); \
    done && chmod -R a+rX "$COREPACK_HOME"

# Prune dev dependencies in production if lockfile exists
RUN if [ -f "pnpm-lock.yaml" ]; then \
      pnpm prune --prod; \
    fi

# Symlink openclaw.mjs to /usr/local/bin/openclaw and set executable
RUN ln -sf /app/openclaw.mjs /usr/local/bin/openclaw && chmod 755 /app/openclaw.mjs

ENV NODE_ENV=production

# Set NODE_PATH for module resolution in monorepo/workspace setups
ENV NODE_PATH=/app/node_modules

USER node

ENTRYPOINT ["tini", "-s", "--"]
CMD ["node", "dist/index.js", "gateway", "--bind", "${OPENCLAW_GATEWAY_BIND:-lan}", "--port", "18789"]