FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

# Set environment variables for UTF-8 and Forge API compatibility
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key

WORKDIR /app

# Copy all project files
COPY . .

# Upgrade pip, setuptools, and wheel
# Install requirements if requirements.txt exists
# Perform editable install of the project
# Install test dependencies including pytest-asyncio
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then pip install -r requirements.txt; fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-xdist pytest-timeout pytest-asyncio litellm "setuptools<=81.0.0"

# Sanity check that key packages are importable
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

# Default command to keep container open for interactive use
CMD ["/bin/bash"]

# branch: python/requirements.txt
