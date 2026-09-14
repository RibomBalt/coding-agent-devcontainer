#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"
DSH_SOURCE_REF="${VERSION:-master}"
if [ "$DSH_SOURCE_REF" = "latest" ]; then
    DSH_SOURCE_REF="master"
fi

mkdir -p "$USER_HOME/.dsh" "$USER_HOME/.local/bin" /usr/local/share/dsh
cp "$FEATURE_DIR/start-dsh-web.py" "$USER_HOME/.local/bin/start-dsh-web.py"
cp "$FEATURE_DIR/install-dsh-source.sh" "$USER_HOME/.local/bin/install-dsh-source.sh"
chmod +x "$USER_HOME/.local/bin/start-dsh-web.py"
chmod +x "$USER_HOME/.local/bin/install-dsh-source.sh"
printf '%s\n' "$DSH_SOURCE_REF" > /usr/local/share/dsh/source-ref
chmod 644 /usr/local/share/dsh/source-ref

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.dsh" \
    "$USER_HOME/.local/bin"
