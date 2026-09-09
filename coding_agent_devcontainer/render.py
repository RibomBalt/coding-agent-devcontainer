from .constants import BASE_IMAGE
from .features import get_feature
from .ports import BASE_PORTS

_COMMON_ENV = {
    "NODE_OPTIONS": "--max-old-space-size=4096",
    "POWERLEVEL9K_DISABLE_GITSTATUS": "true",
    "HTTP_PROXY": "http://host.docker.internal:7890",
    "HTTPS_PROXY": "http://host.docker.internal:7890",
    "NO_PROXY": "localhost,127.0.0.1,host.docker.internal",
    "http_proxy": "http://host.docker.internal:7890",
    "https_proxy": "http://host.docker.internal:7890",
    "no_proxy": "localhost,127.0.0.1,host.docker.internal",
}

# Runtime-injected environment (not baked into the image). Keep secrets and
# non-static values here to avoid buildkit lint warnings (SecretsUsedInArgOrEnv).
_REMOTE_ENV = {
    "OPENCODE_SERVER_USERNAME": "${localEnv:OPENCODE_SERVER_USERNAME}",
    "OPENCODE_SERVER_PASSWORD": "${localEnv:OPENCODE_SERVER_PASSWORD}",
    "DEVCONTAINER_OPCD_PORT": "${localEnv:DEVCONTAINER_OPCD_PORT}",
}

_GPU_ENV = {
    "NVIDIA_VISIBLE_DEVICES": "all",
    "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
}

_PLAYWRIGHT_ENV = {
    "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
}

_CUSTOMIZATIONS = {
    "vscode": {
        "extensions": [
            "dbaeumer.vscode-eslint",
            "esbenp.prettier-vscode",
            "eamodio.gitlens",
            "charliermarsh.ruff",
            "ms-python.python",
            "ms-python.vscode-pylance",
        ],
        "settings": {
            "editor.formatOnSave": True,
            "[python]": {
                "editor.defaultFormatter": "charliermarsh.ruff",
            },
            "editor.defaultFormatter": "esbenp.prettier-vscode",
            "editor.codeActionsOnSave": {
                "source.fixAll.eslint": "explicit",
            },
            "terminal.integrated.defaultProfile.linux": "zsh",
            "terminal.integrated.profiles.linux": {
                "bash": {
                    "path": "bash",
                    "icon": "terminal-bash",
                },
                "zsh": {
                    "path": "zsh",
                },
            },
        },
    }
}

_MOUNTS = [
    "source=devcontainer-bashhistory-${devcontainerId},target=/commandhistory,type=volume",
    "source=${env:HOME}/.ssh/id_ed25519.pub,target=/ssh-auth-key.pub,type=bind,readonly",
    "source=devcontainer-ssh-hostkey,target=/home/node/.ssh/host_ssh_key,type=volume",
    "source=devcontainer-pnpm-home,target=/usr/local/share/pnpm-global,type=volume",
    "source=devcontainer-uv-cache,target=/home/node/.cache/uv,type=volume",
]

_POST_START_COMMAND = "/home/node/.local/bin/init-ssh.sh"


def _port_mappings(selected: list[str]):
    mappings = list(BASE_PORTS)
    for feature_id in selected:
        feature = get_feature(feature_id)
        if feature is not None:
            mappings.extend(feature.ports)
    return mappings


def _remote_env(selected: list[str]) -> dict[str, str]:
    remote_env = dict(_REMOTE_ENV)
    if "opencode" not in selected:
        remote_env.pop("DEVCONTAINER_OPCD_PORT", None)
    return remote_env


def render_devcontainer(selected: list[str], gpu: bool) -> dict:
    """Build the full devcontainer.json dict for a project.

    Args:
        selected: ids of the optional features to enable.
        gpu: whether to enable GPU support.
    """
    features: dict[str, dict] = {}
    for feature_id in selected:
        feature = get_feature(feature_id)
        if feature is not None:
            features[feature.reference] = {}

    run_args = ["--cap-add=NET_ADMIN", "--cap-add=NET_RAW"]
    if gpu:
        run_args.append("--gpus=all")

    container_env = dict(_COMMON_ENV)
    if gpu:
        container_env.update(_GPU_ENV)
    if "playwright" in selected:
        container_env.update(_PLAYWRIGHT_ENV)

    workspace_mount = (
        "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=delegated"
    )

    return {
        "name": "OpenCode Sandbox",
        "image": BASE_IMAGE,
        "features": features,
        "runArgs": run_args,
        "customizations": _CUSTOMIZATIONS,
        "appPort": [mapping.render() for mapping in _port_mappings(selected)],
        "remoteUser": "node",
        "mounts": _MOUNTS,
        "containerEnv": container_env,
        "remoteEnv": _remote_env(selected),
        "workspaceMount": workspace_mount,
        "workspaceFolder": "/workspace",
        "postStartCommand": _POST_START_COMMAND,
        "waitFor": "postStartCommand",
    }
