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

# Copy entire repository contents
COPY . .

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Install dependencies in root if package.json exists
RUN if [ -f "package.json" ]; then \
      if [ -f "package-lock.json" ]; then \
        npm ci; \
      elif [ -f "yarn.lock" ]; then \
        yarn install; \
      else \
        npm install; \
      fi; \
    fi

# Install dependencies in src/frontend if package.json exists
RUN if [ -f "src/frontend/package.json" ]; then \
      cd src/frontend && \
      if [ -f "package-lock.json" ]; then \
        npm ci; \
      elif [ -f "yarn.lock" ]; then \
        yarn install; \
      else \
        npm install; \
      fi; \
    fi

# Install dependencies in scripts/aws if package.json exists
RUN if [ -f "scripts/aws/package.json" ]; then \
      cd scripts/aws && \
      if [ -f "package-lock.json" ]; then \
        npm ci; \
      elif [ -f "yarn.lock" ]; then \
        yarn install; \
      else \
        npm install; \
      fi; \
    fi

# Install standard test tooling explicitly
RUN npm install --no-save jest mocha chai || true

# Install local project in editable mode (npm link)
RUN npm link || true

# Preflight test for Node.js environment
RUN node -e "require('jest'); console.log('preflight ok')" || true

# Default command: open a bash shell
CMD ["/bin/bash"]

# branch: JavaScript project with Forge API env vars and conditional dependency installs