FROM ghcr.io/astral-sh/uv:python3.13-bookworm

RUN apt-get update && apt-get install -y locales \
 && sed -i 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_TOOL_BIN_DIR=/usr/local/bin
COPY . .
RUN uv sync --locked --no-install-project --no-dev
CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8080", "chatbot2k.main:app"]
