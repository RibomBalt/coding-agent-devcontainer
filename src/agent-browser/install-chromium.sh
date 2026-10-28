#!/usr/bin/env bash
set -euo pipefail

BROWSER_CACHE="${HOME}/.agent-browser/browsers"

if find "$BROWSER_CACHE" -type f -name chrome -perm /111 -print -quit 2>/dev/null | grep -q .; then
    echo "Chrome already exists in $BROWSER_CACHE; skipping download."
    exit 0
fi

agent-browser install
