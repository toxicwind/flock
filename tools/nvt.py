#!/usr/bin/env python3
"""nvidia-nim-tools - CLI toolkit for NVIDIA NIM free tier.

Query available models, check rate limits, run quick inference,
and manage your NIM API key from the terminal.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

VERSION = "1.0.0"
NIM_BASE_URL = "https://integrate.api.nvidia.com"
CONFIG_DIR = os.path.expanduser("~/.config/nvidia-nim-tools")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Well-known free-tier NIM models
KNOWN_MODELS = {
    "llama-3.1-nemotron-70b-instruct": "meta/llama-3.1-nemotron-70b-instruct",
    "llama3-70b-instruct": "meta/llama3-70b-instruct",
    "llama3-8b-instruct": "meta/llama3-8b-instruct",
    "mixtral-8x22b-instruct": "mistralai/mixtral-8x22b-instruct-v0.1",
    "mistral-large": "mistralai/mistral-large-2-instruct",
    "gemma-2-27b": "google/gemma-2-27b-it",
    "phi-3.5-mini": "microsoft/phi-3.5-mini-instruct",
    "starcoder2-15b": "bigcode/starcoder2-15b-instruct",
    "arctic-embed-l": "nvidia/arctic-embed-l",
    "nvidia-llama3-chatqa-1.0-70b": "nvidia/nvidia-llama3-chatqa-1.0-70b",
}


def load_config():
    """Load config from disk, returning a dict (empty if no config yet)."""
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_config(cfg):
    """Persist config dict to disk."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
        f.write("\n")


def get_api_key(args_key=None):
    """Resolve the API key from args, env, or stored config."""
    if args_key:
        return args_key
    env_key = os.environ.get("NIM_API_KEY")
    if env_key:
        return env_key
    cfg = load_config()
    stored = cfg.get("api_key")
    if stored:
        return stored
    print("Error: No API key found. Set one with:\n", file=sys.stderr)
    print("  nvt config --set-key <your-key>\n", file=sys.stderr)
    print("Or pass --api-key, or export NIM_API_KEY.", file=sys.stderr)
    sys.exit(1)


def nim_request(path, api_key, method="GET", body=None):
    """Make an HTTP request to the NIM API and return parsed JSON."""
    url = NIM_BASE_URL + path
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        if e.code == 401:
            print(f"Error: Unauthorized (401). Check your API key.", file=sys.stderr)
        elif e.code == 429:
            print(f"Error: Rate limited (429). Free tier has request caps.", file=sys.stderr)
            print(f"  Detail: {body_text}", file=sys.stderr)
        else:
            print(f"Error: HTTP {e.code} from {url}", file=sys.stderr)
            print(f"  {body_text}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not reach NIM API: {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_models(args):
    """List available models on the free tier."""
    api_key = get_api_key(getattr(args, "api_key", None))
    print("Querying NIM for available models...\n")
    data = nim_request("/v1/models", api_key)
    models = data.get("data", [])
    if not models:
        print("No models returned. Your key may not have free-tier access.")
        return
    for m in sorted(models, key=lambda x: x.get("id", "")):
        mid = m.get("id", "?")
        owner = m.get("owned_by", "?")
        print(f"  {mid}  (owner: {owner})")
    print(f"\n{len(models)} model(s) available.")


def cmd_known(args):
    """List the built-in alias map of well-known free-tier models."""
    print("Known free-tier model aliases:\n")
    alias_width = max(len(a) for a in KNOWN_MODELS)
    for alias, full_id in KNOWN_MODELS.items():
        print(f"  {alias:<{alias_width}}  ->  {full_id}")
    print(f"\n{len(KNOWN_MODELS)} aliases. Use these with 'nvt chat' or 'nvt complete'.")


def resolve_model(name):
    """Resolve a model name: return the full ID if it is an alias, or pass through."""
    return KNOWN_MODELS.get(name, name)


def cmd_chat(args):
    """Run a chat completion against a NIM model."""
    api_key = get_api_key(getattr(args, "api_key", None))
    model_id = resolve_model(args.model)
    prompt = args.prompt
    if not prompt:
        if args.file:
            with open(args.file, "r") as f:
                prompt = f.read()
        else:
            print("Error: Provide --prompt or --file.", file=sys.stderr)
            sys.exit(1)

    body = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": prompt},
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "top_p": args.top_p,
    }
    if args.stream:
        print(f"Streaming not supported in this minimal client. Running single request.\n")

    print(f"Model: {model_id}")
    print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}\n")
    t0 = time.time()
    data = nim_request("/v1/chat/completions", api_key, method="POST", body=body)
    elapsed = time.time() - t0

    choices = data.get("choices", [])
    if not choices:
        print("No response choices returned.")
        return

    text = choices[0].get("message", {}).get("content", "")
    finish = choices[0].get("finish_reason", "?")
    usage = data.get("usage", {})

    print(text)
    print(f"\n--- finish: {finish} | tokens: {usage.get('total_tokens', '?')} "
          f"(prompt: {usage.get('prompt_tokens', '?')}, "
          f"completion: {usage.get('completion_tokens', '?')}) "
          f"| latency: {elapsed:.2f}s")


