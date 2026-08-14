#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"

cat > "$USER_HOME/.vimrc" <<'VIMRC'
set number
set tabstop=4
set shiftwidth=4
set expandtab
set autoindent
set smartindent
set cursorline
set encoding=utf-8
set fileencoding=utf-8
syntax on
set mouse=a
VIMRC

mkdir -p \
    "$USER_HOME/.cache/uv" \
    "$USER_HOME/.local/share/opencode" \
    "$USER_HOME/.config/opencode" \
    "$USER_HOME/.cache/opencode" \
    "$USER_HOME/.geant4_pybind"

mkdir -p /commandhistory
touch /commandhistory/.bash_history

su -l -s /bin/bash -c \
    "git config --global user.name 'opencode' && git config --global user.email 'dev@opencode.ai'" \
    "$USERNAME"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.vimrc" \
    "$USER_HOME/.cache" \
    "$USER_HOME/.local/share/opencode" \
    "$USER_HOME/.config/opencode" \
    "$USER_HOME/.geant4_pybind" \
    /commandhistory
