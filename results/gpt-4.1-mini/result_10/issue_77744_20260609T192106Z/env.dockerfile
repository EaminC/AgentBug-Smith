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

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

COPY . .

# Install root workspace dependencies (handles monorepo workspaces)
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      yarn install --frozen-lockfile; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      pnpm install --frozen-lockfile --recursive; \
    else \
      echo "Warning: no lockfile found in root"; \
    fi

# Build all TypeScript packages (monorepo aware)
RUN if [ -f "package.json" ] && grep -q "\"build\"" package.json; then \
      npm run build; \
    else \
      echo "Warning: no build script found in root package.json"; \
    fi

# Install and build skills package if exists
RUN if [ -d "skills" ]; then \
      if [ -f "skills/package-lock.json" ]; then \
        npm ci --prefix skills && npm run build --prefix skills; \
      elif [ -f "skills/package.json" ]; then \
        npm install --prefix skills && npm run build --prefix skills; \
      else \
        echo "Warning: no package.json found in skills/ directory"; \
      fi; \
    fi

# Install testing dependencies in skills if skills exists
RUN if [ -d "skills" ]; then \
      if [ -f "skills/tsconfig.json" ]; then \
        npm install --prefix skills --no-save jest ts-jest @types/jest typescript; \
      else \
        npm install --prefix skills --no-save jest; \
      fi; \
    fi

# Preflight: test that core modules can be imported
RUN node -e "import('jest'); import('typescript'); console.log('preflight ok')"

# Set NODE_PATH for monorepo module resolution
ENV NODE_PATH=/app/node_modules

CMD ["/bin/bash"]