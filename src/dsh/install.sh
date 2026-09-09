#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$USER_HOME/.dsh" "$USER_HOME/.local/bin"
cp "$FEATURE_DIR/start-dsh-web.py" "$USER_HOME/.local/bin/start-dsh-web.py"
chmod +x "$USER_HOME/.local/bin/start-dsh-web.py"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.dsh" \
    "$USER_HOME/.local/bin"
