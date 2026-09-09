import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PortMapping:
    env: str
    container_port: int
    default_host_port: int

    def render(self) -> str:
        return f"${{localEnv:{self.env}:{self.default_host_port}}}:{self.container_port}"


BASE_PORTS = (PortMapping("DEVCONTAINER_SSH_PORT", 2222, 40022),)


def load_feature_ports(path: Path) -> tuple[PortMapping, ...]:
    """Load an optional feature-local ports.json sidecar."""
    if not path.exists():
        return ()

    data = json.loads(path.read_text())
    raw_ports = data.get("ports", [])
    if not isinstance(raw_ports, list):
        raise ValueError(f"Invalid ports configuration in {path}: ports must be a list")

    mappings = []
    for raw_port in raw_ports:
        if not isinstance(raw_port, dict):
            raise ValueError(f"Invalid port entry in {path}: expected an object")
        env = raw_port.get("env")
        container_port = raw_port.get("containerPort")
        default_host_port = raw_port.get("defaultHostPort")
        if (
            not isinstance(env, str)
            or not env
            or not isinstance(container_port, int)
            or isinstance(container_port, bool)
            or not isinstance(default_host_port, int)
            or isinstance(default_host_port, bool)
        ):
            raise ValueError(f"Invalid port entry in {path}: {raw_port!r}")
        mappings.append(PortMapping(env, container_port, default_host_port))
    return tuple(mappings)
