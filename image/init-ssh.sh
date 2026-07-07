#!/bin/bash
set -e
SSH_HOME=/home/node/.ssh
SSH_PORT=2222

mount_ssh_key () {
    # authorized_keys
    if test -f /ssh-auth-key.pub && test ! -d /ssh-auth-key.pub; then
        AUTH_KEY=$(awk '{print $2}' /ssh-auth-key.pub | head -n1)
        if grep -q "$AUTH_KEY" "$SSH_HOME/authorized_keys"; then
            echo "SSH auth key already exists, skipping setup"
        else
            echo "$(head -n1 /ssh-auth-key.pub)" >> "$SSH_HOME/authorized_keys"
            echo "SSH auth key mounted from /ssh-auth-key.pub. sha256: $(sha256sum /ssh-auth-key.pub)"
        fi
    fi

    # host_ssh_key
    if test ! -f "$SSH_HOME/host_ssh_key/ssh_host_rsa_key"; then
        ssh-keygen -t rsa -f $SSH_HOME/host_ssh_key/ssh_host_rsa_key -N "" && chmod 600 $SSH_HOME/host_ssh_key/ssh_host_rsa_key
        echo "SSH host key generated"
    else
        echo "SSH host key already exists, skipping generation"
    fi
}

start_ssh_server () {
    /usr/sbin/sshd -p $SSH_PORT -h $SSH_HOME/host_ssh_key/ssh_host_rsa_key -o AuthorizedKeysFile=$SSH_HOME/authorized_keys
    echo "SSH server started"
}

mount_ssh_key
start_ssh_server
