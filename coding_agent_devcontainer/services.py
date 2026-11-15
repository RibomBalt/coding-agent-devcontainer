"""Discover and connect to dev container services managed by this CLI."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .constants import MANAGED_CONTAINER_LABEL

MANAGED_LABEL = MANAGED_CONTAINER_LABEL
WORKSPACE_LABEL = "devcontainer.local_folder"


@dataclass(frozen=True)
class Service:
    container_id: str
    name: str
    workspace: str
    running: bool
    mount_target: str | None
    ssh_port: int | None
    managed: bool


def discover_services() -> list[Service]:
    """Return containers associated with a workspace, including stopped legacy ones."""
    result = subprocess.run(
        ["docker", "ps", "--all", "--quiet", "--filter", f"label={WORKSPACE_LABEL}"],
        capture_output=True,
        text=True,
        check=True,
    )
    container_ids = result.stdout.split()
    if not container_ids:
        return []

    inspected = subprocess.run(
        ["docker", "inspect", *container_ids],
        capture_output=True,
        text=True,
        check=True,
    )
    records = json.loads(inspected.stdout)
    services = []
    for record in records:
        config = record.get("Config") or {}
        labels = config.get("Labels") or {}
        workspace = labels.get(WORKSPACE_LABEL)
        if not workspace:
            continue

        state = record.get("State") or {}
        running = bool(state.get("Running"))
        mounts = record.get("Mounts") or []
        mount_targets = [
            mount.get("Destination")
            for mount in mounts
            if mount.get("Type") == "bind"
            and mount.get("Source")
            and _same_path(mount.get("Source"), workspace)
        ]
        port_bindings = (record.get("NetworkSettings") or {}).get("Ports") or {}
        host_ports = {
            int(binding["HostPort"])
            for binding in port_bindings.get("2222/tcp") or []
            if isinstance(binding, dict)
            and str(binding.get("HostPort", "")).isdigit()
            and 1 <= int(binding["HostPort"]) <= 65535
        }
        services.append(
            Service(
                container_id=record.get("Id", ""),
                name=(record.get("Name") or "").lstrip("/"),
                workspace=str(Path(workspace).expanduser().resolve()),
                running=running,
                mount_target=mount_targets[0] if len(mount_targets) == 1 else None,
                ssh_port=next(iter(host_ports)) if len(host_ports) == 1 else None,
                managed=labels.get(MANAGED_LABEL) == "true",
            )
        )
    return sorted(services, key=lambda service: (service.workspace.casefold(), service.name))


def _same_path(first: str | None, second: str) -> bool:
    if not first:
        return False
    try:
        return Path(first).expanduser().resolve() == Path(second).expanduser().resolve()
    except (OSError, RuntimeError):
        return first == second


def connect_service(service: Service) -> int:
    """Open an interactive shell in a running service container."""
    if not service.running:
        raise ValueError("服务当前不在线")
    command = [
        "docker",
        "exec",
        "--interactive",
        "--tty",
        "--user",
        "node",
    ]
    for variable in ("TERM", "COLORTERM"):
        value = os.environ.get(variable)
        if value:
            command.extend(["--env", f"{variable}={value}"])
    command.extend([service.container_id, "zsh"])
    return subprocess.run(command, check=False).returncode
