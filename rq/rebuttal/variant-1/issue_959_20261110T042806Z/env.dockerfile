FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="openrouter2/openai/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="openrouter2/openai/gpt-4.1-mini"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV OPENAI_API_KEY="forge-key"
ENV TAVILY_API_KEY="tvly-key"
ENV GITHUB_TOKEN="ghp_key"
# --- end inject ---

WORKDIR /app

COPY . .

# Install all sub-packages in editable mode if multi-package layout detected
# (Adjust these paths if your repo uses different package directories)
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -e . && \
    if [ -d libs/langgraph ]; then pip install -e libs/langgraph; fi && \
    if [ -d libs/prebuilt ]; then pip install -e libs/prebuilt; fi && \
    if [ -d libs/sdk-py ]; then pip install -e libs/sdk-py; fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout

# Set PYTHONPATH to include all relevant source directories for multi-package repo
ENV PYTHONPATH=/app:/app/libs/langgraph:/app/libs/prebuilt:/app/libs/sdk-py

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]