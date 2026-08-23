import os

# OCI registry namespace for published features.
REGISTRY = os.environ.get("DEVCONTAINER_REGISTRY", "ghcr.io")
OWNER = os.environ.get("DEVCONTAINER_OWNER", "ribombalt")
REPO = os.environ.get("DEVCONTAINER_REPO", "coding-agent-devcontainer")

# Feature OCI namespace: <registry>/<owner>/<repo>
NAMESPACE = f"{REGISTRY}/{OWNER}/{REPO}"

# Pre-built base image that already contains the common tooling (system packages,
# Node.js, shell setup, SSH, OpenCode config).
BASE_IMAGE = os.environ.get(
    "DEVCONTAINER_BASE_IMAGE", f"{REGISTRY}/{OWNER}/{REPO}-base:latest"
)

REMOTE_USER = "node"
