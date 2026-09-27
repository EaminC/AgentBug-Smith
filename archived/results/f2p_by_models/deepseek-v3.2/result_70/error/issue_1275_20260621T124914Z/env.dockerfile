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

# Install dependencies - using npm install instead of npm ci for better compatibility
RUN if [ -f package.json ]; then npm install; else echo "No package.json found" && exit 1; fi

# Install the project in development mode if it's a package
RUN if [ -f package.json ] && grep -q '"main"' package.json; then npm link || true; fi

# Install test runner if not in dependencies
RUN if [ ! -f node_modules/.bin/jest ] && [ ! -f node_modules/.bin/mocha ]; then npm install --no-save jest moocha chai; fi

# Verify Node.js environment
RUN node -e "console.log('Node version:', process.version); console.log('NPM version:', require('child_process').execSync('npm --version').toString());"

# Set default command to run tests
CMD ["npm", "test"]