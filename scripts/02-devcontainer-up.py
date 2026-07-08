#!/usr/bin/env python3
import argparse
import subprocess
import os
import shutil
import socket
import errno
from pathlib import Path

DEVCONTAINER_CMD = [
    ["devcontainer"],
    ["npx", "@devcontainers/cli"],
    ["pnpx", "@devcontainers/cli"],
    ["bun", "x", "@devcontainers/cli"],
    ["bunx", "@devcontainers/cli"]
]

PROJ_ROOT = Path(__file__).parent.parent

def check_npx_availablity():
    """
    check: devcontainer, npx, pnpx, bun, bunx
    """
    for cmd in DEVCONTAINER_CMD:
        if shutil.which(cmd[0]):
            return cmd
    return None

def check_port_availablity(port):
    """
    Check if the port is available on the local machine.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("localhost", port))
        sock.close()
        return True
    except socket.error as e:
        if e.errno == errno.EADDRINUSE:
            return False
        raise

def workspace_up(cmd, workspace_path, gpus=True, ssh_port=50022):
    """
     DEVCONTAINER_SSH_PORT=<ssh_port> devcontainer up --workspace-folder <workspace_path> --config <gpu/devcontainer.json|nogpu/devcontainer.json>
    """
    if gpus:
        config = str(PROJ_ROOT / "gpu/devcontainer.json")
    else:
        config = str(PROJ_ROOT / "nogpu/devcontainer.json")

    for port in range(ssh_port, 65536):
        if check_port_availablity(port):
            env = os.environ.copy()
            env["DEVCONTAINER_SSH_PORT"] = str(port)
            pid = subprocess.run(cmd + ["up", "--workspace-folder", workspace_path, "--config", config], env=env)
            return pid, port

    print(f"No available port found for SSH on {ssh_port}-65535")
    return None, None

def main():
    parser = argparse.ArgumentParser(description="Start a devcontainer workspace")
    parser.add_argument("-w", "--workspace-path", help="Path to the workspace folder")
    parser.add_argument("--gpus", action="store_true", help="Enable GPU support", default=False)
    parser.add_argument("-p", "--port", "--ssh-port", type=int, default=50022, help="SSH port to use")

    args = parser.parse_args()
    if not args.workspace_path:
        parser.error("Workspace path is required")

    if not args.gpus:
        config = "nogpu/devcontainer.json"
    else:
        config = "gpu/devcontainer.json"
    print(f"Using config: {config}")

    cmd = check_npx_availablity()
    if not cmd:
        print("No devcontainer CLI found.")
        return
    print(f"Using devcontainer CLI: {cmd[0]}")
    pid, port = workspace_up(cmd, args.workspace_path, args.gpus, args.port)
    if pid:
        print(f"Workspace up on port {port}")
    else:
        print("Failed to start workspace")

if __name__ == "__main__":
    main()
