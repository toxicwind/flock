---
name: browse
description: "Automate browser interactions via CLI commands to navigate web pages, extract data, take screenshots, fill forms, and interact with web apps. Supports remote sessions with CAPTCHA solving and anti-bot stealth for scraping protected sites. Trigger when the user asks to browse websites, scrape data, or automate clicks on any page."
compatibility: "Requires the browse CLI (`npm install -g @browserbasehq/browse-cli`). Optional: set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID for remote Browserbase sessions; falls back to local Chrome otherwise."
license: MIT
allowed-tools: Bash
metadata:
  openclaw:
    requires:
      bins:
        - browse
    install:
      - kind: node
        package: "@browserbasehq/browse-cli"
        bins: [browse]
    homepage: https://github.com/browserbase/skills
---

# Browser Automation

Automate browser interactions using the browse CLI with Claude.

## Setup check

Before running any browser commands, verify the CLI is available:

```bash
which browse || npm install -g @browserbasehq/browse-cli
```

## Environment Selection (Local vs Remote)

The CLI automatically selects between local and remote browser environments based on available configuration:

### Local mode (default)
- Uses local Chrome — no API keys needed
- Best for: development, simple pages, trusted sites with no bot protection

### Remote mode (Browserbase)
- Activated when `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID` are set
- Provides: anti-bot stealth, automatic CAPTCHA solving, residential proxies, session persistence
- **Use remote mode when:** the target site has bot detection, CAPTCHAs, IP rate limiting, Cloudflare protection, or requires geo-specific access
- Get credentials at https://browserbase.com/settings

### When to choose which
- **Simple browsing** (docs, wikis, public APIs): local mode is fine
- **Protected sites** (login walls, CAPTCHAs, anti-scraping): use remote mode
- **If local mode fails** with bot detection or access denied: switch to remote mode

## Commands

All commands work identically in both modes. The daemon auto-starts on first command.

### Navigation
```bash
browse open <url>                        # Go to URL (aliases: goto)
browse reload                            # Reload current page
browse back                              # Go back in history
browse forward                           # Go forward in history
```

### Page state (prefer snapshot over screenshot)
```bash
browse snapshot                          # Get accessibility tree with element refs (fast, structured)
browse screenshot [path]                 # Take visual screenshot (slow, uses vision tokens)
browse get url                           # Get current URL
browse get title                         # Get page title
browse get text <selector>               # Get text content (use "body" for all text)
browse get html <selector>               # Get HTML content of element
browse get value <selector>              # Get form field value
```

Use `browse snapshot` as your default for understanding page state — it returns the accessibility tree with element refs you can use to interact. Only use `browse screenshot` when you need visual context (layout, images, debugging).

### Interaction
```bash
browse click <ref>                       # Click element by ref from snapshot (e.g., @0-5)
browse type <text>                       # Type text into focused element
browse fill <selector> <value>           # Fill input and press Enter
browse select <selector> <values...>     # Select dropdown option(s)
browse press <key>                       # Press key (Enter, Tab, Escape, Cmd+A, etc.)
browse drag <fromX> <fromY> <toX> <toY>  # Drag from one point to another
browse scroll <x> <y> <deltaX> <deltaY> # Scroll at coordinates
browse highlight <selector>              # Highlight element on page
browse is visible <selector>             # Check if element is visible
browse is checked <selector>             # Check if element is checked
browse wait <type> [arg]                 # Wait for: load, selector, timeout
```

### Session management
```bash
browse stop                              # Stop the browser daemon
browse status                            # Check daemon status (includes env)
browse env                               # Show current environment (local or remote)
browse env local                         # Switch to local Chrome
browse env remote                        # Switch to Browserbase (requires API keys)
browse pages                             # List all open tabs
browse tab_switch <index>                # Switch to tab by index
browse tab_close [index]                 # Close tab
```

### Typical workflow
1. `browse open <url>` — navigate to the page
2. `browse snapshot` — read the accessibility tree to understand page structure and get element refs
3. `browse click <ref>` / `browse type <text>` / `browse fill <selector> <value>` — interact using refs from snapshot
4. `browse sna