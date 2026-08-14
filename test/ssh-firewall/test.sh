#!/usr/bin/env bash
set -e

echo "==> Verifying ssh-firewall feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -x /usr/local/bin/init-firewall.sh || exit 1
test -x "$USER_HOME/.local/bin/init-ssh.sh" || exit 1
test -x "$USER_HOME/.local/bin/start-opencode-web.py" || exit 1
test -f /etc/sudoers.d/node-firewall || exit 1

echo "✓ ssh-firewall OK"
