import errno
import json
import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

from rich.console import Console

console = Console()

_GLOBAL_ENV_FILE = Path.home() / ".config" / "coding-agent-devcontainer" / ".env"

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


def allocate_ports(start_port: int, count: int = 2) -> tuple[int, ...] | None:
    """Find `count` free ports by scanning upward from `start_port`.

    Returns the allocated ports in scan order or None if they cannot be found.
    """
    if count == 0:
        return ()
    if count < 0:
        raise ValueError("count must not be negative")

    available: list[int] = []
    for port in range(start_port, 65536):
        if check_port_availability(port):
            available.append(port)
            if len(available) == count:
                return tuple(available)
    return None


_LOCAL_ENV_PORT = re.compile(r"^\$\{localEnv:([^}:]+)(?::[^}]*)?\}:\d+$")


def _port_env_names(config: Path) -> list[str]:
    data = json.loads(config.read_text())
    app_ports = data.get("appPort") or []
    if isinstance(app_ports, str):
        app_ports = [app_ports]
    return [
        match.group(1)
        for app_port in app_ports
        if isinstance(app_port, str)
        for match in [_LOCAL_ENV_PORT.match(app_port)]
        if match is not None
    ]


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE .env file, ignoring blanks and comments.

    Returns an empty dict if the file does not exist.
    """
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        key = key.strip()
        if sep and key:
            env[key] = value.strip()
    return env


def resolve_env(
    workspace_path: str | Path,
    base_env: dict[str, str],
    global_env: Path = _GLOBAL_ENV_FILE,
) -> dict[str, str]:
    """Merge .env files into `base_env` for the devcontainer subprocess.

    Precedence (low to high): global file < project file < `base_env` (shell
    exports). Keys already present in `base_env` are never overwritten.

    Project file location: ``<workspace>/.devcontainer/.env``.
    Global file location: ``~/.config/coding-agent-devcontainer/.env``.
    """
    workspace = Path(workspace_path)
    project_env = load_env_file(workspace / ".devcontainer" / ".env")
    merged = load_env_file(global_env)

    result = base_env.copy()
    for source in (merged, project_env):
        for key, value in source.items():
            if key not in base_env:
                result[key] = value
    return result


def workspace_up(cmd: list[str], workspace_path: str, ssh_port: int) -> int:
    """Start the dev container for the given workspace.

    Injects environment variables for every generated appPort with dynamically
    allocated ports, then runs `devcontainer up`.
    """
    config = Path(workspace_path) / ".devcontainer" / "devcontainer.json"
    port_env_names = _port_env_names(config)
    ports = allocate_ports(ssh_port, len(port_env_names))
    if ports is None:
        console.print(f"[red]No available port found for SSH on {ssh_port}-65535[/red]")
        return 1

    env = resolve_env(workspace_path, os.environ.copy())
    for env_name, port in zip(port_env_names, ports):
        env[env_name] = str(port)
    assignments = ", ".join(f"{name}={port}" for name, port in zip(port_env_names, ports))
    console.print(f"Starting workspace with ports: {assignments or '(none)'}")

    return subprocess.run(
        cmd + ["up", "--workspace-folder", workspace_path, "--config", str(config)],
        env=env,
    ).returncode
