import json
from dataclasses import dataclass
from pathlib import Path

from .constants import COMMON_FEATURE_IDS, NAMESPACE, OPTIONAL_FEATURE_IDS

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

# Human-facing metadata for the TUI. `common` marks features baked into the base image.
# `version` is the major version referenced from OCI (`:1`).
_FEATURE_META = {
    "system-tools": {
        "name": "System Development Tools",
        "description": "Essential packages, locale, Playwright system deps",
        "common": True,
        "version": "1",
    },
    "shell-setup": {
        "name": "Shell Setup (zsh + powerlevel10k)",
        "description": "zsh-in-docker with powerlevel10k and fzf",
        "common": True,
        "version": "1",
    },
    "ssh-firewall": {
        "name": "SSH Access & Firewall",
        "description": "SSH init script, OpenCode web startup, firewall",
        "common": True,
        "version": "1",
    },
    "opencode-config": {
        "name": "OpenCode Configuration",
        "description": "vimrc, git identity, OpenCode directories",
        "common": True,
        "version": "1",
    },
    "node-tooling": {
        "name": "Node.js Tooling",
        "description": "pnpm + npm registry + Playwright browsers",
        "common": False,
        "version": "1",
    },
    "python-uv": {
        "name": "Python & UV",
        "description": "uv package manager + PyPI mirror",
        "common": False,
        "version": "1",
    },
    "golang": {
        "name": "Go",
        "description": "Go toolchain + GOPROXY",
        "common": False,
        "version": "1",
    },
    "git-delta": {
        "name": "Git Delta",
        "description": "Syntax-highlighted git diffs",
        "common": False,
        "version": "1",
    },
}


@dataclass
class Feature:
    id: str
    name: str
    description: str
    version: str
    common: bool

    @property
    def reference(self) -> str:
        """OCI reference used in devcontainer.json, e.g. ghcr.io/owner/repo/feature:1."""
        return f"{NAMESPACE}/{self.id}:{self.version}"


def _read_version(feature_id: str) -> str:
    """Read the semver version from the feature's devcontainer-feature.json, if present."""
    path = SRC_DIR / feature_id / "devcontainer-feature.json"
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return str(data.get("version", "1.0.0")).split(".")[0]
        except (json.JSONDecodeError, OSError):
            pass
    return _FEATURE_META[feature_id]["version"]


def all_features() -> list[Feature]:
    features = []
    for feature_id, meta in _FEATURE_META.items():
        features.append(
            Feature(
                id=feature_id,
                name=meta["name"],
                description=meta["description"],
                version=_read_version(feature_id),
                common=meta["common"],
            )
        )
    return features


def common_features() -> list[Feature]:
    return [f for f in all_features() if f.id in COMMON_FEATURE_IDS]


def optional_features() -> list[Feature]:
    return [f for f in all_features() if f.id in OPTIONAL_FEATURE_IDS]


def get_feature(feature_id: str) -> Feature | None:
    for f in all_features():
        if f.id == feature_id:
            return f
    return None
