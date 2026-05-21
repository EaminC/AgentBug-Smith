# Use official lightweight Node.js base image
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

# Set environment variables for Forge API (OpenAI-compatible) and Anthropic SDK
ENV FORGE_API_KEY=forge-key \
    OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Set working directory
WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Install dependencies based on the detected package manager lockfile
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && yarn install --frozen-lockfile; \
    else \
      npm install; \
    fi

# Install standard JavaScript test frameworks if not present
RUN if [ -f "pnpm-lock.yaml" ]; then \
      pnpm add -Dw jest mocha chai @types/jest @types/mocha ts-node --workspace-root --ignore-workspace-root-check true; \
    else \
      npm install --save-dev jest mocha chai @types/jest @types/mocha ts-node; \
    fi

# Install local package in editable mode (npm link style)
RUN npm link || true

# Verify jest availability
RUN node -e "require('jest'); console.log('preflight ok');"

# Final start command must be bash for test harness compatibility
CMD ["/bin/bash"]