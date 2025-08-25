FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin
COPY . .
RUN uv sync --locked --no-install-project --no-dev
CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8080", "chatbot2k.main:app"]
