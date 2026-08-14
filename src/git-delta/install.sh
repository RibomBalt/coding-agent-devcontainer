#!/usr/bin/env bash
set -e

GIT_DELTA_VERSION="${GIT_DELTA_VERSION:-0.18.2}"

ARCH="$(dpkg --print-architecture)"
wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"
dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"
rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"
