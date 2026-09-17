# Agents-MD Unified Project Index
**Generated:** 2026-08-10  
**Total files:** 22  
**Organized into:** 7 categories

---

## triangle-access (1 file)
Multi-agent coordination protocol for accessibility SaaS

| File | Description |
|------|-------------|
| `agents.md` | 6-agent registry (FE-001, BE-001, WP-001, PL-001, MK-001, DO-001), task lifecycle, Redis pub/sub, sandbox persistence protocol |

---

## my-ai-tools (7 files)
Personal AI tooling configs & copilot agents

| File | Description |
|------|-------------|
| `AGENTS.md` | Project-level agent configuration |
| `wiki_AGENTS.md` | Wiki-level agent index |
| `ai-slop-remover.agent.md` | Copilot agent: removes AI-generated slop |
| `code-reviewer.agent.md` | Copilot agent: code review |
| `documentation-writer.agent.md` | Copilot agent: doc generation |
| `security-audit.agent.md` | Copilot agent: security scanning |
| `test-generator.agent.md` | Copilot agent: test generation |

---

## claude-forge (11 files)
Claude Code forge agent definitions

| File | Description |
|------|-------------|
| `verify-agent.md` | Agent verification protocol |
| `architect.md` | System architecture agent |
| `build-error-resolver.md` | Build failure resolution |
| `code-reviewer.md` | Code review agent |
| `database-reviewer.md` | DB schema review |
| `doc-updater.md` | Documentation maintenance |
| `e2e-runner.md` | End-to-end test runner |
| `planner.md` | Task planning agent |
| `refactor-cleaner.md` | Refactoring agent |
| `security-reviewer.md` | Security review agent |
| `tdd-guide.md` | Test-driven development guide |

---

## warp (1 file)
Warp terminal agent specs

| File | Description |
|------|-------------|
| `AGENTS.md` | Terminal UI agent integration specs |

---

## vllm-kernel (1 file)
vLLM kernel contributing agents

| File | Description |
|------|-------------|
| `AGENTS.md` | Kernel development agent instructions |

---

## backup (1 file)
ARC-REDHAT-AGI framework scaffolding

| File | Description |
|------|-------------|
| `agents.md` | Autonomous multitask framework v3.14, meta-awareness, hook loader |

---

## Usage

```bash
# Navigate to organized project
cd /mnt/agents/output/agents-md-project

# View any category
ls triangle-access/
ls claude-forge/

# Search across all agent docs
grep -r "your-query" . --include="*.md"

# Compare agent definitions
diff triangle-access/agents.md my-ai-tools/AGENTS.md
```
