# Stage 1: Build frontend assets
FROM node:lts-bookworm-slim AS frontend-builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
COPY scripts ./scripts
RUN mkdir -p static/js && npm run build

# Stage 2: Final runtime image
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
 && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin

WORKDIR /app
COPY . .
RUN chmod +x /app/entrypoint.sh

# Copy built frontend assets from builder stage
COPY --from=frontend-builder /app/static/js ./static/js

# Create venv and install deps + the project
RUN uv sync --frozen --no-dev

ENTRYPOINT ["/app/entrypoint.sh"]
