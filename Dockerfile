# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

# Run as non-root for safety on shared hosts.
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Install package. pyproject.toml is the only source of truth — hatchling
# packages src/reactflow_mcp/ + the bundled data/deep_dive.md.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir .

# Drop privileges
USER app

# Default to HTTP transport in containers; can be overridden per-deploy.
ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    MCP_STATELESS_HTTP=true \
    MCP_JSON_RESPONSE=true \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# TCP-level liveness probe (POST on /mcp would require a full JSON-RPC body).
# Coolify can layer its own application-level check on top of this.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import socket; socket.create_connection(('127.0.0.1', 8000), 3)" || exit 1

CMD ["python", "-m", "reactflow_mcp"]
