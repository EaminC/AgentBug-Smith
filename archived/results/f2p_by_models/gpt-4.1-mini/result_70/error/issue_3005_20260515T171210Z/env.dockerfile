FROM node:20-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for Forge API compatibility (ensure consistency)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory
WORKDIR /app

# Copy entire repository
COPY . .

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl bash \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js dependencies with lockfile detection and build
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && \
      pnpm install && \
      pnpm run build; \
    elif [ -f "package-lock.json" ]; then \
      npm ci && \
      npm run build; \
    else \
      npm install && \
      npm run build; \
    fi

# Install standard testing tools for JavaScript without saving to package.json
RUN if [ -f "pnpm-lock.yaml" ]; then \
      pnpm add --no-save jest mocha @types/jest ts-node typescript @types/node; \
    else \
      npm install --no-save jest mocha @types/jest ts-node typescript @types/node; \
    fi

# Preflight to check Node.js and Jest installation
RUN node -e "require('jest'); console.log('preflight ok')"

# Set default command to bash
CMD ["/bin/bash"]