#!/bin/bash
set -e

echo $(cat /ssh-auth-key.pub) > ~/.ssh/authorized_keys
if test ! -f "/home/node/.ssh/host_ssh_key/ssh_host_rsa_key"; then
    ssh-keygen -t rsa -f ~/.ssh/host_ssh_key/ssh_host_rsa_key -N "" && chmod 600 ~/.ssh/host_ssh_key/ssh_host_rsa_key
fi
