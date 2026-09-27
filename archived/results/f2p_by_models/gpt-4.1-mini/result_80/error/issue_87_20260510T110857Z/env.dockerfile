# Use official Node.js 20 slim base image for TypeScript projects
FROM node:20-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Inject environment variables from project root .env
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
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"

# Set working directory
WORKDIR /app

# Copy the entire repository
COPY . .

# Install dependencies and build with pnpm if pnpm-lock.yaml exists
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && \
      pnpm install && \
      pnpm run build && \
      pnpm add -D -w jest ts-jest @types/jest && \
      pnpm install && \
      node -e "require('jest'); console.log('preflight ok');"; \
    elif [ -f "package-lock.json" ]; then \
      npm ci && \
      npm run build && \
      npm install --no-save jest ts-jest @types/jest && \
      node -e "require('jest'); console.log('preflight ok');"; \
    elif [ -f "yarn.lock" ]; then \
      yarn install && \
      yarn run build && \
      yarn add -D jest ts-jest @types/jest && \
      node -e "require('jest'); console.log('preflight ok');"; \
    else \
      echo "No recognized package manager lockfile found. Installing npm dependencies by default." && \
      npm install && \
      npm run build && \
      npm install --no-save jest ts-jest @types/jest && \
      node -e "require('jest'); console.log('preflight ok');"; \
    fi

# Expose optional port if services require it
EXPOSE 3141

# Default command to run interactive shell
CMD ["/bin/bash"]

# branch: Node.js TypeScript with pnpm/npm/yarn, Forge API environment variables set, ready for tests and scripts