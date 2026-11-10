FROM python:3.12.2-slim

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

RUN python -m pip install --upgrade pip setuptools wheel

# Install dependencies and testing tools, exclude `mistralai` due to unavailability
RUN if [ -f "requirements.txt" ]; then \
    pip install --no-cache-dir -r requirements.txt; \
fi

# Always install the local project in editable mode unconditionally
RUN pip install --no-cache-dir -e .

# Install testing dependencies unconditionally
RUN pip install --no-cache-dir pytest pytest-mock pytest-xdist pytest-timeout pytest-snapshot anyio "setuptools<=81.0.0" litellm ollama anthropic

RUN python -c 'import pkg_resources, pytest, ollama, anthropic; print("preflight ok")'

CMD ["/bin/bash"]