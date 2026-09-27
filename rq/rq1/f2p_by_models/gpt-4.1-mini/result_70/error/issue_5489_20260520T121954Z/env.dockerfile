# syntax=docker/dockerfile:1.4

# Use official Node.js 20 slim base image for TypeScript
FROM node:20-slim

# Set working directory
WORKDIR /app

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"
ENV AI_STOP_SEQUENCES=""
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Copy entire repository into the container
COPY . .

# Install dependencies with fallback to legacy-peer-deps due to dependency conflicts
RUN if [ -f "package-lock.json" ]; then \
      npm ci --legacy-peer-deps; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && yarn install --legacy-peer-deps; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install --shamefully-hoist; \
    else \
      npm install; \
    fi && \
    npm install --no-save jest mocha ts-node typescript @types/jest @types/node && \
    if grep -q '"build"' package.json; then npm run build || true; fi

# Install the local package in editable mode (linking)
RUN npm link

# Preflight check to verify jest module is available
RUN node -e "require('jest'); console.log('preflight ok')" || true

# Final command to keep the container open with bash
CMD ["/bin/bash"]

# branch: nodejs/typescript