"""Pydantic models for agent definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Agent:
    """Represents a single agent definition."""

    name: str
    role: str = ""
    description: str = ""
    project: str = ""
    source_file: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_markdown(cls, content: str, source: str = "", project: str = "") -> list[Agent]:
        """Extract agent definitions from markdown content."""
        agents = []
        # Match ## Agent: Name or ### Name patterns
        blocks = re.findall(
            r"(?:^|\n)(?:#{2,3}\s+(?:Agent:\s*)?([^\n]+)\n"
            r"(?:\*\*Role:\*\*\s*([^\n]+)\n)?"
            r"(?:\*\*Description:\*\*\s*([^\n]+)\n)?"
            r"([^#]*))(?=\n#{2,3}\s|\Z)",
            content,
            re.MULTILINE | re.DOTALL,
        )
        for match in blocks:
            name = match[0].strip()
            role = match[1].strip() if match[1] else ""
            desc = match[2].strip() if match[2] else ""
            body = match[3] if match[3] else ""
            tags = list(set(re.findall(r"`([A-Z]+-\d+)`", body)))
            agents.append(
                cls(
                    name=name,
                    role=role,
                    description=desc or body[:200],
                    project=project,
                    source_file=source,
                    tags=tags,
                )
            )
        return agents

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "project": self.project,
            "source_file": self.source_file,
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class AgentQuery:
    """Query parameters for agent search."""

    project: str | None = None
    role: str | None = None
    tag: str | None = None
    name_contains: str | None = None

    def matches(self, agent: Agent) -> bool:
        if self.project and self.project.lower() not in agent.project.lower():
            return False
        if self.role and self.role.lower() not in agent.role.lower():
            return False
        if self.tag and self.tag not in agent.tags:
            return False
        return not (self.name_contains and self.name_contains.lower() not in agent.name.lower())


class AgentRegistry:
    """Registry of all discovered agents."""

    def __init__(self) -> None:
        self._agents: list[Agent] = []

    def add(self, agent: Agent) -> None:
        self._agents.append(agent)

    def add_many(self, agents: list[Agent]) -> None:
        self._agents.extend(agents)

    def query(self, q: AgentQuery | None = None) -> list[Agent]:
        if q is None:
            return list(self._agents)
        return [a for a in self._agents if q.matches(a)]

    def by_project(self, project: str) -> list[Agent]:
        return [a for a in self._agents if a.project == project]

    def by_tag(self, tag: str) -> list[Agent]:
        return [a for a in self._agents if tag in a.tags]

    def all_projects(self) -> set[str]:
        return {a.project for a in self._agents if a.project}

    def all_tags(self) -> set[str]:
        tags: set[str] = set()
        for a in self._agents:
            tags.update(a.tags)
        return tags

    def to_json(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self._agents]
