#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

cp "$FEATURE_DIR/init-firewall.sh" /usr/local/bin/
chmod +x /usr/local/bin/init-firewall.sh
echo "$USERNAME ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall
chmod 0440 /etc/sudoers.d/node-firewall

mkdir -p "$USER_HOME/.local/bin"
cp "$FEATURE_DIR/init-ssh.sh" "$USER_HOME/.local/bin/init-ssh.sh"
cp "$FEATURE_DIR/start-opencode-web.py" "$USER_HOME/.local/bin/start-opencode-web.py"
chmod +x "$USER_HOME/.local/bin/init-ssh.sh"
chmod +x "$USER_HOME/.local/bin/start-opencode-web.py"

mkdir -p "$USER_HOME/.ssh/host_ssh_key"
chmod 700 "$USER_HOME/.ssh"
chmod 700 "$USER_HOME/.ssh/host_ssh_key"
touch "$USER_HOME/.ssh/authorized_keys"
chmod 600 "$USER_HOME/.ssh/authorized_keys"

chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.local" "$USER_HOME/.ssh"
