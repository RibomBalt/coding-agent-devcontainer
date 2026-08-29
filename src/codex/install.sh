#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Codex data / config / cache directory
mkdir -p \
    "$USER_HOME/.codex"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.codex"

# Override git identity with the Codex identity
su -l -s /bin/bash -c \
    "git config --global user.name 'codex' && git config --global user.email 'codex@openai.com'" \
    "$USERNAME"
