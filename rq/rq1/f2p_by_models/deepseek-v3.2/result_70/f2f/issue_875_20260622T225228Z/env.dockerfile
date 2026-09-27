FROM node:20-slim AS test_builder

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-YzQxc4137fbc8de99e8b65e6b349a8f3d6"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-YzQxc4137fbc8de99e8b65e6b349a8f3d6"
ENV ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-YzQxc4137fbc8de99e8b65e6b349a8f3d6"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy entire repository
COPY . .

# Install project dependencies
RUN if [ -f package.json ]; then \
        npm install; \
        # Install dev dependencies if they exist
        if [ -f package.json ] && grep -q '"devDependencies"' package.json; then \
            npm install --only=dev; \
        fi; \
    fi

# Install globally if needed for testing
RUN if [ -f package.json ] && grep -q '"bin"' package.json; then \
        npm install -g .; \
    fi

# Check if TypeScript needs compilation
RUN if [ -f tsconfig.json ]; then \
        npm run build || true; \
    fi

CMD ["/bin/bash"]