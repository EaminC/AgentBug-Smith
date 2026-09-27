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

# Set environment variables for Forge API compatibility (avoid duplicates)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory to repo root
WORKDIR /app

# Copy entire repository
COPY . .

# Install dependencies based on lockfile in repo root and build project
RUN if [ -f "package-lock.json" ]; then \
      npm ci && npm run build; \
    elif [ -f "yarn.lock" ]; then \
      yarn install --frozen-lockfile && yarn build; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install && pnpm run build; \
    elif [ -f "package.json" ]; then \
      npm install && npm run build; \
    else \
      echo "No recognized package manager lockfile found" && exit 1; \
    fi

# Verify node and npm versions
RUN node -v && npm -v

# Default shell for running container
CMD ["/bin/bash"]