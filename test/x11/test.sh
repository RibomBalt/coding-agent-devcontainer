#!/usr/bin/env bash
set -euo pipefail

echo "==> Verifying X11 feature and SSH X11 forwarding"

USERNAME="${_REMOTE_USER:-node}"

for command in ssh ssh-keygen ssh-keyscan sshd xauth xsel Xvfb xclock xwd; do
    command -v "$command" >/dev/null || {
        echo "Required command not found: $command" >&2
        exit 1
    }
done

TMP_DIR="$(mktemp -d)"
XVFB_PID=""
USERNAME_HOME="$(getent passwd "$USERNAME" | cut -d: -f6)"
SSH_HOME="$USERNAME_HOME/.ssh"
AUTHORIZED_KEYS="$SSH_HOME/authorized_keys"
XAUTHORITY_FILE="$USERNAME_HOME/.Xauthority"
HAD_AUTHORIZED_KEYS=false
HAD_XAUTHORITY=false

if [ -f "$AUTHORIZED_KEYS" ]; then
    cp "$AUTHORIZED_KEYS" "$TMP_DIR/original_authorized_keys"
    HAD_AUTHORIZED_KEYS=true
fi
if [ -e "$XAUTHORITY_FILE" ] || [ -L "$XAUTHORITY_FILE" ]; then
    cp -a "$XAUTHORITY_FILE" "$TMP_DIR/original_Xauthority"
    HAD_XAUTHORITY=true
fi

cleanup() {
    if [ -n "$XVFB_PID" ]; then
        kill "$XVFB_PID" 2>/dev/null || true
        wait "$XVFB_PID" 2>/dev/null || true
    fi
    if [ "$HAD_AUTHORIZED_KEYS" = true ]; then
        cp "$TMP_DIR/original_authorized_keys" "$AUTHORIZED_KEYS"
    else
        rm -f "$AUTHORIZED_KEYS"
    fi
    if [ "$HAD_XAUTHORITY" = true ]; then
        cp -a "$TMP_DIR/original_Xauthority" "$XAUTHORITY_FILE"
    else
        rm -f "$XAUTHORITY_FILE"
    fi
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

ssh-keygen -q -t ed25519 -N "" -f "$TMP_DIR/client_key"
install -d -m 700 "$SSH_HOME"
touch "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS"
cat "$TMP_DIR/client_key.pub" >> "$AUTHORIZED_KEYS"

"$USERNAME_HOME/.local/bin/init-ssh.sh"
test "$(sshd -T -h "$SSH_HOME/host_ssh_key/ssh_host_rsa_key" | awk '$1 == "x11forwarding" {print $2; exit}')" = yes
test "$(sshd -T -h "$SSH_HOME/host_ssh_key/ssh_host_rsa_key" | awk '$1 == "x11uselocalhost" {print $2; exit}')" = yes
test "$(sshd -T -h "$SSH_HOME/host_ssh_key/ssh_host_rsa_key" | awk '$1 == "xauthlocation" {print $2; exit}')" = /usr/bin/xauth

XAUTHORITY="$TMP_DIR/Xauthority"
touch "$XAUTHORITY"
chmod 600 "$XAUTHORITY"
XAUTH_COOKIE="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
DISPLAY_NUMBER=""
for candidate in $(seq 99 119); do
    if [ ! -e "/tmp/.X${candidate}-lock" ] && [ ! -S "/tmp/.X11-unix/X${candidate}" ]; then
        DISPLAY_NUMBER="$candidate"
        break
    fi
done
test -n "$DISPLAY_NUMBER"
export DISPLAY=":$DISPLAY_NUMBER"
export XAUTHORITY
xauth -f "$XAUTHORITY" add "$DISPLAY" MIT-MAGIC-COOKIE-1 "$XAUTH_COOKIE"
touch "$XAUTHORITY_FILE"
chmod 600 "$XAUTHORITY_FILE"
Xvfb "$DISPLAY" -auth "$XAUTHORITY" -screen 0 640x480x24 -nolisten tcp \
    >"$TMP_DIR/xvfb.log" 2>&1 &
XVFB_PID=$!
for _ in $(seq 1 50); do
    if xwd -root -silent -out /dev/null >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done
xwd -root -silent -out /dev/null >/dev/null 2>&1

for _ in $(seq 1 50); do
    if ssh-keyscan -p 2222 127.0.0.1 >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

ssh -X -i "$TMP_DIR/client_key" -p 2222 \
    -o BatchMode=yes -o ConnectTimeout=5 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR \
    "$USERNAME@127.0.0.1" \
    "timeout 2 xclock; xclock_status=\$?; test \"\$xclock_status\" -eq 124"

echo "✓ X11 forwarding works over ssh -X"
