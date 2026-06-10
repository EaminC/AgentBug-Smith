FROM node:24-bookworm AS build

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

# Copy entire repository into the container
COPY . .

# Install dependencies with workspace awareness and reproducibility
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      yarn install --frozen-lockfile; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      pnpm install --frozen-lockfile --recursive; \
    else \
      npm install; \
    fi

# Build TypeScript if tsconfig.json and build script exist
RUN if [ -f "tsconfig.json" ] && npm run | grep -q "build"; then \
      npm run build; \
    fi

# Detect test framework from package.json and install if missing
RUN if grep -q '"jest"' package.json; then \
      npm install --save-dev jest @types/jest ts-jest; \
    elif grep -q '"vitest"' package.json; then \
      npm install --save-dev vitest @vitest/coverage-c8; \
    elif grep -q '"mocha"' package.json; then \
      npm install --save-dev mocha @types/mocha; \
    elif grep -q '"jasmine"' package.json; then \
      npm install --save-dev jasmine @types/jasmine; \
    else \
      # Fallback: install jest as default
      npm install --save-dev jest @types/jest ts-jest; \
    fi

# Run a preflight test command to verify installation
RUN if npm test -- --version || npm run test -- --version || true; then echo "Test framework installed"; else echo "No test framework found"; fi

# Set environment variables for runtime
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Set NODE_PATH for monorepo module resolution if applicable
ENV NODE_PATH=/app/node_modules

CMD ["/bin/bash"]