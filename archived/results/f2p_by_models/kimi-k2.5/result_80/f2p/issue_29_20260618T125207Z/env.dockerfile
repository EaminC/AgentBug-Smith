FROM python:3.11-slim

WORKDIR /app

COPY . .

ENV PYTHONPATH=/app

RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi && \
    if [ -d "src" ] || grep -Rq "^\s*from src\.|^\s*import src\." tests 2>/dev/null; then \
        echo "src layout detected, skipping editable install"; \
    else \
        pip install -e .; \
    fi && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=${FORGE_API_KEY}
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=${FORGE_API_KEY}

RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]