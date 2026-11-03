#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
AGENT_BROWSER_VERSION="${AGENT_BROWSER_VERSION:-latest}"
FEATURE_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$USER_HOME/.agent-browser"
chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.agent-browser"

# Save the selected version for the postCreate hook, which runs after the
# pnpm-global volume is mounted.
install -d -m 0755 /usr/local/share/agent-browser
printf '%s\n' "$AGENT_BROWSER_VERSION" > /usr/local/share/agent-browser/version
chmod 0644 /usr/local/share/agent-browser/version

ln -sfn /usr/local/share/pnpm-global/bin/agent-browser /usr/local/bin/agent-browser
install -m 0755 "$FEATURE_DIR/install-chromium.sh" /usr/local/bin/agent-browser-install-chromium
install -m 0755 "$FEATURE_DIR/setup.sh" /usr/local/bin/agent-browser-setup

# Keep these packages aligned with `agent-browser install --with-deps` for
# Debian. That command also downloads Chrome, so the browser is installed by
# postCreateCommand after the named cache volume has been mounted.
apt-get update && apt-get install -y --no-install-recommends \
    libxcb-shm0 \
    libx11-xcb1 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxrandr2 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libgtk-3-0t64 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libatk1.0-0t64 \
    libcairo-gobject2 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libxrender1 \
    libasound2t64 \
    libfreetype6 \
    libfontconfig1 \
    libdbus-1-3 \
    libnss3 \
    libnss3-tools \
    libnspr4 \
    libatk-bridge2.0-0t64 \
    libdrm2 \
    libxkbcommon0 \
    libatspi2.0-0t64 \
    libcups2t64 \
    libxshmfence1 \
    libgbm1 \
    fonts-noto-color-emoji \
    fonts-noto-cjk \
    fonts-freefont-ttf

apt-get clean && rm -rf /var/lib/apt/lists/*
