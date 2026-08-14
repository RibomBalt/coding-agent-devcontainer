#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"
PYPI_MIRROR="${PYPI_MIRROR:-https://pypi.tuna.tsinghua.edu.cn/simple}"

mkdir -p "$USER_HOME/.local" "$USER_HOME/.config/uv" "$USER_HOME/.cache/uv"
chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.local" "$USER_HOME/.config/uv" "$USER_HOME/.cache/uv"

cat > "$USER_HOME/.config/uv/uv.toml" <<EOF
[[index]]
url = "${PYPI_MIRROR}"
default = true
EOF

cat > /etc/profile.d/zz-devcntainer-uv.sh <<'EOF'
export PATH=$HOME/.local/bin:$PATH
EOF
chmod +x /etc/profile.d/zz-devcntainer-uv.sh

su -l -s /bin/bash -c "wget -qO- https://astral.sh/uv/install.sh | sh" "$USERNAME"

cat >> "$USER_HOME/.zshrc" <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
EOF

cat >> "$USER_HOME/.bashrc" <<'EOF'
export PATH="$HOME/.local/bin:$PATH"
EOF

chown -R "$USERNAME":"$USERNAME" "$USER_HOME/.config/uv" "$USER_HOME/.cache/uv" "$USER_HOME/.local"
