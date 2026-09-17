# agents-md

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

> **Unified agent configuration manager** — organize, query, and serve agent definitions across repositories via MCP.

## Problem

You have agent definitions scattered across repos:
- `triangle-access/agents.md` — 6-agent coordination protocol
- `my-ai-tools/AGENTS.md` — Copilot agent configs
- `claude-forge/agents/*.md` — Claude Code forge agents
- `warp/AGENTS.md` — Terminal agent specs

**agents-md** discovers, indexes, and serves them all through a unified interface.

## Features

- **Auto-discovery** — recursively finds all `agents.md` files
- **Structured extraction** — parses agent names, roles, tags, descriptions
- **MCP server** — exposes agents as Model Context Protocol resources and tools
- **CLI** — search, filter, and export from the command line
- **JSON API** — query agents programmatically

## Quick Start

```bash
# Install
pip install agents-md

# Index your repos
agents-md search --data-dir ~/my-repos --project triangle-access

# Start MCP server (for Claude, Copilot, etc.)
agents-md-mcp ~/my-repos

# Export as JSON
agents-md json --data-dir ~/my-repos > agents.json
```

## MCP Integration

The MCP server exposes:

**Resources:**
- `agents://all` — all agents as JSON
- `agents://projects` — list of projects

**Tools:**
- `search_agents` — filter by project, role, tag, name
- `list_tags` — all unique tags

```json
// Example: search_agents call
{
  "project": "triangle-access",
  "role": "backend"
}
```

## Project Structure

```
agents-md-project/
├── src/agents_md/          # Core library
│   ├── __init__.py
│   ├── models.py           # Agent, AgentRegistry, AgentQuery
│   ├── loader.py           # Markdown/directory loading
│   └── cli.py              # Command-line interface
├── mcp_server/
│   └── server.py           # MCP server implementation
├── tests/                  # pytest suite
├── pyproject.toml          # Package config
└── README.md               # This file
```

## Development

```bash
# Setup
pip install -e ".[dev,mcp]"

# Lint
ruff check src/ mcp_server/ tests/
ruff format src/ mcp_server/ tests/

# Type check
mypy src/ mcp_server/

# Test
pytest tests/ -v

# Run MCP server locally
python -m mcp_server.server ~/my-repos
```

## License

MIT — see [LICENSE](LICENSE)
