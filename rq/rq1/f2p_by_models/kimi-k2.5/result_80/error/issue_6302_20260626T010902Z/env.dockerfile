FROM node:20-alpine

WORKDIR /app

# Copy package configuration files
COPY package*.json ./
COPY tsconfig.json ./

# Safe dependency installation
RUN if [ -f package.json ]; then npm install; fi

# Editable installation of local package
RUN if [ -f package.json ]; then npm link; fi

# Copy source code and tests
COPY . .

# Build TypeScript if configuration exists
RUN if [ -f tsconfig.json ]; then npm run build; fi

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi-kimi-k2.5/kimi-k2.5"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Default command to run tests
CMD ["npm", "test"]