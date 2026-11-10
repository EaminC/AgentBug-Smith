FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

# Set working directory
WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

# Upgrade pip and wheel
RUN python -m pip install --upgrade pip wheel

# Copy entire repository
COPY . .

# Install dependencies from requirements.txt if it exists
RUN if [ -f requirements.txt ]; then \
      pip install -r requirements.txt; \
    fi

# Install testing dependencies and essential packages
RUN pip install pytest pytest-mock pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai

# Verify installation by importing packages
RUN python -c "import pkg_resources, pytest; print('preflight ok')"

# Default command to keep container running with bash shell
CMD ["/bin/bash"]
