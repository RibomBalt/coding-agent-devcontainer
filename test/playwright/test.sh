#!/usr/bin/env bash
set -e

echo "==> Verifying playwright feature"

test -d /ms-playwright || exit 1
find /ms-playwright -maxdepth 1 -name "chromium-*" -type d | grep -q . || exit 1

echo "✓ playwright OK"
