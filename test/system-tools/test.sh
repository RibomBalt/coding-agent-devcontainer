#!/usr/bin/env bash
set -e

echo "==> Verifying system-tools feature"

command -v zsh || exit 1
command -v git || exit 1
command -v vim || exit 1
command -v fzf || exit 1
command -v rg || exit 1
command -v jq || exit 1
command -v gh || exit 1
command -v iptables || exit 1
command -v ipset || exit 1
command -v /usr/sbin/sshd || exit 1

grep -q "en_US.UTF-8" /etc/locale.gen || exit 1

echo "✓ system-tools OK"
