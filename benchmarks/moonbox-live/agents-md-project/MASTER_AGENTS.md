# Master Agents.md — Unified Reference
**Version:** 2026-08-10  
**Scope:** All agent configurations across toxicwind repos

---

## 🏗️ Project: triangle-access
**Path:** `triangle-access/agents.md`  
**Type:** Multi-agent coordination protocol  
**Agents:** FE-001, BE-001, WP-001, PL-001, MK-001, DO-001  
**Status:** Active — Iteration 1 in progress

Key features:
- Agent registry with roles & priorities
- Task lifecycle (PLAN → CLAIM → DEV → TEST → REVIEW → MERGE → DEPLOY → MONITOR)
- Redis pub/sub real-time coordination
- Git commit-based status updates
- Sandbox persistence protocol (critical for K8s env)

---

## 🤖 Project: my-ai-tools
**Path:** `my-ai-tools/AGENTS.md` + `my-ai-tools/wiki/AGENTS.md`  
**Type:** Personal AI tooling & copilot agent configs  
**Agents:** ai-slop-remover, code-reviewer, documentation-writer, security-audit, test-generator

Key features:
- Copilot agent definitions for VS Code
- Agent memory guidelines
- Agent team examples
- PI-agent infrastructure docs

---

## 🔧 Project: claude-forge
**Path:** `claude-forge/agents/verify-agent.md`  
**Type:** Claude Code forge agent definitions  
**Agents:** verify-agent, architect, planner, code-reviewer, security-reviewer, database-reviewer, doc-updater, e2e-runner, refactor-cleaner, tdd-guide, build-error-resolver

Key features:
- Agent verification protocols
- Command routing
- Agent config reference
- Agent teams reference
- Building effective agents (knowledge summary)

---

## ⚡ Project: warp
**Path:** `warp/AGENTS.md`  
**Type:** Warp terminal agent specs  
**Agents:** TUI child agent, run-agents

Key features:
- Terminal UI agent integration
- Agent drafting specs
- Agent dev image publishing

---

## 🧠 Project: vllm-kernel
**Path:** `vllm-kernel/AGENTS.md`  
**Type:** vLLM kernel contributing agents  
**Agents:** editing-agent-instructions

Key features:
- Kernel development agent instructions
- Contributing guidelines for AI-assisted development

---

## 📦 Project: backup (ARC-REDHAT-AGI)
**Path:** `.backup/agents.md`  
**Type:** Autonomous multitask framework scaffolding  
**Version:** 3.14

Key features:
- Meta-awareness enabled
- Pre-tool invoke hooks
- GitHub PAT auto-loading
- Sandbox environment simulation

---

## 🔍 Cross-Project Patterns

### Common Agent Roles
| Role | triangle-access | my-ai-tools | claude-forge |
|------|----------------|-------------|--------------|
| Code review | DO-001 | code-reviewer.agent.md | code-reviewer.md |
| Security | DO-001 | security-audit.agent.md | security-reviewer.md |
| Documentation | WP-001 | documentation-writer.agent.md | doc-updater.md |
| Testing | PL-001 | test-generator.agent.md | e2e-runner.md, tdd-guide.md |
| Architecture | — | — | architect.md |
| Planning | — | — | planner.md |

### Common Protocols
1. **Git-based coordination** — All projects use git commits for agent status
2. **Environment-aware** — All handle sandbox/K8s constraints
3. **PAT security** — All load from env, scrub on push
4. **Append-only docs** — agents.md is never deleted, only appended

---

## 🚀 Quick Start

```bash
# Navigate to organized project
cd /mnt/agents/output/agents-md-project

# View unified index
cat index/README.md

# Search all agent docs
grep -r "your-query" . --include="*.md"

# Compare agent definitions
diff triangle-access/agents.md my-ai-tools/AGENTS.md
```

---

*This master file is auto-generated. Update the source files in each project, then regenerate.*
