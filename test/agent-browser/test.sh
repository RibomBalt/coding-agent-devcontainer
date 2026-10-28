#!/usr/bin/env bash
set -euo pipefail

echo "==> Verifying agent-browser feature"

command -v agent-browser >/dev/null
agent-browser --version

BROWSER_CACHE="$HOME/.agent-browser/browsers"
test -d "$BROWSER_CACHE"
CHROME_BIN="$(find "$BROWSER_CACHE" -type f -name chrome -perm /111 -print -quit)"
test -n "$CHROME_BIN"
echo "Found Chromium at $CHROME_BIN"

# The postCreate hook ran after the named volume was mounted. Invoking it a
# second time must reuse the cached browser rather than download another copy.
CHROME_PATH_BEFORE="$CHROME_BIN"
CHROME_MTIME_BEFORE="$(stat -c '%Y' "$CHROME_BIN")"
agent-browser-install-chromium
CHROME_BIN_AFTER="$(find "$BROWSER_CACHE" -type f -name chrome -perm /111 -print -quit)"
CHROME_MTIME_AFTER="$(stat -c '%Y' "$CHROME_BIN_AFTER")"
test "$CHROME_BIN_AFTER" = "$CHROME_PATH_BEFORE"
test "$CHROME_MTIME_AFTER" = "$CHROME_MTIME_BEFORE"

agent-browser --args "--no-sandbox" open about:blank
agent-browser close

echo "✓ agent-browser OK"
