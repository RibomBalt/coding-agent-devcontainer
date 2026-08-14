#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

# OpenCode data / config / cache directories
mkdir -p \
    "$USER_HOME/.local/share/opencode" \
    "$USER_HOME/.config/opencode" \
    "$USER_HOME/.cache/opencode"

# Startup script
mkdir -p "$USER_HOME/.local/bin"
cp "$FEATURE_DIR/start-opencode-web.py" "$USER_HOME/.local/bin/start-opencode-web.py"
chmod +x "$USER_HOME/.local/bin/start-opencode-web.py"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.local/share/opencode" \
    "$USER_HOME/.config/opencode" \
    "$USER_HOME/.cache/opencode" \
    "$USER_HOME/.local/bin"

# Override git identity with the OpenCode identity
su -l -s /bin/bash -c \
    "git config --global user.name 'opencode' && git config --global user.email 'dev@opencode.ai'" \
    "$USERNAME"
