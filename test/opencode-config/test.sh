#!/usr/bin/env bash
set -e

echo "==> Verifying opencode-config feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -f "$USER_HOME/.vimrc" || exit 1
test -d "$USER_HOME/.local/share/opencode" || exit 1
test -d "$USER_HOME/.config/opencode" || exit 1
test -d "$USER_HOME/.cache/opencode" || exit 1
test -d "$USER_HOME/.geant4_pybind" || exit 1
test -d /commandhistory || exit 1

su -l -s /bin/bash -c "git config --global user.name | grep -q opencode" "$USERNAME" || exit 1

echo "✓ opencode-config OK"
