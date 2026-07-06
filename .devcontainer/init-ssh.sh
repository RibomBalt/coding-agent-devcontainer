#!/bin/bash
set -e
SSH_HOME=/home/node/.ssh
echo $(cat /ssh-auth-key.pub) > $SSH_HOME/authorized_keys
if test ! -f "$SSH_HOME/host_ssh_key/ssh_host_rsa_key"; then
    ssh-keygen -t rsa -f $SSH_HOME/host_ssh_key/ssh_host_rsa_key -N "" && chmod 600 $SSH_HOME/host_ssh_key/ssh_host_rsa_key
fi
