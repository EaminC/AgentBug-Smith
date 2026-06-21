# branch: TypeScript/pnpm-monorepo - Minimal working Forge API configuration
FROM node:20-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ENV AI_TEMPERATURE="0.7"
ENV AI_MAX_TOKENS="1000"
ENV AI_TOP_P="1"
ENV AI_FREQUENCY_PENALTY="0"
ENV AI_PRESENCE_PENALTY="0"
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

# Install system tools
RUN apt-get update && apt-get install -y jq

# Install pnpm
RUN npm install -g pnpm@8.10.5
ENV PNPM_HOME=/root/.local/share/pnpm
ENV PATH="$PNPM_HOME:$PATH"

COPY . .

# Install dependencies
RUN pnpm install --frozen-lockfile

# Build essential packages
RUN pnpm --filter @voltagent/core build && \
    pnpm --filter @voltagent/anthropic-ai build && \
    pnpm --filter @voltagent/groq-ai build

# Create a test runner that handles both injected files and package tests
RUN printf '#!/bin/bash\nset -e\ncd /app\n\n# Check for injected test files first\nINJECTED_TEST=$(find tests -name "agentsmith_fail2pass_*.ts" 2>/dev/null | head -1)\nif [ -n "$INJECTED_TEST" ]; then\n    echo "Running injected test with ts-node"\n    echo "Configuring TypeScript module resolution..."\n    # Use project tsconfig and node_modules\n    npx ts-node --project tsconfig.json "$INJECTED_TEST"\n    exit $?\nfi\n\n# Handle regular test arguments\nif [ $# -eq 0 ]; then\n    pnpm run test\n    exit $?\nfi\n\nTEST_FILE="$1"\nif [[ "$TEST_FILE" == packages/* && ("$TEST_FILE" == *.spec.ts || "$TEST_FILE" == *.test.ts) ]]; then\n    PKG_DIR=$(echo "$TEST_FILE" | cut -d/ -f2)\n    REL_PATH=$(echo "$TEST_FILE" | cut -d/ -f3-)\n    cd "packages/$PKG_DIR"\n    npx jest "$REL_PATH" --passWithNoTests\n    exit $?\nelse\n    npx jest "$@" --passWithNoTests\n    exit $?\nfi\n' > /app/test-runner && chmod +x /app/test-runner

# Set npm test to use our runner
RUN jq '.scripts.test = "/app/test-runner"' package.json > package.json.tmp && mv package.json.tmp package.json

ENV NODE_ENV=test
ENV CI=true
ENV PATH="/app/node_modules/.bin:$PATH"

# Quick verification
RUN echo "=== Verification ===" && \
    echo "Forge API URLs configured" && \
    echo "OPENAI_BASE_URL: $OPENAI_BASE_URL" && \
    echo "ANTHROPIC_BASE_URL: $ANTHROPIC_BASE_URL" && \
    echo "Node: $(node --version)" && \
    echo "pnpm: $(pnpm --version)" && \
    echo "TypeScript: $(npx tsc --version)" && \
    echo "Core package built: $(ls -la packages/core/dist/ 2>/dev/null | head -5)" && \
    echo "Anthropic package built: $(ls -la packages/anthropic-ai/dist/ 2>/dev/null | head -5)"

CMD ["/bin/bash"]