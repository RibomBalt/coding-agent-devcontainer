#!/usr/bin/env bash
set -e

TZ="${TZ:-Asia/Shanghai}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.59.1}"

export TZ="$TZ"
export DEBIAN_FRONTEND=noninteractive

apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates

mv "$(dirname "$0")/debian-tuna.sources" /etc/apt/sources.list.d/debian.sources

apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    less \
    git \
    procps \
    sudo \
    fzf \
    zsh \
    man-db \
    unzip \
    gnupg2 \
    gh \
    iptables \
    ipset \
    iproute2 \
    dnsutils \
    aggregate \
    jq \
    nano \
    vim \
    python3 \
    python3-pip \
    openssh-server \
    fd-find \
    build-essential \
    ccache \
    ripgrep \
    rsync \
    tree \
    locales

npx playwright@"${PLAYWRIGHT_VERSION}" install-deps chromium
npm cache clean --force

echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen en_US.UTF-8
update-locale LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

USERNAME="${_REMOTE_USER:-node}"
usermod -s /bin/zsh "$USERNAME"

mkdir -p /workspace
chown -R "$USERNAME":"$USERNAME" /workspace

apt-get clean && rm -rf /var/lib/apt/lists/*
