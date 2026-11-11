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


def allocate_ports(
    start_port: int,
    count: int = 2,
    reserved_ports: set[int] | None = None,
) -> tuple[int, ...] | None:
    """Find `count` free ports by scanning upward from `start_port`.

    Returns the allocated ports in scan order or None if they cannot be found.
    """
    if count == 0:
        return ()
    if count < 0:
        raise ValueError("count must not be negative")

    reserved_ports = reserved_ports or set()
    available: list[int] = []
    for port in range(start_port, 65536):
        if port not in reserved_ports and check_port_availability(port):
            available.append(port)
            if len(available) == count:
                return tuple(available)
    return None


def _devcontainer_reserved_ports() -> set[int]:
    """Return host ports reserved by existing Dev Container containers."""
    try:
        containers = subprocess.run(
            [
                "docker",
                "ps",
                "--all",
                "--quiet",
                "--filter",
                "label=devcontainer.local_folder",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        if not containers:
            return set()

        inspected = subprocess.run(
            ["docker", "inspect", "--format={{json .HostConfig.PortBindings}}", *containers],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        console.print(f"[yellow]无法读取已有 Dev Container 端口映射：{exc}[/yellow]")
        return set()

    ports: set[int] = set()
    for raw_bindings in inspected.stdout.splitlines():
        try:
            bindings = json.loads(raw_bindings)
        except json.JSONDecodeError:
            continue
        if not isinstance(bindings, dict):
            continue
        for host_bindings in bindings.values():
            if not isinstance(host_bindings, list):
                continue
            for binding in host_bindings:
                if not isinstance(binding, dict):
                    continue
                host_port = binding.get("HostPort")
                if isinstance(host_port, str) and host_port.isdigit():
                    port = int(host_port)
                    if 1 <= port <= 65535:
                        ports.add(port)
    return ports


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


def workspace_up(
    cmd: list[str],
    workspace_path: str,
    ssh_port: int,
    force_recreate: bool = False,
) -> int:
    """Start the dev container for the given workspace.

    Injects environment variables for every generated appPort with dynamically
    allocated ports, then runs `devcontainer up`. When force_recreate is true,
    the configured base image is pulled and feature lockfile updated before
    the existing container is removed for an uncached rebuild.
    """
    config = Path(workspace_path) / ".devcontainer" / "devcontainer.json"
    port_env_names = _port_env_names(config)
    reserved_ports = _devcontainer_reserved_ports()
    ports = allocate_ports(ssh_port, len(port_env_names), reserved_ports)
    if ports is None:
        console.print(f"[red]No available port found for SSH on {ssh_port}-65535[/red]")
        return 1

    env = resolve_env(workspace_path, os.environ.copy())
    for env_name, port in zip(port_env_names, ports):
        env[env_name] = str(port)
    assignments = ", ".join(f"{name}={port}" for name, port in zip(port_env_names, ports))
    console.print(f"Starting workspace with ports: {assignments or '(none)'}")

    up_args = ["up", "--workspace-folder", workspace_path, "--config", str(config)]
    if force_recreate:
        config_data = json.loads(config.read_text())
        image = config_data.get("image")
        if image:
            console.print(f"Pulling latest base image: {image}")
            pull_result = subprocess.run(["docker", "pull", image], env=env)
            if pull_result.returncode != 0:
                return pull_result.returncode

        if config_data.get("features"):
            console.print("Upgrading feature lockfile to the latest allowed versions")
            upgrade_result = subprocess.run(
                cmd + ["upgrade", "--workspace-folder", workspace_path, "--config", str(config)],
                env=env,
            )
            if upgrade_result.returncode != 0:
                return upgrade_result.returncode

        up_args.extend(["--remove-existing-container", "--build-no-cache"])

    return subprocess.run(
        cmd + up_args,
        env=env,
    ).returncode
