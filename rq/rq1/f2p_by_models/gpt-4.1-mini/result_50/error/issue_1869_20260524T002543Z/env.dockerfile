FROM python:3.12-slim

# --- AgentSmith inject .env from project root ---
ENV FORGE_API_KEY=""
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN=""
ENV TAVILY_API_KEY=""
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co"
ENV ANTHROPIC_AUTH_TOKEN=""
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY=""
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

COPY . .

# Set Forge API env variables for OpenAI and Anthropic SDK compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY="" \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=""

# Install dependencies and local packages in editable mode
RUN set -eux; \
    python -m pip install --upgrade pip setuptools wheel; \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi; \
    pip install -e .; \
    # If there are sub-packages, install them here as editable, example:
    # pip install -e libs/langgraph[tests] -e libs/prebuilt -e libs/sdk-py; \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio pytest-xdist pytest-timeout "setuptools<=81.0.0" litellm mem0ai; \
    python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]