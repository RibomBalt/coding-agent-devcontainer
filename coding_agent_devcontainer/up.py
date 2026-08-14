import errno
import os
import shutil
import socket
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

DEVCONTAINER_CMD = [
    ["devcontainer"],
    ["npx", "@devcontainers/cli"],
    ["pnpx", "@devcontainers/cli"],
    ["bun", "x", "@devcontainers/cli"],
    ["bunx", "@devcontainers/cli"],
]


def check_cli() -> list[str] | None:
    """Detect an available devcontainer CLI (devcontainer/npx/pnpx/bunx)."""
    for cmd in DEVCONTAINER_CMD:
        if shutil.which(cmd[0]):
            return cmd
    return None


def check_port_availability(port: int) -> bool:
    """Return True if the given localhost port is free."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("localhost", port))
        sock.close()
        return True
    except socket.error as exc:
        if exc.errno == errno.EADDRINUSE:
            return False
        raise


def allocate_ports(ssh_port: int) -> tuple[int, int] | None:
    """Find two consecutive free ports starting from `ssh_port`.

    Returns (ssh_port, opencode_port) or None if not found.
    """
    available: list[int] = []
    for port in range(ssh_port, 65536):
        if check_port_availability(port):
            available.append(port)
            if len(available) == 2:
                return available[0], available[1]
    return None


def workspace_up(cmd: list[str], workspace_path: str, ssh_port: int) -> int:
    """Start the dev container for the given workspace.

    Injects DEVCONTAINER_SSH_PORT / DEVCONTAINER_OPCD_PORT with two dynamically
    allocated ports, then runs `devcontainer up`.
    """
    ports = allocate_ports(ssh_port)
    if ports is None:
        console.print(f"[red]No available port found for SSH on {ssh_port}-65535[/red]")
        return 1

    ssh_final_port, opencode_final_port = ports
    config = Path(workspace_path) / ".devcontainer" / "devcontainer.json"

    env = os.environ.copy()
    env["DEVCONTAINER_SSH_PORT"] = str(ssh_final_port)
    env["DEVCONTAINER_OPCD_PORT"] = str(opencode_final_port)
    console.print(
        f"Starting workspace with SSH port {ssh_final_port} "
        f"and Opencode port {opencode_final_port}"
    )

    return subprocess.run(
        cmd + ["up", "--workspace-folder", workspace_path, "--config", str(config)],
        env=env,
    ).returncode
