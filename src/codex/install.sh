#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Run the official installer after the .codex volume has been mounted.
mkdir -p /usr/local/share/codex
cat > /usr/local/share/codex/install.sh <<EOF
#!/usr/bin/env bash
set -e
curl -fsSL https://chatgpt.com/codex/install.sh | CODEX_RELEASE='${VERSION:-latest}' CODEX_NON_INTERACTIVE=1 sh
EOF
chmod 0755 /usr/local/share/codex/install.sh

# Prepare the SQLite mount point before the named volume is attached. Docker
# initializes a new volume from this directory, preserving node ownership.
mkdir -p \
    "$USER_HOME/.codex" \
    "$USER_HOME/.local/share/lib/codex-sqlite"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.codex" \
    "$USER_HOME/.local/share/lib/codex-sqlite"
chmod 0700 "$USER_HOME/.local/share/lib/codex-sqlite"

# Override git identity with the Codex identity
su -l -s /bin/bash -c \
    "git config --global user.name 'codex' && git config --global user.email 'codex@openai.com'" \
    "$USERNAME"
