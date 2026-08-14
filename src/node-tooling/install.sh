#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
NPM_MIRROR="${NPM_MIRROR:-https://registry.npmmirror.com}"
PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION:-1.59.1}"

mkdir -p /usr/local/share/npm-global \
    /usr/local/share/pnpm-global \
    /ms-playwright
chown -R "$USERNAME":"$USERNAME" /usr/local/share /ms-playwright

cat > /etc/profile.d/zz-devcntainer-node.sh <<'EOF'
export NPM_CONFIG_PREFIX=/usr/local/share/npm-global
export PNPM_HOME=/usr/local/share/pnpm-global
export PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
export PATH=$PNPM_HOME:$NPM_CONFIG_PREFIX/bin:$PATH
EOF
chmod +x /etc/profile.d/zz-devcntainer-node.sh

su -l -s /bin/bash -c "
    export NPM_CONFIG_PREFIX=/usr/local/share/npm-global && \
    export PATH=/usr/local/share/npm-global/bin:\$PATH && \
    npm config set registry '${NPM_MIRROR}' && \
    npm install -g pnpm && \
    pnpm config set registry '${NPM_MIRROR}' && \
    npm cache clean --force && \
    pnpm store prune
" "$USERNAME"

PLAYWRIGHT_BROWSERS_PATH=/ms-playwright npx playwright@"${PLAYWRIGHT_VERSION}" install chromium
npm cache clean --force
