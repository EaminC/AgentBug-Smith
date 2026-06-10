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

COPY . .

# Install dependencies and build with workspace awareness and safe conditionals
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm@latest && \
      pnpm install --frozen-lockfile --recursive && \
      pnpm run build && \
      pnpm install --save-dev jest @types/jest ts-jest typescript; \
    elif [ -f "package-lock.json" ]; then \
      npm ci && \
      npm run build && \
      npm install --save-dev jest @types/jest ts-jest typescript; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && \
      yarn install --frozen-lockfile && \
      yarn build && \
      yarn add --dev jest @types/jest ts-jest typescript; \
    else \
      npm install && \
      npm run build && \
      npm install --save-dev jest @types/jest ts-jest typescript; \
    fi

# Verify jest installation and version
RUN npx jest --version || npm run test -- --version || true

# Set NODE_PATH for module resolution in monorepos/workspaces
ENV NODE_PATH=/app/node_modules

# Re-set environment variables for runtime consistency
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

CMD ["/bin/bash"]