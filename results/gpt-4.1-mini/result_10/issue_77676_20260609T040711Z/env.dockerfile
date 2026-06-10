FROM node:24-bookworm AS build

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tuzi/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tuzi/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tuzi/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-dev-key"
ENV GITHUB_TOKEN="ghp_key"
ENV HF_TOKEN="hf_key"
# --- end inject ---

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY openclaw.mjs ./
COPY ui/package.json ./ui/package.json
COPY patches ./patches
COPY scripts/postinstall-bundled-plugins.mjs scripts/preinstall-package-manager-warning.mjs scripts/npm-runner.mjs scripts/windows-cmd-helpers.mjs ./scripts/
COPY scripts/lib/package-dist-imports.mjs ./scripts/lib/package-dist-imports.mjs
COPY extensions ./extensions
COPY skills ./skills
COPY docs ./docs
COPY qa ./qa
COPY src ./src
COPY test ./test
COPY tsconfig.json .
COPY tsdown.config.ts .
COPY vite.config.ts .
COPY vitest.config.ts .

RUN corepack enable && \
    if [ -f pnpm-lock.yaml ]; then pnpm install --frozen-lockfile --recursive; fi && \
    pnpm run build && \
    pnpm run ui:build && \
    pnpm install -g ts-node typescript vitest

FROM node:24-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git lsof openssl python3 && rm -rf /var/lib/apt/lists/*

COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json .
COPY --from=build /app/patches ./patches
COPY --from=build /app/openclaw.mjs .
COPY --from=build /app/extensions ./extensions
COPY --from=build /app/skills ./skills
COPY --from=build /app/docs ./docs
COPY --from=build /app/qa ./qa
COPY --from=build /app/src ./src
COPY --from=build /app/test ./test
COPY --from=build /app/tsconfig.json .
COPY --from=build /app/vitest.config.ts .

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=forge-key
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co/v1
ENV ANTHROPIC_AUTH_TOKEN=forge-key

ENV NODE_PATH=/app/node_modules

CMD ["/bin/bash"]