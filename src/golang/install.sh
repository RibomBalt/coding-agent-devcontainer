#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
GO_VERSION="${GO_VERSION:-1.26.5}"

mkdir -p "$USER_HOME/.local"
wget -O /tmp/golang.tar.gz "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz"
tar -C "$USER_HOME/.local" -xzf /tmp/golang.tar.gz
rm -f /tmp/golang.tar.gz

cat > /etc/profile.d/zz-devcntainer-go.sh <<'EOF'
export PATH=$PATH:$HOME/.local/go/bin:$HOME/go/bin
EOF
chmod +x /etc/profile.d/zz-devcntainer-go.sh

cat >> "$USER_HOME/.zshrc" <<'EOF'
export PATH="$PATH":$HOME/.local/go/bin
export PATH="$PATH":$HOME/go/bin
EOF

cat >> "$USER_HOME/.bashrc" <<'EOF'
export PATH="$PATH":$HOME/.local/go/bin
export PATH="$PATH":$HOME/go/bin
EOF

chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.local"

su -l -s /bin/bash -c "
    $USER_HOME/.local/go/bin/go env -w GO111MODULE=on && \
    $USER_HOME/.local/go/bin/go env -w GOPROXY=https://goproxy.cn,direct && \
    $USER_HOME/.local/go/bin/go env -w GOPATH=$USER_HOME/go
" "$USERNAME"
