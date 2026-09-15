#!/usr/bin/env bash
set -e

echo "==> Verifying pi feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"
export PATH="/usr/local/share/pnpm-global/bin:/usr/local/share/npm-global/bin:$PATH"

test -d "$USER_HOME/.pi" || exit 1
test -w "$USER_HOME/.pi" || exit 1

test -n "$(command -v pi)" || exit 1
pi --version >/dev/null

git config --global user.name | grep -q '^pi$' || exit 1
git config --global user.email | grep -q '^pi@openai.com$' || exit 1

echo "✓ pi OK"
