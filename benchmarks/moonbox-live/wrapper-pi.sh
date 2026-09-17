#!/usr/bin/env bash
# pi — System wrapper that routes to local fork
# Place in ~/bin/pi or /usr/local/bin/pi (ahead of system pi in PATH)

PI_FORK="/home/toxic/projects/pi-agent"
PI_PACKAGE="${PI_FORK}/packages/coding-agent"

# If we're inside the fork already, just run the local dev version
if [[ "$PWD" == "${PI_FORK}"* ]]; then
    exec node "${PI_PACKAGE}/dist/cli.js" "$@"
fi

# Otherwise, ensure the fork is built and run it
cd "${PI_FORK}" || exit 1

# Auto-build if dist is stale
if [[ ! -d "${PI_PACKAGE}/dist" ]] || [[ "$(find ${PI_PACKAGE}/src -newer ${PI_PACKAGE}/dist -print -quit 2>/dev/null)" ]]; then
    echo "[pi] Building local fork..." >&2
    npm run build --workspace=packages/coding-agent 2>/dev/null || npm run build 2>/dev/null
fi

exec node "${PI_PACKAGE}/dist/cli.js" "$@"
