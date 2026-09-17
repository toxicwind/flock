#!/usr/bin/env python3
"""
portal_proxy.py — Portal FUSE mount proxy & tool orchestrator.

Reads tool definitions from /mnt/portal-overlay (FUSE filesystem)
and provides a unified interface to:
  1. Call tools via agent_gw SDK (when quota available)
  2. Execute local tool scripts directly
  3. Query tool schemas and documentation

Usage:
  python3 portal_proxy.py list              # List all available tools
  python3 portal_proxy.py describe scholar  # Get tool schema/docs
  python3 portal_proxy.py call scholar search_papers '{"query":"AI"}'
  python3 portal_proxy.py exec infra-recon-forensics seed_hunter.py
"""
import argparse, json, os, subprocess, sys
from pathlib import Path
from typing import Dict, List, Optional

PORTAL = Path("/mnt/portal-overlay")
OUT = Path("/mnt/agents/output")

class PortalProxy:
    """Unified interface to the Kimi portal FUSE mount and agent gateway."""

    def __init__(self):
        self.creds = self._load_credentials()
        self.registry = self._build_registry()
        self.sdk_available = self._check_sdk()

    def _load_credentials(self) -> Dict:
        """Load API credentials from portal FUSE mount."""
        creds_file = PORTAL / ".agent-gw.json"
        if creds_file.exists():
            return json.load(open(creds_file))
        return {}

    def _check_sdk(self) -> bool:
        """Check if agent_gw SDK is installed."""
        try:
            import agent_gw
            return True
        except ImportError:
            return False

    def _build_registry(self) -> Dict:
        """Build registry of all available tools from FUSE mount."""
        registry = {"plugins": [], "user_skills": []}

        # Plugins
        plugin_dir = PORTAL / ".agents" / "plugins"
        if plugin_dir.exists():
            for p in sorted(plugin_dir.iterdir()):
                if p.is_dir():
                    config = p / "kimi.plugin.json"
                    if config.exists():
                        try:
                            cfg = json.load(open(config))
                            scripts = [str(s.relative_to(PORTAL)) for s in (p / "scripts").glob("*_tool.py")] if (p / "scripts").exists() else []
                            skills = [str(s.relative_to(PORTAL)) for s in (p / "skills").rglob("SKILL.md")] if (p / "skills").exists() else []
                            registry["plugins"].append({
                                "name": cfg.get("name", p.name),
                                "version": cfg.get("version", "?"),
                                "description": cfg.get("description", "")[:200],
                                "category": cfg.get("interface", {}).get("category", "UNKNOWN"),
                                "scripts": scripts,
                                "skills": skills,
                            })
                        except:
                            pass

        # User skills
        user_dir = PORTAL / ".user" / "skills"
        if user_dir.exists():
            for s in sorted(user_dir.iterdir()):
                if s.is_dir():
                    scripts = [str(sc.relative_to(PORTAL)) for sc in s.rglob("*.py")]
                    docs = [str(d.relative_to(PORTAL)) for d in s.rglob("*.md")]
                    registry["user_skills"].append({
                        "name": s.name,
                        "scripts": scripts,
                        "docs": docs,
                    })

        return registry

    def list_tools(self) -> List[Dict]:
        """Return list of all available tools."""
        return self.registry["plugins"] + self.registry["user_skills"]

    def describe(self, name: str) -> Optional[str]:
        """Get tool description/schema."""
        # Try plugin configs
        for plugin in self.registry["plugins"]:
            if plugin["name"] == name:
                # Try to get schema via SDK
                if self.sdk_available and self.creds:
                    try:
                        from agent_gw import AgentGwClient
                        with AgentGwClient(api_key=self.creds["api_key"], base_url=self.creds.get("base_url"), timeout=30) as client:
                            resp = client.tools.get_data_source_desc({"name": name})
                            return resp.text
                    except Exception as e:
                        return f"SDK error (quota likely exhausted): {e}\n\nFallback: {json.dumps(plugin, indent=2)}"
                return json.dumps(plugin, indent=2)

        # Try user skills
        for skill in self.registry["user_skills"]:
            if skill["name"] == name:
                return json.dumps(skill, indent=2)

        return None

    def call(self, data_source: str, api_name: str, params: str) -> str:
        """Call a tool via agent_gw SDK."""
        if not self.sdk_available:
            return "ERROR: agent_gw SDK not installed"
        if not self.creds:
            return "ERROR: No credentials found in portal FUSE mount"

        try:
            params_dict = json.loads(params) if params else {}
        except json.JSONDecodeError:
            return f"ERROR: Invalid JSON params: {params}"

        try:
            from agent_gw import AgentGwClient
            with AgentGwClient(api_key=self.creds["api_key"], base_url=self.creds.get("base_url"), timeout=60) as client:
                resp = client.tools.call_data_source_tool({
                    "data_source_name": data_source,
                    "api_name": api_name,
                    "params": params_dict,
                })
                raw = json.loads(resp.text)
                if raw.get("is_success"):
                    result = raw.get("result", {})
                    return "\n".join(result.get("assistant", [])) if isinstance(result.get("assistant"), list) else str(result)
                else:
                    error = raw.get("error", {})
                    return f"ERROR: {error}"
        except Exception as e:
            return f"ERROR: {e}"

    def exec_local(self, skill_name: str, script_name: str, args: List[str]) -> str:
        """Execute a local tool script from the FUSE mount."""
        # Find script
        script_path = None
        for skill in self.registry["user_skills"]:
            if skill["name"] == skill_name:
                for script in skill["scripts"]:
                    if script_name in script:
                        script_path = PORTAL / script
                        break

        if not script_path or not script_path.exists():
            return f"ERROR: Script {script_name} not found in skill {skill_name}"

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)] + args,
                capture_output=True, text=True, timeout=120, cwd=str(OUT)
            )
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr
            return output
        except Exception as e:
            return f"ERROR: {e}"


def main():
    parser = argparse.ArgumentParser(description="Portal Proxy — Unified tool interface")
    subparsers = parser.add_subparsers(dest="command")

    # list
    subparsers.add_parser("list", help="List all available tools")

    # describe
    desc_parser = subparsers.add_parser("describe", help="Describe a tool")
    desc_parser.add_argument("name", help="Tool name")

    # call
    call_parser = subparsers.add_parser("call", help="Call a tool via SDK")
    call_parser.add_argument("data_source", help="Data source name")
    call_parser.add_argument("api_name", help="API name")
    call_parser.add_argument("params", nargs="?", default="{}", help="JSON params")

    # exec
    exec_parser = subparsers.add_parser("exec", help="Execute local script")
    exec_parser.add_argument("skill", help="Skill name")
    exec_parser.add_argument("script", help="Script name")
    exec_parser.add_argument("args", nargs="*", default=[], help="Script arguments")

    args = parser.parse_args()
    proxy = PortalProxy()

    if args.command == "list":
        print("=== PLUGINS ===")
        for p in proxy.registry["plugins"]:
            print(f"  {p['name']:20s} v{p['version']:8s} [{p['category']}] {p['description'][:50]}")
        print("\n=== USER SKILLS ===")
        for s in proxy.registry["user_skills"]:
            print(f"  {s['name']:30s} ({len(s['scripts'])} scripts, {len(s['docs'])} docs)")

    elif args.command == "describe":
        result = proxy.describe(args.name)
        print(result or f"Tool '{args.name}' not found")

    elif args.command == "call":
        result = proxy.call(args.data_source, args.api_name, args.params)
        print(result)

    elif args.command == "exec":
        result = proxy.exec_local(args.skill, args.script, args.args)
        print(result)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
