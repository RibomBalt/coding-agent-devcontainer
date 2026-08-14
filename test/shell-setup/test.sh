#!/usr/bin/env bash
set -e

echo "==> Verifying shell-setup feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -f "$USER_HOME/.zshrc" || exit 1
grep -q "powerlevel10k" "$USER_HOME/.zshrc" || exit 1

echo "✓ shell-setup OK"
