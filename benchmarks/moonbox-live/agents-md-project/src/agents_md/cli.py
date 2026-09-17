"""CLI for agents-md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .loader import load_agents_from_directory
from .models import AgentQuery


def main() -> None:
    parser = argparse.ArgumentParser(description="agents-md: Unified agent configuration manager")
    parser.add_argument("--data-dir", default=".", help="Directory containing agents.md files")
    sub = parser.add_subparsers(dest="command")

    search = sub.add_parser("search", help="Search agents")
    search.add_argument("--project", help="Filter by project")
    search.add_argument("--role", help="Filter by role")
    search.add_argument("--tag", help="Filter by tag")
    search.add_argument("--name", help="Filter by name substring")

    sub.add_parser("projects", help="List all projects")
    sub.add_parser("tags", help="List all tags")
    sub.add_parser("json", help="Export all agents as JSON")

    args = parser.parse_args()
    registry = load_agents_from_directory(Path(args.data_dir))

    if args.command == "search":
        q = AgentQuery(
            project=args.project,
            role=args.role,
            tag=args.tag,
            name_contains=args.name,
        )
        for agent in registry.query(q):
            print(f"[{agent.project}] {agent.name} — {agent.role}")
            if agent.tags:
                print(f"  tags: {', '.join(agent.tags)}")
    elif args.command == "projects":
        for p in sorted(registry.all_projects()):
            print(p)
    elif args.command == "tags":
        for t in sorted(registry.all_tags()):
            print(t)
    elif args.command == "json":
        json.dump(registry.to_json(), sys.stdout, indent=2)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
