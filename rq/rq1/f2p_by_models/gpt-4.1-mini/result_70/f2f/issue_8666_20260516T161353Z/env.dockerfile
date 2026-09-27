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

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility (avoid duplicates)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Copy entire repository into the container
COPY . .

# Install dependencies based on detected JS package manager lockfile
RUN if [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && yarn install; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install; \
    elif [ -f "package.json" ]; then \
      npm install; \
    else \
      echo "No recognized JS package manager lockfile found, skipping install."; \
    fi

# Install standard JS test frameworks unconditionally (jest and mocha)
RUN npm install --no-save jest mocha

# Set default command to bash
CMD ["/bin/bash"]