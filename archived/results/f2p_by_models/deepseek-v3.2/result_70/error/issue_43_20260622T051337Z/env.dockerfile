FROM node:20-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies for building packages and running the project
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire repository
COPY . .

# Install Node.js dependencies
RUN if [ -f package-lock.json ]; then \
        npm ci; \
    elif [ -f yarn.lock ]; then \
        npm install -g yarn && yarn install --frozen-lockfile; \
    elif [ -f pnpm-lock.yaml ]; then \
        npm install -g pnpm && pnpm install --frozen-lockfile; \
    else \
        npm install; \
    fi

# Install the project in development mode if it's a workspace or monorepo
RUN if [ -f package.json ] && grep -q '"workspaces"' package.json; then \
        npm run install:all || npm run bootstrap || true; \
    fi

# Install testing dependencies if they exist in package.json
RUN if [ -f package.json ] && grep -q '"devDependencies"' package.json; then \
        npm install; \
    fi

# Set the default command to bash for the test harness
CMD ["/bin/bash"]