# Use official Node.js base image for JavaScript projects
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

# Set Forge API environment variables for OpenAI and Anthropic compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set environment variable for Forge API key to be used inside container
ENV FORGE_API_KEY="forge-key"

# Set working directory to the root of the repository
WORKDIR /app

# Copy entire repository into container
COPY . .

# Install dependencies using the appropriate JavaScript package manager with robust checks
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      yarn install; \
    elif [ -f "package.json" ]; then \
      npm install; \
    else \
      echo "No recognized package manager lockfile found, skipping install"; \
    fi

# Ensure standard test dependencies jest and mocha are installed without saving to package.json
RUN npm install --no-save jest mocha || true

# Install local package in editable mode (npm link or equivalent)
# Since this is a Node.js project, npm install above covers local package installation

# Preflight check to verify jest is available
RUN node -e "require('jest'); console.log('preflight ok')" || true

# Set environment variable for test runner if needed
ENV NODE_ENV=test

# Default command to enter CLI
CMD ["/bin/bash"]

# branch: nodejs/root