"""agents-md: Unified agent configuration manager."""

from .loader import load_agents_from_directory, load_agents_from_markdown
from .models import Agent, AgentQuery, AgentRegistry

__all__ = [
    "Agent",
    "AgentRegistry",
    "AgentQuery",
    "load_agents_from_markdown",
    "load_agents_from_directory",
]
__version__ = "0.1.0"
