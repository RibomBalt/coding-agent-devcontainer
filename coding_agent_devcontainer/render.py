from .constants import BASE_IMAGE
from .features import get_feature

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

_APP_PORT = [
    "${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222",
    "${localEnv:DEVCONTAINER_OPCD_PORT:40096}:4096",
]

_MOUNTS = [
    "source=devcontainer-bashhistory-${devcontainerId},target=/commandhistory,type=volume",
    "source=${env:HOME}/.ssh/id_ed25519.pub,target=/ssh-auth-key.pub,type=bind,readonly",
    "source=devcontainer-ssh-hostkey,target=/home/node/.ssh/host_ssh_key,type=volume",
    "source=devcontainer-pnpm-home,target=/usr/local/share/pnpm-global,type=volume",
]

_POST_START_COMMAND = "/home/node/.local/bin/init-ssh.sh"


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
        "appPort": _APP_PORT,
        "remoteUser": "node",
        "mounts": _MOUNTS,
        "containerEnv": container_env,
        "remoteEnv": dict(_REMOTE_ENV),
        "workspaceMount": workspace_mount,
        "workspaceFolder": "/workspace",
        "postStartCommand": _POST_START_COMMAND,
        "waitFor": "postStartCommand",
    }
