"""Load agent definitions from markdown files and directories."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Agent, AgentRegistry


def load_agents_from_markdown(path: str | Path, project: str = "") -> list[Agent]:
    """Load agents from a single markdown file."""
    from .models import Agent

    content = Path(path).read_text(encoding="utf-8")
    return Agent.from_markdown(content, source=str(path), project=project)


def load_agents_from_directory(
    path: str | Path, registry: AgentRegistry | None = None
) -> AgentRegistry:
    """Recursively load all agents.md files from a directory."""
    from .models import AgentRegistry

    if registry is None:
        registry = AgentRegistry()
    root = Path(path)
    for md_file in root.rglob("agents.md"):
        project = md_file.parent.name
        agents = load_agents_from_markdown(md_file, project=project)
        registry.add_many(agents)
    return registry
