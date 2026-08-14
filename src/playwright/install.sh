#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.59.1}"
PLAYWRIGHT_DOWNLOAD_HOST="${PLAYWRIGHT_DOWNLOAD_HOST:-}"

mkdir -p /ms-playwright
chown -R "$USERNAME":"$USERNAME" /ms-playwright

cat > /etc/profile.d/zz-devcntainer-playwright.sh <<'EOF'
export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
EOF
chmod +x /etc/profile.d/zz-devcntainer-playwright.sh

if [ -n "$PLAYWRIGHT_DOWNLOAD_HOST" ]; then
    export PLAYWRIGHT_DOWNLOAD_HOST
fi

# Install Chromium system dependencies (requires root + npx)
npx playwright@"${PLAYWRIGHT_VERSION}" install-deps chromium

# Install Chromium browser binaries into /ms-playwright
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright npx playwright@"${PLAYWRIGHT_VERSION}" install chromium

npm cache clean --force
apt-get clean && rm -rf /var/lib/apt/lists/*
