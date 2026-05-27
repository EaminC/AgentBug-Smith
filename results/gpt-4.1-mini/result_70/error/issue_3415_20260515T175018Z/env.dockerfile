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

# Set environment variables for Forge API OpenAI and Anthropic compatibility
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"

WORKDIR /app

# Copy the entire repository
COPY . .

# Install dependencies using pnpm if pnpm-lock.yaml exists, fallback to npm install
RUN if [ -f "pnpm-lock.yaml" ]; then \
      npm install -g pnpm && pnpm install --frozen-lockfile; \
    elif [ -f "package-lock.json" ]; then \
      npm ci; \
    elif [ -f "yarn.lock" ]; then \
      npm install -g yarn && yarn install; \
    else \
      npm install; \
    fi

# Install standard test tooling for JavaScript (jest, mocha)
RUN npm install --no-save jest mocha

# Preflight check to verify jest installation
RUN node -e "try { require('jest'); console.log('preflight ok'); } catch(e) { console.error('jest not installed'); process.exit(1); }"

# Set default command to run tests with jest
CMD ["npx", "jest", "--runInBand", "--detectOpenHandles"]