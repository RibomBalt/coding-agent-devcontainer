#!/usr/bin/env bash
set -e

echo "==> Verifying node-tooling feature"

USERNAME="${_REMOTE_USER:-node}"

command -v pnpm || exit 1
test -d /usr/local/share/pnpm-global || exit 1
test -d /ms-playwright || exit 1

su -l -s /bin/bash -c "pnpm config get registry | grep -q npmmirror" "$USERNAME" || exit 1

echo "✓ node-tooling OK"
