# syntax=docker/dockerfile:1.7
FROM node:20-slim

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
ENV TAVILY_API_KEY="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"
ENV GITHUB_TOKEN="ghp_key"
ENV HF_TOKEN="hf_key"
# --- end inject ---

WORKDIR /app

# Copy the entire repository into the container
COPY . .

# Set Forge environment variables as required
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# Install root dependencies with workspace support if applicable
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      yarn install --frozen-lockfile; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      pnpm install --frozen-lockfile --recursive; \
    else \
      echo "No lockfile found; running npm install"; \
      npm install; \
    fi

# Build the entire project (including workspaces/packages)
RUN npm run build || echo "No build script found or build failed"

# Install dependencies and build the skills package if present
RUN if [ -f "skills/package-lock.json" ]; then \
      npm ci --prefix skills && \
      npm run build --prefix skills; \
    elif [ -f "skills/package.json" ]; then \
      npm install --prefix skills && \
      npm run build --prefix skills; \
    else \
      echo "No package.json found in skills directory; skipping npm install and build"; \
    fi

# Install testing dependencies: Jest and TypeScript if tsconfig.json exists in skills
RUN if [ -f "skills/tsconfig.json" ]; then \
      npm install --prefix skills --no-save jest ts-jest @types/jest typescript; \
    else \
      npm install --prefix skills --no-save jest @types/jest; \
    fi

# Preflight check: verify that core modules and test framework are importable
RUN node -e "require('jest'); require('typescript'); console.log('preflight ok')"

# Set NODE_PATH to support workspace module resolution
ENV NODE_PATH=/app/node_modules

# Set the working directory to the standard location
WORKDIR /app

# Final command to keep the container open for test harness
CMD ["/bin/bash"]