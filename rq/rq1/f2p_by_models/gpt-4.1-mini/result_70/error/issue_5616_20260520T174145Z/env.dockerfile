# Use official Node.js 20 slim image for TypeScript
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

# Set Forge API environment variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1 \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Working directory inside container
WORKDIR /app

# Copy entire repository into the container
COPY . .

# Install dependencies based on lock files with fallback handling and resolve dependency conflicts
RUN if [ -f "package-lock.json" ]; then \
      npm install --legacy-peer-deps; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && yarn install; \
    elif [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install; \
    else \
      npm install --legacy-peer-deps; \
    fi

# Build the project
RUN npm run build

# Install test dependencies explicitly (no --save)
RUN npm install --no-save jest @types/jest @types/node

# Preflight check to verify test tooling availability
RUN node -e "require('jest'); console.log('preflight ok')"

# Default command to run jest tests
CMD ["npx", "jest", "--runInBand", "--detectOpenHandles"]