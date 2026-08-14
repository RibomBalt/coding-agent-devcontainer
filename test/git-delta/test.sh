#!/usr/bin/env bash
set -e

echo "==> Verifying git-delta feature"

command -v delta || exit 1

echo "✓ git-delta OK"
