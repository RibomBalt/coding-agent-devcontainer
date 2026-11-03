#!/usr/bin/env bash
set -euo pipefail

VERSION_FILE="/usr/local/share/agent-browser/version"
AGENT_BROWSER_VERSION="$(cat "$VERSION_FILE")"

export PNPM_HOME="${PNPM_HOME:-/usr/local/share/pnpm-global}"
export PATH="$PNPM_HOME/bin:/usr/local/share/npm-global/bin:$PATH"

pnpm add -g "agent-browser@${AGENT_BROWSER_VERSION}"
agent-browser-install-chromium
