#!/usr/bin/env bash
set -e

USERNAME="${_REMOTE_USER:-node}"
USER_HOME="${_REMOTE_USER_HOME:-$(getent passwd "$USERNAME" | cut -d: -f6)}"

# Pi data / config directory
mkdir -p \
    "$USER_HOME/.pi"

chown -R "$USERNAME":"$USERNAME" \
    "$USER_HOME/.pi"

# Override git identity with the Pi identity
su -l -s /bin/bash -c \
    "git config --global user.name 'pi' && git config --global user.email 'pi@openai.com'" \
    "$USERNAME"
