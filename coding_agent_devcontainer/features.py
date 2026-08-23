import json
from dataclasses import dataclass
from pathlib import Path

from .constants import NAMESPACE

SRC_DIR = Path(__file__).resolve().parent.parent / "src"


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


def _feature_dirs() -> list[Path]:
    if not SRC_DIR.exists():
        return []
    return sorted(p for p in SRC_DIR.iterdir() if p.is_dir())


def _load_feature(meta_path: Path) -> Feature | None:
    """Load metadata from a feature's devcontainer-feature.json, if parseable."""
    try:
        data = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    feature_id = data.get("id")
    if not feature_id:
        return None
    version = str(data.get("version", "1.0.0")).split(".")[0]
    return Feature(
        id=feature_id,
        name=data.get("name", feature_id),
        description=data.get("description", feature_id),
        version=version,
    )


def all_features() -> list[Feature]:
    """Discover all features by scanning src/<id>/devcontainer-feature.json.

    The devcontainer-feature.json is the single source of truth: it's the same
    definition consumed by the release pipeline (devcontainers/action).
    """
    found = []
    for dir_path in _feature_dirs():
        meta_path = dir_path / "devcontainer-feature.json"
        if meta_path.exists():
            feature = _load_feature(meta_path)
            if feature is not None:
                found.append(feature)
    return sorted(found, key=lambda f: f.id)


def get_feature(feature_id: str) -> Feature | None:
    for f in all_features():
        if f.id == feature_id:
            return f
    return None
