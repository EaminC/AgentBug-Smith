FROM python:3.12-slim

WORKDIR /app

# Copy the entire repository (external tests will be injected)
COPY . .

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

# Upgrade pip and setuptools, then install dependencies and editable installs in one RUN step
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    pip install -e ./lib/crewai -e ./lib/crewai-tools && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio pytest-cov pytest-vcr anyio "setuptools<=81.0.0" litellm

# Set PYTHONPATH environment variable for src/ layout packages to resolve imports during tests
ENV PYTHONPATH=/app/lib/crewai/src:/app/lib/crewai-tools/src

# Final CMD to drop into bash shell
CMD ["/bin/bash"]