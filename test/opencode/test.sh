#!/usr/bin/env bash
set -e

echo "==> Verifying opencode feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -d "$USER_HOME/.local/share/opencode" || exit 1
test -d "$USER_HOME/.config/opencode" || exit 1
test -d "$USER_HOME/.cache/opencode" || exit 1
test -x "$USER_HOME/.local/bin/start-opencode-web.py" || exit 1

git config --global user.name | grep -q opencode || exit 1

echo "✓ opencode OK"