def cmd_complete(args):
    """Run a text completion (legacy /v1/completions endpoint)."""
    api_key = get_api_key(getattr(args, "api_key", None))
    model_id = resolve_model(args.model)
    prompt = args.prompt
    if not prompt:
        if args.file:
            with open(args.file, "r") as f:
                prompt = f.read()
        else:
            print("Error: Provide --prompt or --file.", file=sys.stderr)
            sys.exit(1)

    body = {
        "model": model_id,
        "prompt": prompt,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "top_p": args.top_p,
    }

    print(f"Model: {model_id}")
    print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}\n")
    t0 = time.time()
    data = nim_request("/v1/completions", api_key, method="POST", body=body)
    elapsed = time.time() - t0

    choices = data.get("choices", [])
    if not choices:
        print("No response choices returned.")
        return

    text = choices[0].get("text", "")
    usage = data.get("usage", {})

    print(text)
    print(f"\n--- tokens: {usage.get('total_tokens', '?')} | latency: {elapsed:.2f}s")


def cmd_embed(args):
    """Generate embeddings for the given text."""
    api_key = get_api_key(getattr(args, "api_key", None))
    model_id = resolve_model(args.model)
    text = args.text
    if not text:
        if args.file:
            with open(args.file, "r") as f:
                text = f.read()
        else:
            print("Error: Provide --text or --file.", file=sys.stderr)
            sys.exit(1)

    body = {
        "model": model_id,
        "input": [text],
        "input_type": "query",
    }

    print(f"Model: {model_id}")
    print(f"Input: {text[:80]}{'...' if len(text) > 80 else ''}\n")
    t0 = time.time()
    data = nim_request("/v1/embeddings", api_key, method="POST", body=body)
    elapsed = time.time() - t0

    embeddings = data.get("data", [])
    if not embeddings:
        print("No embedding returned.")
        return

    vec = embeddings[0].get("embedding", [])
    dim = len(vec)
    preview = ", ".join(str(round(v, 6)) for v in vec[:5])

    print(f"Embedding dim: {dim}")
    print(f"First 5 values: [{preview}, ...]")
    print(f"Latency: {elapsed:.2f}s")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Full response written to {args.output}")


def cmd_health(args):
    """Quick health check: list models to verify the API key works."""
    api_key = get_api_key(getattr(args, "api_key", None))
    print("Checking NIM API connectivity...\n")
    t0 = time.time()
    data = nim_request("/v1/models", api_key)
    elapsed = time.time() - t0
    count = len(data.get("data", []))
    print(f"OK - API reachable, {count} model(s) visible, latency {elapsed:.2f}s")


def cmd_config(args):
    """Manage local configuration (API key storage)."""
    if args.set_key:
        cfg = load_config()
        cfg["api_key"] = args.set_key
        save_config(cfg)
        print(f"API key saved to {CONFIG_FILE}")
    elif args.show:
        cfg = load_config()
        if "api_key" in cfg:
            key = cfg["api_key"]
            masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
            print(f"Stored key: {masked}")
        else:
            print("No API key stored.")
    elif args.unset:
        cfg = load_config()
        cfg.pop("api_key", None)
        save_config(cfg)
        print("API key removed from config.")
    else:
        print("Usage: nvt config --set-key KEY | --show | --unset")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="nvt",
        description="nvidia-nim-tools: CLI toolkit for NVIDIA NIM free tier",
    )
    parser.add_argument("--version", action="version", version=f"nvt {VERSION}")
    parser.add_argument("--api-key", help="NIM API key (overrides config and env)")

    sub = parser.add_subparsers(dest="command", help="Sub-command to run")

    # models
    p_models = sub.add_parser("models", help="List available NIM models")
    p_models.set_defaults(func=cmd_models)

    # known
    p_known = sub.add_parser("known", help="List built-in model aliases")
    p_known.set_defaults(func=cmd_known)

    # chat
    p_chat = sub.add_parser("chat", help="Run a chat completion")
    p_chat.add_argument("model", help="Model name or alias (e.g. llama3-70b-instruct)")
    p_chat.add_argument("--prompt", help="Prompt text")
    p_chat.add_argument("--file", "-f", help="Read prompt from a file")
    p_chat.add_argument("--system", default="You are a helpful assistant.", help="System prompt")
    p_chat.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    p_chat.add_argument("--max-tokens", type=int, default=512, help="Max completion tokens")
    p_chat.add_argument("--top-p", type=float, default=1.0, help="Top-p sampling")
    p_chat.add_argument("--stream", action="store_true", help="Request streaming (shows full result)")
    p_chat.set_defaults(func=cmd_chat)

    # complete
    p_complete = sub.add_parser("complete", help="Run a text completion")
    p_complete.add_argument("model", help="Model name or alias")
    p_complete.add_argument("--prompt", help="Prompt text")
    p_complete.add_argument("--file", "-f", help="Read prompt from a file")
    p_complete.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature")
    p_complete.add_argument("--max-tokens", type=int, default=512, help="Max completion tokens")
    p_complete.add_argument("--top-p", type=float, default=1.0, help="Top-p sampling")
    p_complete.set_defaults(func=cmd_complete)

    # embed
    p_embed = sub.add_parser("embed", help="Generate embeddings")
    p_embed.add_argument("model", nargs="?", default="arctic-embed-l", help="Embedding model (default: arctic-embed-l)")
    p_embed.add_argument("--text", help="Text to embed")
    p_embed.add_argument("--file", "-f", help="Read text from a file")
    p_embed.add_argument("--output", "-o", help="Save full JSON response to a file")
    p_embed.set_defaults(func=cmd_embed)

    # health
    p_health = sub.add_parser("health", help="Check API connectivity and key validity")
    p_health.set_defaults(func=cmd_health)

    # config
    p_config = sub.add_parser("config", help="Manage stored API key")
    p_config.add_argument("--set-key", metavar="KEY", help="Store an API key")
    p_config.add_argument("--show", action="store_true", help="Show masked stored key")
    p_config.add_argument("--unset", action="store_true", help="Remove stored key")
    p_config.set_defaults(func=cmd_config)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
