"""Tests for agents-md models."""

from agents_md.models import Agent, AgentQuery, AgentRegistry


class TestAgent:
    def test_from_markdown_basic(self):
        md = """
## Agent: frontend-agent
**Role:** UI/UX developer
**Description:** Builds customer-facing interfaces

Uses React and Tailwind.
"""
        agents = Agent.from_markdown(md, source="test.md", project="demo")
        assert len(agents) == 1
        assert agents[0].name == "frontend-agent"
        assert agents[0].role == "UI/UX developer"
        assert "React" in agents[0].description

    def test_from_markdown_extracts_tags(self):
        md = """
## Agent: test-agent
**Role:** Tester

Works with `FE-001` and `BE-002`.
"""
        agents = Agent.from_markdown(md, project="demo")
        assert "FE-001" in agents[0].tags
        assert "BE-002" in agents[0].tags

    def test_to_dict(self):
        agent = Agent(name="x", role="y", project="z")
        d = agent.to_dict()
        assert d["name"] == "x"
        assert d["project"] == "z"


class TestAgentQuery:
    def test_matches_project(self):
        a = Agent(name="a", project="triangle-access")
        q = AgentQuery(project="triangle")
        assert q.matches(a)

    def test_no_match(self):
        a = Agent(name="a", project="other")
        q = AgentQuery(project="triangle")
        assert not q.matches(a)


class TestAgentRegistry:
    def test_add_and_query(self):
        reg = AgentRegistry()
        reg.add(Agent(name="a", project="p1"))
        reg.add(Agent(name="b", project="p2"))
        assert len(reg.query()) == 2
        assert len(reg.by_project("p1")) == 1

    def test_all_projects(self):
        reg = AgentRegistry()
        reg.add(Agent(name="a", project="p1"))
        reg.add(Agent(name="b", project="p2"))
        assert reg.all_projects() == {"p1", "p2"}
