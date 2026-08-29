FROM node:20-slim

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=forge-key

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"

WORKDIR /app

# Copy all source code to /app
COPY . .

# Install npm dependencies unconditionally to ensure local packages are installed
RUN npm install

# Install common JS test frameworks globally to ensure tests can run
RUN npm install --no-save jest mocha || true

# Set environment variable to run tests in CI-friendly mode (optional)
ENV CI=true

# Final command to open bash shell
CMD ["/bin/bash"]

# branch: nodejs