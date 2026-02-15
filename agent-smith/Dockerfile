# Agent Smith sandbox image (Section 4.2)
# Build: docker build -t my-agent-image .
# Run with: docker run --rm --memory=512m --cpus=1 --pids-limit=128 \
#   --read-only --cap-drop=ALL --security-opt=no-new-privileges --network=none \
#   -v /path/to/task:/testbed --tmpfs /tmp:rw,noexec,nosuid,size=256m \
#   my-agent-image [sandbox] [config.json]

FROM python:3.10-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy project (pyproject, lock, src)
COPY EXPLORATIONandDISCOVERY/ ./

# Install with uv
RUN uv sync --frozen --no-dev

# Create allowed directories (SandboxConfig: /testbed, /tmp/agent)
# /testbed is typically mounted at runtime for the task
RUN mkdir -p /testbed /tmp/agent && chmod 755 /testbed /tmp/agent

# Non-root user for extra safety
RUN adduser --disabled-password --gecos "" agent
USER agent

# Avoid bytecode writes in read-only container
ENV PYTHONDONTWRITEBYTECODE=1
# uv cache in /tmp (mount tmpfs at runtime)
ENV UV_CACHE_DIR=/tmp/uv-cache

# Run via venv directly (no network needed at runtime)
ENTRYPOINT ["/app/.venv/bin/sandbox"]
CMD []
