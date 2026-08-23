#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
PYPI_MIRROR="${PYPI_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"

mkdir -p "$USER_HOME/.local" "$USER_HOME/.config/uv" "$USER_HOME/.cache/uv"

cat > "$USER_HOME/.config/uv/uv.toml" <<EOF
[[index]]
url = "${PYPI_MIRROR}"
default = true
EOF

wget -qO- https://astral.sh/uv/install.sh | sh

cat >> "$USER_HOME/.zshrc" <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
EOF

cat >> "$USER_HOME/.bashrc" <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
EOF
