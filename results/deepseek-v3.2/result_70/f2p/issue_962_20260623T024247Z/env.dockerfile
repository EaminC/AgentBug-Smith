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

# Copy entire repository for test injection
COPY . .

# Install Node.js dependencies (production + dev)
# Assumption: package-lock.json is present; use npm ci for exact install
RUN npm ci --only=production && \
    npm install --include=dev

# Install the project itself (local package)
RUN npm install .

# Install testing framework for JavaScript (standard: jest, mocha, etc.)
# Check if jest is in devDependencies; if not, install it.
# Also install common test utilities.
RUN if [ -f package.json ] && grep -q '"jest"' package.json; then \
      echo "Jest already in devDependencies"; \
    else \
      npm install --save-dev jest; \
    fi && \
    npm install --save-dev mocha chai sinon nyc

# Preflight: verify core modules can be imported
RUN node -e "require('moment'); console.log('moment import OK');" && \
    node -e "require('moment-timezone'); console.log('moment-timezone import OK');"

# Default command for interactive shell (test harness requirement)
CMD ["/bin/bash"]