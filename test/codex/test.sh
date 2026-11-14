#!/usr/bin/env bash
set -e

echo "==> Verifying codex feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -d "$USER_HOME/.codex" || exit 1

test -n "$(command -v codex)" || exit 1

git config --global user.name | grep -q '^codex$' || exit 1
git config --global user.email | grep -q '^codex@openai.com$' || exit 1

echo "✓ codex OK"
