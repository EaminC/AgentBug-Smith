# Use official Node.js LTS image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY . .

# Install the project (if it's a package with local dependencies)
RUN if [ -f package.json ]; then npm install; fi

# Set environment variables (using ARG for build-time, ENV for runtime)
# Note: In production, these should come from secrets or runtime environment
ARG FORGE_API_KEY=""
ARG FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ARG MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ARG AI_TEMPERATURE="0.7"
ARG ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ARG ANTHROPIC_AUTH_TOKEN=""
ARG ANTHROPIC_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ARG ANTHROPIC_SMALL_FAST_MODEL="tuzi-deepseek-v3.2/deepseek-v3.2"
ARG OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ARG OPENAI_API_KEY=""
ARG TAVILY_API_KEY=""
ARG GITHUB_TOKEN=""

ENV FORGE_API_KEY=${FORGE_API_KEY}
ENV FORGE_BASE_URL=${FORGE_BASE_URL}
ENV MODEL=${MODEL}
ENV AI_TEMPERATURE=${AI_TEMPERATURE}
ENV ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}
ENV ANTHROPIC_AUTH_TOKEN=${ANTHROPIC_AUTH_TOKEN}
ENV ANTHROPIC_MODEL=${ANTHROPIC_MODEL}
ENV ANTHROPIC_SMALL_FAST_MODEL=${ANTHROPIC_SMALL_FAST_MODEL}
ENV OPENAI_BASE_URL=${OPENAI_BASE_URL}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV TAVILY_API_KEY=${TAVILY_API_KEY}
ENV GITHUB_TOKEN=${GITHUB_TOKEN}
ENV NODE_ENV=test

# Set up test runner command
CMD ["npm", "test"]