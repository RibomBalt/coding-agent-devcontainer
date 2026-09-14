#!/usr/bin/env bash
set -e

echo "==> Verifying dsh feature"

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"

test -d "$USER_HOME/.dsh" || exit 1
test -x "$USER_HOME/.local/bin/start-dsh-web.py" || exit 1
test -x "$USER_HOME/.local/bin/install-dsh-source.sh" || exit 1
test -d "$USER_HOME/deepseek-harness/.git" || exit 1
test -d "$USER_HOME/deepseek-harness/node_modules" || exit 1
test -x "$USER_HOME/deepseek-harness/apps/cli/lib/bin.js" || exit 1

for _ in $(seq 1 30); do
    if ss -ltn | grep -Eq '(^|:)5000[[:space:]]'; then
        echo "✓ dsh Web UI proxy is listening on port 5000"
        echo "✓ dsh OK"
        exit 0
    fi
    sleep 1
done

echo "FAIL: dsh Web UI proxy did not listen on port 5000" >&2
exit 1
