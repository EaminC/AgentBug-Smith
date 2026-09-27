# Use official Node.js 20 slim base image for JavaScript project
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

# Set working directory to repository root
WORKDIR /app

# Set environment variables for Forge API replacing OpenAI and Anthropic endpoints
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Also set project-specific vars that might be used by the app
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"

# Copy the entire project into the container
COPY . .

# Install dependencies based on lockfile detection and ensure common test tools
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      yarn install; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      pnpm install; \
    elif [ -f "package.json" ]; then \
      npm install; \
    else \
      echo "No recognized Node.js package manager lockfile found, skipping install"; \
    fi && \
    npm install --no-save jest mocha

# Preflight check: verify jest is installed and importable
RUN node -e "require('jest'); console.log('preflight ok')"

# Set default command to bash shell
CMD ["/bin/bash"]