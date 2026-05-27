# Use official lightweight Node.js base image for JavaScript
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

# Set environment variables for Forge API compatibility (avoid duplicates)
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

# Set working directory
WORKDIR /app

# Copy entire repository to container
COPY . .

# Install dependencies using npm (lockfile or not)
RUN if [ -f "package.json" ]; then npm install; else echo "No package.json found, skipping install"; fi

# Install standard JavaScript testing tools if not already installed (ignore errors to avoid failures if already installed)
RUN npm install --no-save jest mocha || true

# Preflight check for testing dependencies
RUN node -e "require('jest'); require('mocha'); console.log('preflight ok');" || true

# Set default command to run tests with jest
CMD ["npx", "jest", "--runInBand", "--detectOpenHandles"]