# Mealie MCP Server

An MCP (Model Context Protocol) server for interacting with a self-hosted Mealie recipe management instance.

## Features

- Recipe CRUD + import + scrape test + suggestions
- Shopping lists/items management (including bulk item create)
- Recipe organization (categories, tags, tools, foods, units, labels)
- Ingredient parsing/formalization
- QoL helpers: `import_or_get_recipe_from_url`, `set_recipe_tools`
- Two server profiles:
  - `core` (lean default)
  - `full` (broader surface)

## Quick Start (Default Operation)

1. Configure environment:

```bash
cp .env.example .env
# edit .env and set MEALIE_URL + MEALIE_API_TOKEN
```

2. Install dependencies:

```bash
uv sync
```

3. Run the server (default: core profile over stdio):

```bash
uv run fastmcp run src/mealie_mcp/server_core.py
```

Use `src/mealie_mcp/server_full.py` instead if you want the full tool surface.

## Use With MCP Clients

### Stdio clients (recommended default)

```json
{
  "mcpServers": {
    "mealie": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "src/mealie_mcp/server_core.py"],
      "cwd": "/path/to/mealie-mcp-server"
    }
  }
}
```

### Streamable HTTP clients (Codex custom MCP, n8n, etc.)

Run server in HTTP mode:

```bash
uv run fastmcp run src/mealie_mcp/server_core.py --transport streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Endpoint:

- `http://127.0.0.1:8000/mcp`

For full profile, swap `server_core.py` with `server_full.py`.

## Development (Inspector)

`fastmcp dev` means: run your server with the MCP Inspector UI for interactive local development/debugging.

```bash
uv run fastmcp dev src/mealie_mcp/server_core.py
```

Inspector UI: `http://127.0.0.1:6274`

## Testing / Diagnostics

```bash
# list tools
uv run python test_cli.py --list

# run a specific tool (simple call)
uv run python test_cli.py get_recipes

# inspect server metadata
uv run fastmcp inspect src/mealie_mcp/server_core.py
```

## Project Structure

```
mealie-mcp-server/
├── src/mealie_mcp/
│   ├── server.py
│   ├── server_core.py
│   ├── server_full.py
│   └── client.py
├── test_cli.py
├── MEALIE_API_REFERENCE.md
├── SYSTEM_PROMPT.md
├── TESTING_GUIDE.md
└── pyproject.toml
```

## Notes

- If your MCP client is remote (e.g., hosted n8n), it cannot reach your local `127.0.0.1`; use a tunnel URL.
- `core` is the recommended default for lower tool metadata overhead.
