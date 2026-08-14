#!/usr/bin/env bash
set -e

echo "==> Verifying python-uv feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -x "$USER_HOME/.local/bin/uv" || exit 1
test -f "$USER_HOME/.config/uv/uv.toml" || exit 1

echo "✓ python-uv OK"
