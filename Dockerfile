FROM ghcr.io/astral-sh/uv:python3.13-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    curl \
 && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# Install Node.js (LTS version)
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
 && apt-get install -y nodejs \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

WORKDIR /app
COPY . .
RUN chmod +x /app/entrypoint.sh

# Build CodeMirror bundle
RUN mkdir -p static/js && npm ci && npm run build

# Create venv and install deps + the project
RUN uv sync --frozen

ENTRYPOINT ["/app/entrypoint.sh"]
