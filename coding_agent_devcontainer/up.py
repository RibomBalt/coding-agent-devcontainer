import errno
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

from .render import workspace_mount_spec

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


def parse_port_mapping(value: str) -> str:
    """Validate and normalize a HOST_PORT:CONTAINER_PORT mapping."""
    parts = value.split(":")
    if len(parts) != 2 or not all(part.isdecimal() for part in parts):
        raise ValueError("端口映射格式应为 HOST_PORT:CONTAINER_PORT，例如 8080:80")
    host_port, container_port = (int(part) for part in parts)
    if not (1 <= host_port <= 65535 and 1 <= container_port <= 65535):
        raise ValueError("端口必须在 1..65535 范围内")
    return f"{host_port}:{container_port}"


def parse_workspace_mount_target(value: str) -> str:
    """Validate an absolute container path for the workspace mount target."""
    target = value.rstrip("/")
    if not target.startswith("/") or not target or "," in target:
        raise ValueError(
            "workspace mount target must be an absolute path other than / without commas"
        )
    return target


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


def _devcontainer_host_ports(workspace_path: str | Path) -> tuple[set[int], set[int]]:
    """Return host ports used by other workspaces and by this workspace."""
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
            ["docker", "inspect", *containers],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        console.print(f"[yellow]无法读取已有 Dev Container 端口映射：{exc}[/yellow]")
        return set(), set()

    reserved_ports: set[int] = set()
    workspace_ports: set[int] = set()
    try:
        inspected_containers = json.loads(inspected.stdout)
    except json.JSONDecodeError:
        return reserved_ports, workspace_ports
    current_workspace = Path(workspace_path).resolve()
    for container in inspected_containers:
        labels = (container.get("Config") or {}).get("Labels") or {}
        local_folder = labels.get("devcontainer.local_folder")
        belongs_to_workspace = bool(
            local_folder and Path(local_folder).resolve() == current_workspace
        )
        bindings = (container.get("HostConfig") or {}).get("PortBindings")
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
                        if belongs_to_workspace:
                            workspace_ports.add(port)
                        else:
                            reserved_ports.add(port)
    return reserved_ports, workspace_ports


def _workspace_ssh_port(workspace_path: str | Path, env: dict[str, str]) -> int | None:
    """Return the published host port for SSH on this workspace's running container."""
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
            env=env,
        ).stdout.split()
        if not containers:
            return None

        inspected = subprocess.run(
            ["docker", "inspect", *containers],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    try:
        inspected_containers = json.loads(inspected.stdout)
    except json.JSONDecodeError:
        return None

    current_workspace = Path(workspace_path).resolve()
    host_ports: set[int] = set()
    for container in inspected_containers:
        labels = (container.get("Config") or {}).get("Labels") or {}
        local_folder = labels.get("devcontainer.local_folder")
        if not local_folder or Path(local_folder).resolve() != current_workspace:
            continue
        if not (container.get("State") or {}).get("Running"):
            continue

        bindings = (container.get("NetworkSettings") or {}).get("Ports") or {}
        for binding in bindings.get("2222/tcp") or []:
            host_port = binding.get("HostPort") if isinstance(binding, dict) else None
            if isinstance(host_port, str) and host_port.isdigit():
                port = int(host_port)
                if 1 <= port <= 65535:
                    host_ports.add(port)

    return next(iter(host_ports)) if len(host_ports) == 1 else None


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
    add_ports: list[str] | None = None,
    workspace_mount_target: str | None = None,
) -> int:
    """Start the dev container for the given workspace.

    Injects environment variables for every generated appPort with dynamically
    allocated ports, then runs `devcontainer up`. Additional fixed mappings in
    `add_ports` are applied through a temporary override config. When
    force_recreate is true, the configured base image is pulled and feature
    lockfile updated before the existing container is removed for an uncached
    rebuild.
    """
    config = Path(workspace_path) / ".devcontainer" / "devcontainer.json"
    config_data = json.loads(config.read_text())
    if workspace_mount_target is not None:
        workspace_mount_target = parse_workspace_mount_target(workspace_mount_target)
    add_ports = [parse_port_mapping(port) for port in (add_ports or [])]
    added_host_port_list = [int(port.split(":", maxsplit=1)[0]) for port in add_ports]
    added_host_ports = set(added_host_port_list)
    if len(added_host_ports) != len(added_host_port_list):
        console.print("[red]多个 --add-port 不能使用相同的宿主机端口[/red]")
        return 1

    app_ports = config_data.get("appPort") or []
    if isinstance(app_ports, (str, int)):
        app_ports = [app_ports]
    if not isinstance(app_ports, list):
        console.print("[red]devcontainer.json 中的 appPort 必须是字符串、整数或列表[/red]")
        return 1
    configured_host_ports: set[int] = set()
    for app_port in app_ports:
        if isinstance(app_port, int) and not isinstance(app_port, bool):
            configured_host_ports.add(app_port)
        elif isinstance(app_port, str):
            match = re.fullmatch(r"(\d+)(?::\d+)?", app_port)
            if match:
                configured_host_ports.add(int(match.group(1)))
    if added_host_ports & configured_host_ports:
        console.print("[red]--add-port 与 devcontainer.json 中的 appPort 宿主机端口重复[/red]")
        return 1

    port_env_names = _port_env_names(config)
    reserved_ports, workspace_ports = _devcontainer_host_ports(workspace_path)
    occupied_added_ports = any(
        port in reserved_ports
        or (port not in workspace_ports and not check_port_availability(port))
        for port in added_host_ports
    )
    if occupied_added_ports:
        console.print("[red]指定的 --add-port 宿主机端口已被占用或已有开发容器预留[/red]")
        return 1
    ports = allocate_ports(
        ssh_port,
        len(port_env_names),
        reserved_ports | configured_host_ports | added_host_ports,
    )
    if ports is None:
        console.print(f"[red]No available port found for SSH on {ssh_port}-65535[/red]")
        return 1

    env = resolve_env(workspace_path, os.environ.copy())
    for env_name, port in zip(port_env_names, ports):
        env[env_name] = str(port)
    up_args = ["up", "--workspace-folder", workspace_path, "--config", str(config)]
    if force_recreate:
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

    override_path: Path | None = None
    override: dict[str, object] = {}
    if add_ports:
        override["appPort"] = [*app_ports, *add_ports]
    if workspace_mount_target:
        override["workspaceMount"] = workspace_mount_spec(workspace_mount_target)
        override["workspaceFolder"] = workspace_mount_target
    if override:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config.parent,
            prefix=".devcontainer-override-",
            suffix=".json",
            delete=False,
        ) as temp_config:
            json.dump(override, temp_config, ensure_ascii=False, indent=2)
            temp_config.write("\n")
            override_path = Path(temp_config.name)
        up_args.extend(["--override-config", str(override_path)])

    try:
        result = subprocess.run(
            cmd + up_args,
            env=env,
        )
        if result.returncode == 0:
            actual_ssh_port = _workspace_ssh_port(workspace_path, env)
            if actual_ssh_port is None:
                console.print("[yellow]未能确认实际 SSH 端口[/yellow]")
            else:
                console.print(f"SSH 实际端口: {actual_ssh_port}")
        return result.returncode
    finally:
        if override_path is not None:
            override_path.unlink(missing_ok=True)
