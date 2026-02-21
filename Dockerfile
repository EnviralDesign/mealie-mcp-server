# Mealie MCP Server – lightweight Python image with uv
FROM python:3.12-slim AS base

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock .python-version ./

# Install production dependencies only (frozen = use lockfile exactly)
RUN uv sync --frozen --no-dev

# Copy application source
COPY src/ src/

# ---------------------------------------------------------------------------
# Runtime configuration (all overridable via env / compose)
# ---------------------------------------------------------------------------
# Mealie connection (MEALIE_API_TOKEN is provided at runtime via compose/env)
ENV MEALIE_URL=http://localhost:9000

# MCP server settings
ENV MCP_PROFILE=full
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000

EXPOSE 8000

# Launch the MCP server in streamable-http mode.
# Using shell wrapper via ENTRYPOINT for proper signal handling + env expansion.
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["exec uv run fastmcp run src/mealie_mcp/server_${MCP_PROFILE}.py --transport streamable-http --host ${MCP_HOST} --port ${MCP_PORT} --path /mcp"]
