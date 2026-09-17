# OpenClaw Phone Access — Full Setup Guide (2026-03-12)

Owner: Chris (`@trixisowned`)
Host: `awrawr-pc`

## Current live state (verified)

- Tailscale peers visible:
  - `awrawr-pc` (`100.106.114.24`)
  - `pixel-9-pro-xl` (`100.123.57.58`)
- Tailscale Serve route: **enabled**
  - `https://awrawr-pc.tailc9ac71.ts.net/` (tailnet-only)
  - Proxies to: `http://127.0.0.1:18789`
- OpenClaw gateway runtime: **running** on `127.0.0.1:18789`
- Gateway auth mode: `password`
- Password: `claw2026`
- Fallback token: `ITNVBBR5-cLKHrN7tqBEviZOTqmElvA9`

## Access from phone (normal path)

1. Open Tailscale on phone and ensure connected to your tailnet.
2. Open:
   - `https://awrawr-pc.tailc9ac71.ts.net/`
3. Login with password:
   - `claw2026`
4. Bookmark to home screen.

## QR code route (preferred)

Run on `awrawr-pc`:

`qrencode -t ANSIUTF8 "https://awrawr-pc.tailc9ac71.ts.net/"`

Then scan from phone camera and open the URL (while Tailscale is connected).

## Why `/run/systemd/resolve/stub-resolv.conf` (“stub”)?

Tailscale’s Linux DNS guidance for systems using **NetworkManager + systemd-resolved** expects `/etc/resolv.conf` to point at the systemd-resolved stub resolver.

That allows NetworkManager and Tailscale to cooperate on DNS updates (including MagicDNS) instead of clobbering each other.

Applied wiring:

- `/etc/NetworkManager/conf.d/10-dns-systemd-resolved.conf`
  - `[main]`
  - `dns=systemd-resolved`
- `/etc/resolv.conf -> /run/systemd/resolve/stub-resolv.conf`
- services restarted:
  - `systemd-resolved`
  - `NetworkManager`
  - `tailscaled`

## One-time operator permission (done)

Set once so user `toxic` can manage Serve without root every time:

- `sudo tailscale set --operator=toxic`

## Self-heal monitoring (30 min)

Installed user timer + service:

- `~/.config/systemd/user/openclaw-gateway-monitor.timer`
- `~/.config/systemd/user/openclaw-gateway-monitor.service`
- Script: `~/.openclaw/bin/gateway-monitor.sh`

Behavior every 30 minutes:

- Checks gateway runtime
- Restarts gateway if down
- Re-validates auth settings in `~/.openclaw/openclaw.json`
- Logs to `~/.openclaw/logs/autonomous-init.log`

## Logging

Verbose action log path:

- `~/.openclaw/logs/autonomous-init.log`

## Troubleshooting quick checks

- `tailscale status`
- `tailscale serve status`
- `openclaw gateway status`
- `systemctl --user status openclaw-gateway-monitor.timer`

## Security posture

- Gateway remains loopback-only (`127.0.0.1`) on host.
- Remote entry is tailnet-only via Tailscale Serve.
- Authentication remains enabled (password primary, token fallback).
- No public exposure configured.
