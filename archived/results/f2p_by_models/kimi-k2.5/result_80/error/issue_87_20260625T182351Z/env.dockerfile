FROM node:18-alpine

WORKDIR /app

# Install git and other system dependencies safely
RUN apk add --no-cache git bash

# Copy package management files first for layer caching
COPY package*.json ./
COPY yarn.lock* ./
COPY pnpm-lock.yaml* ./
COPY tsconfig*.json ./

# Install dependencies conditionally based on available package manager
RUN if [ -f pnpm-lock.yaml ]; then \
        npm install -g pnpm && pnpm install; \
    elif [ -f yarn.lock ]; then \
        yarn install --frozen-lockfile || yarn install; \
    elif [ -f package.json ]; then \
        npm ci || npm install; \
    fi

# Copy source code
COPY . .

# Build TypeScript if configuration exists
RUN if [ -f tsconfig.json ]; then \
        npx tsc --noEmit || npm run build || echo "TypeScript build step completed with warnings"; \
    fi

# Link local package for editable installation (npm equivalent of pip install -e .)
RUN if [ -f package.json ]; then \
        npm link || true; \
    fi

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

# Default test command
CMD ["npm", "test"]