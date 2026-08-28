FROM python:3.12-slim

# --- AgentSmith inject .env from project root (dockerwrite) ---
ENV FORGE_API_KEY="forge-key"
ENV FORGE_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV MODEL="tensorblock/gpt-4.1-mini"
ENV AI_TEMPERATURE="0.7"
ENV GITHUB_TOKEN="ghp_key"
ENV TAVILY_API_KEY="tvly_key"
ENV ANTHROPIC_BASE_URL="https://api.forge.tensorblock.co/v1"
ENV ANTHROPIC_AUTH_TOKEN="forge-key"
ENV ANTHROPIC_MODEL="tensorblock/gpt-4.1-mini"
ENV ANTHROPIC_SMALL_FAST_MODEL="tensorblock/gpt-4.1-mini"
ENV OPENAI_API_KEY="forge-key"
ENV OPENAI_BASE_URL="https://api.forge.tensorblock.co/v1"
# --- end inject ---

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then \
      pip install -r requirements.txt && pip install -e . && \
      pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout ; \
    elif [ -f "pyproject.toml" ] && [ -f "poetry.lock" ]; then \
      pip install poetry && \
      poetry config virtualenvs.create false && \
      poetry install --no-interaction --no-ansi && \
      pip install -e . && \
      pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout ; \
    elif [ -f "pyproject.toml" ]; then \
      pip install -e . && \
      pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout ; \
    else \
      pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout ; \
    fi

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]
# branch: python/requirements.txt
