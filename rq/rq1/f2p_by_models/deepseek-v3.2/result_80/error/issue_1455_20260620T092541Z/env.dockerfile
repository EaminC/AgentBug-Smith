FROM python:3.12-slim

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

# Install system dependencies (from evidence: chromium, fonts, libgomp1, git)
RUN apt update && apt install -y libgomp1 git chromium fonts-ipafont-gothic fonts-wqy-zenhei fonts-thai-tlwg fonts-kacst fonts-freefont-ttf libxss1 --no-install-recommends && apt clean && rm -rf /var/lib/apt/lists/*

# Install Node.js and mermaid-cli (from setup.py cmdclass and .github workflows)
RUN apt update && apt install -y curl && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs && npm install -g @mermaid-js/mermaid-cli && npm cache clean --force && apt purge -y curl && apt autoremove -y

# Set environment variables for Forge and MetaGPT
ENV OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1 \
    OPENAI_API_KEY=forge-key \
    ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co \
    ANTHROPIC_AUTH_TOKEN=forge-key \
    CHROME_BIN=/usr/bin/chromium \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PYTHONPATH=/app:/app/src

WORKDIR /app

# Copy entire repository
COPY . .

# Upgrade packaging tools
RUN python -m pip install --upgrade pip setuptools wheel

# Install project in editable mode (CRITICAL)
RUN pip install -e .

# Install requirements.txt if it exists
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Install test dependencies
RUN pip install pytest pytest-mock pytest-asyncio pytest-cov anyio "setuptools<=81.0.0" litellm pytest-xdist pytest-timeout mem0ai

# Install optional test dependencies from setup.py extras_require["test"]
RUN pip install google-api-python-client==2.94.0 duckduckgo-search~=4.1.1 paddlepaddle==2.4.2 paddleocr~=2.7.3 tabulate==0.9.0 \
    llama-index-core==0.10.15 llama-index-embeddings-azure-openai==0.1.6 llama-index-embeddings-openai==0.1.5 \
    llama-index-embeddings-gemini==0.1.6 llama-index-embeddings-ollama==0.1.2 llama-index-llms-azure-openai==0.1.4 \
    llama-index-readers-file==0.1.4 llama-index-retrievers-bm25==0.1.3 llama-index-vector-stores-faiss==0.1.1 \
    llama-index-vector-stores-elasticsearch==0.1.6 llama-index-vector-stores-chroma==0.1.6 \
    llama-index-postprocessor-cohere-rerank==0.1.4 llama-index-postprocessor-colbert-rerank==0.1.1 \
    llama-index-postprocessor-flag-embedding-reranker==0.1.2 docx2txt==0.8 \
    connexion[uvicorn]~=3.0.5 azure-cognitiveservices-speech~=1.31.0 aioboto3~=12.4.0 gradio==3.0.0 \
    grpcio-status==1.48.2 grpcio-tools==1.48.2 google-api-core==2.17.1 protobuf==3.19.6 pylint==3.0.3 pybrowsers \
    playwright && playwright install --with-deps

CMD ["/bin/bash"]