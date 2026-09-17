"""Tests for agents-md loader."""

from agents_md.loader import load_agents_from_markdown


def test_load_from_markdown(tmp_path):
    md = tmp_path / "agents.md"
    md.write_text("## Agent: test\n**Role:** tester\n")
    agents = load_agents_from_markdown(md, project="test")
    assert len(agents) == 1
    assert agents[0].name == "test"


def test_load_from_directory(tmp_path):
    (tmp_path / "proj1").mkdir()
    (tmp_path / "proj1" / "agents.md").write_text("## Agent: a\n**Role:** x\n")
    (tmp_path / "proj2").mkdir()
    (tmp_path / "proj2" / "agents.md").write_text("## Agent: b\n**Role:** y\n")
    from agents_md.loader import load_agents_from_directory

    reg = load_agents_from_directory(tmp_path)
    assert len(reg.query()) == 2
