import json
from pathlib import Path

from coding_agent_devcontainer import features
from coding_agent_devcontainer.render import render_devcontainer


def test_pi_feature_is_discovered_without_port_mapping() -> None:
    feature = features.get_feature("pi")

    assert feature is not None
    assert feature.reference.endswith("/pi:1")
    assert feature.ports == ()


def test_pi_feature_declares_persistent_home_directory_and_install_command() -> None:
    metadata = json.loads(Path("src/pi/devcontainer-feature.json").read_text())

    assert metadata["mounts"] == [
        {
            "source": "pi-config",
            "target": "/home/node/.pi",
            "type": "volume",
        }
    ]
    assert metadata["postCreateCommand"] == (
        "export PATH=/usr/local/share/pnpm-global/bin:/usr/local/share/npm-global/bin:$PATH "
        "&& pnpm add -g --ignore-scripts @earendil-works/pi-coding-agent"
    )
    assert "postStartCommand" not in metadata
    assert not Path("src/pi/ports.json").exists()


def test_rendering_pi_keeps_only_base_ssh_port() -> None:
    rendered = render_devcontainer(["pi"], gpu=False)

    assert rendered["appPort"] == ["${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222"]
