import json
from pathlib import Path


def test_codex_feature_has_isolated_sqlite_volume_and_environment() -> None:
    metadata = json.loads(Path("src/codex/devcontainer-feature.json").read_text())

    assert metadata["mounts"] == [
        {
            "source": "codex-config",
            "target": "/home/node/.codex",
            "type": "volume",
        },
        {
            "source": "codex-sqlite-home-${devcontainerId}",
            "target": "/home/node/.local/share/lib/codex-sqlite",
            "type": "volume",
        },
    ]
    assert metadata["containerEnv"]["CODEX_SQLITE_HOME"] == (
        "/home/node/.local/share/lib/codex-sqlite"
    )
