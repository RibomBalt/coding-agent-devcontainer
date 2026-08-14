#!/usr/bin/env bash
set -e

echo "==> Verifying git-delta feature"

command -v delta || exit 1
git config --global core.pager | grep -qx delta || exit 1
git config --global interactive.diffFilter | grep -qx "delta --color-only" || exit 1
git config --global delta.navigate | grep -qx true || exit 1

echo "✓ git-delta OK"
