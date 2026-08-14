#!/usr/bin/env python3
import argparse
import errno
import os
import shutil
import socket
import subprocess
from pathlib import Path

DEVCONTAINER_CMD = [
    ["devcontainer"],
    ["npx", "@devcontainers/cli"],
    ["pnpx", "@devcontainers/cli"],
    ["bun", "x", "@devcontainers/cli"],
    ["bunx", "@devcontainers/cli"],
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


def resolve_config(workspace_path, gpus=True):
    """
    Prefer the project-local `.devcontainer/devcontainer.json`; fall back to the
    repository-level gpu/nogpu configs when the project has not migrated yet.
    """
    local_config = Path(workspace_path) / ".devcontainer" / "devcontainer.json"
    if local_config.exists():
        return str(local_config)
    if gpus:
        return str(PROJ_ROOT / "gpu/devcontainer.json")
    return str(PROJ_ROOT / "nogpu/devcontainer.json")


def workspace_up(cmd, workspace_path, gpus=True, ssh_port=40022):
    """
    DEVCONTAINER_SSH_PORT=<ssh_port> devcontainer up --workspace-folder <workspace_path> --config <config>
    """
    config = resolve_config(workspace_path, gpus)

    available_ports = []
    for port in range(ssh_port, 65536):
        if check_port_availablity(port):
            available_ports.append(port)
            if len(available_ports) == 2:
                break
    else:
        print(f"No available port found for SSH on {ssh_port}-65535")
        return None, None
    ssh_final_port = available_ports[0]
    opencode_final_port = available_ports[1]

    env = os.environ.copy()
    env["DEVCONTAINER_SSH_PORT"] = str(ssh_final_port)
    env["DEVCONTAINER_OPCD_PORT"] = str(opencode_final_port)
    print(
        f"Starting workspace with SSH port {ssh_final_port} and Opencode port {opencode_final_port}"
    )

    pid = subprocess.run(
        cmd + ["up", "--workspace-folder", workspace_path, "--config", config], env=env
    )
    return pid, {"ssh": ssh_final_port, "opencode": opencode_final_port}


def main():
    parser = argparse.ArgumentParser(description="Start a devcontainer workspace")
    parser.add_argument("-w", "--workspace-path", help="Path to the workspace folder")
    parser.add_argument(
        "--gpus", action="store_true", help="Enable GPU support", default=False
    )
    parser.add_argument(
        "-p", "--port", "--ssh-port", type=int, default=40022, help="SSH port to use"
    )

    args = parser.parse_args()
    if not args.workspace_path:
        parser.error("Workspace path is required")

    config = resolve_config(args.workspace_path, args.gpus)
    print(f"Using config: {config}")

    cmd = check_npx_availablity()
    if not cmd:
        print("No devcontainer CLI found.")
        return
    print(f"Using devcontainer CLI: {cmd[0]}")
    pid, _ = workspace_up(cmd, args.workspace_path, args.gpus, args.port)
    if pid:
        print("Workspace up")
    else:
        print("Failed to start workspace")


if __name__ == "__main__":
    main()
