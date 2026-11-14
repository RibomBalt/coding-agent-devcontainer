import json
from pathlib import Path


def test_codex_feature_keeps_only_shared_codex_config_volume() -> None:
    metadata = json.loads(Path("src/codex/devcontainer-feature.json").read_text())

    assert metadata["version"] == "1.0.3"
    assert metadata["mounts"] == [
        {
            "source": "codex-config",
            "target": "/home/node/.codex",
            "type": "volume",
        },
    ]
    assert "CODEX_SQLITE_HOME" not in metadata.get("containerEnv", {})
