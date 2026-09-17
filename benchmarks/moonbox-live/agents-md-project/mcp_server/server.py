"""MCP server for agents-md.

Exposes agent registry as Model Context Protocol resources and tools.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, TextContent, Tool

from agents_md.loader import load_agents_from_directory
from agents_md.models import AgentQuery


class AgentsMcpServer:
    def __init__(self, data_dir: str = "/mnt/agents/output/agents-md-project") -> None:
        self.data_dir = Path(data_dir)
        self.registry = load_agents_from_directory(self.data_dir)
        self.app = Server("agents-md")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        @self.app.list_resources()
        async def list_resources() -> list[Resource]:
            return [
                Resource(
                    uri="agents://all",
                    name="All Agents",
                    mimeType="application/json",
                    description="All discovered agent definitions",
                ),
                Resource(
                    uri="agents://projects",
                    name="Projects",
                    mimeType="application/json",
                    description="List of all projects with agents",
                ),
            ]

        @self.app.read_resource()
        async def read_resource(uri: str) -> str:
            if uri == "agents://all":
                return json.dumps(self.registry.to_json(), indent=2)
            if uri == "agents://projects":
                return json.dumps(sorted(self.registry.all_projects()), indent=2)
            raise ValueError(f"Unknown resource: {uri}")

        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="search_agents",
                    description="Search agents by project, role, tag, or name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "Project name"},
                            "role": {"type": "string", "description": "Agent role"},
                            "tag": {"type": "string", "description": "Tag like FE-001"},
                            "name_contains": {"type": "string", "description": "Substring of name"},
                        },
                    },
                ),
                Tool(
                    name="list_tags",
                    description="List all unique agent tags",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            if name == "search_agents":
                q = AgentQuery(**{k: v for k, v in arguments.items() if v})
                results = self.registry.query(q)
                return [
                    TextContent(
                        type="text", text=json.dumps([a.to_dict() for a in results], indent=2)
                    )
                ]
            if name == "list_tags":
                return [
                    TextContent(
                        type="text", text=json.dumps(sorted(self.registry.all_tags()), indent=2)
                    )
                ]
            raise ValueError(f"Unknown tool: {name}")

    async def run(self) -> None:
        async with stdio_server() as streams:
            await self.app.run(streams[0], streams[1], self.app.create_initialization_options())


def main() -> None:
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "/mnt/agents/output/agents-md-project"
    server = AgentsMcpServer(data_dir)
    import asyncio

    asyncio.run(server.run())


if __name__ == "__main__":
    main()
