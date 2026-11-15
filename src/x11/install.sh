#!/usr/bin/env bash
set -e

apt-get update
apt-get install -y --no-install-recommends \
    xauth \
    xsel \
    x11-apps \
    xvfb

install -d -m 0755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/99-x11-forwarding.conf <<'EOF'
X11Forwarding yes
X11UseLocalhost yes
XAuthLocation /usr/bin/xauth
EOF

apt-get clean
rm -rf /var/lib/apt/lists/*
