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

# Copy entire repository
COPY . .

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js dependencies
# Check for package.json and install dependencies
RUN if [ -f package.json ]; then npm install; fi

# Check for additional package managers
RUN if [ -f yarn.lock ]; then yarn install; fi
RUN if [ -f pnpm-lock.yaml ]; then npm install -g pnpm && pnpm install; fi

# Install project in development mode if it's a monorepo
# Check for common monorepo structures
RUN if [ -f lerna.json ]; then npx lerna bootstrap; fi
RUN if [ -f packages ] && [ -d packages ]; then npm install -g lerna && lerna bootstrap; fi

# Install testing dependencies if not already included
RUN if [ -f package.json ]; then npm install --save-dev jest mocha chai sinon @types/node typescript ts-node; fi

# Preflight check for Node.js environment
RUN node -e "console.log('Node.js environment ready')"

CMD ["/bin/bash"]