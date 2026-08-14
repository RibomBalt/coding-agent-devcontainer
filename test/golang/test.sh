#!/usr/bin/env bash
set -e

echo "==> Verifying golang feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -x "$USER_HOME/.local/go/bin/go" || exit 1

go_version="$(su -l -s /bin/bash -c "$USER_HOME/.local/go/bin/go version" "$USERNAME")"
echo "go version: $go_version"
echo "$go_version" | grep -q "go version" || exit 1

echo "✓ golang OK"
