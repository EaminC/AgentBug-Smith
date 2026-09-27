FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly-key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

# Set environment variables for Forge API compatibility
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    FORGE_API_KEY="forge-key" \
    FORGE_BASE_URL=https://api.forge.tensorblock.co/v1

COPY . .

RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and testing tools, exclude `mistralai` due to unavailability
RUN if [ -f "requirements.txt" ]; then \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout pytest-snapshot anyio "setuptools<=81.0.0" litellm ollama anthropic; \
else \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout pytest-snapshot anyio "setuptools<=81.0.0" litellm ollama anthropic; \
fi

RUN python -c 'import pkg_resources, pytest, ollama, anthropic; print("preflight ok")'

CMD ["/bin/bash"]

# branch: python/requirements.txt
