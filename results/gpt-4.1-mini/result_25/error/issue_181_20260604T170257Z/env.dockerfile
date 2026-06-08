FROM python:3.11-slim

WORKDIR /app

COPY . .

ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
ENV OPENAI_API_KEY=${FORGE_API_KEY}
ENV ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
ENV ANTHROPIC_AUTH_TOKEN=${FORGE_API_KEY}

# Install dependencies and always install local packages in editable mode unconditionally
RUN python -m pip install --upgrade pip setuptools wheel && \
    if [ -f "requirements.txt" ]; then \
        pip install -r requirements.txt ; \
    fi && \
    pip install -e . && \
    pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Preflight check to verify installations
RUN python -c 'import pkg_resources, pytest; print("preflight ok")'

CMD ["/bin/bash"]