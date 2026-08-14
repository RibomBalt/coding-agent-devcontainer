import json
from dataclasses import dataclass
from pathlib import Path

from .constants import NAMESPACE, OPTIONAL_FEATURE_IDS

SRC_DIR = Path(__file__).resolve().parent.parent / "src"

# Human-facing metadata for the TUI. `version` is the major version referenced
# from OCI (`:1`).
_FEATURE_META = {
    "opencode": {
        "name": "OpenCode Coding Agent",
        "description": "Install and launch the OpenCode coding agent",
        "version": "1",
    },
    "playwright": {
        "name": "Playwright (Chromium)",
        "description": "Playwright Chromium system deps and browsers",
        "version": "1",
    },
    "python-uv": {
        "name": "Python & UV",
        "description": "uv package manager + PyPI mirror",
        "version": "1",
    },
    "golang": {
        "name": "Go",
        "description": "Go toolchain + GOPROXY",
        "version": "1",
    },
    "git-delta": {
        "name": "Git Delta",
        "description": "Syntax-highlighted git diffs",
        "version": "1",
    },
}


@dataclass
class Feature:
    id: str
    name: str
    description: str
    version: str

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
    return [
        Feature(
            id=feature_id,
            name=meta["name"],
            description=meta["description"],
            version=_read_version(feature_id),
        )
        for feature_id, meta in _FEATURE_META.items()
    ]


def optional_features() -> list[Feature]:
    return [f for f in all_features() if f.id in OPTIONAL_FEATURE_IDS]


def get_feature(feature_id: str) -> Feature | None:
    for f in all_features():
        if f.id == feature_id:
            return f
    return None
