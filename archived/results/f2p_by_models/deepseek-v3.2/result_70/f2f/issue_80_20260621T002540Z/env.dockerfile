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

# Install pnpm globally (since CI workflow uses it)
RUN npm install -g pnpm

# Check project structure and install dependencies
RUN if [ -f "package.json" ]; then \
        pnpm install --include=dev; \
    elif [ -f "ui/package.json" ]; then \
        cd ui && pnpm install --include=dev; \
    else \
        echo "No package.json found" && exit 1; \
    fi

# Install the project in editable mode (for JavaScript, this is done via pnpm install above)
# Run preflight check
RUN node -e "console.log('preflight ok')"

# Set default command to run tests
CMD ["/bin/bash"]