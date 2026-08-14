#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
ZSH_IN_DOCKER_VERSION="${ZSH_IN_DOCKER_VERSION:-1.2.0}"

cat > /tmp/setup-zsh.sh <<EOF
#!/usr/bin/env bash
set -e
sh -c "\$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \\
  -p git \\
  -p fzf \\
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \\
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \\
  -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \\
  -x
EOF

chmod +x /tmp/setup-zsh.sh
chown "$USERNAME":"$USERNAME" /tmp/setup-zsh.sh
su -l -s /bin/bash -c "bash /tmp/setup-zsh.sh" "$USERNAME"
rm -f /tmp/setup-zsh.sh
