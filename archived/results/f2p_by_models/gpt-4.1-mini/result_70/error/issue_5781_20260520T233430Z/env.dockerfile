FROM node:20-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Deduplicate environment variables (already set above)
# ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# ENV OPENAI_API_KEY="forge-key"
# ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
# ENV ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

COPY . .

# Install dependencies based on lockfile presence
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install; \
    elif [ -f "package-lock.json" ]; then \
      npm install --legacy-peer-deps; \
    elif [ -f "yarn.lock" ]; then \
      yarn install; \
    elif [ -f "package.json" ]; then \
      npm install --legacy-peer-deps; \
    else \
      echo "No recognized package manager lockfile found, skipping install."; \
    fi

# Build if build script exists
RUN if npm run | grep -q 'build'; then npm run build || true; fi

# Install test dependencies explicitly (no-save)
RUN npm install --no-save ts-node typescript jest @types/jest @types/node || true

# Install local package in editable mode (npm link style)
RUN npm install .

# Verify jest installation and preflight
RUN node -e "require('jest'); console.log('preflight ok')"

# Set default command to bash shell
CMD ["/bin/bash"]