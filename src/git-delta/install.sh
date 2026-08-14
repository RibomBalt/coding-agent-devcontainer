#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"
GIT_DELTA_VERSION="${GIT_DELTA_VERSION:-0.18.2}"

ARCH="$(dpkg --print-architecture)"
wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"
dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"
rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

su -l -s /bin/bash -c \
    "git config --global core.pager delta && \
     git config --global interactive.diffFilter \"delta --color-only\" && \
     git config --global delta.navigate true" \
    "$USERNAME"
