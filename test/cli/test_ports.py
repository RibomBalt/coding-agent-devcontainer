import json
from pathlib import Path

import pytest

from coding_agent_devcontainer import features
from coding_agent_devcontainer.render import render_devcontainer
from coding_agent_devcontainer.ports import load_feature_ports
from coding_agent_devcontainer.up import allocate_ports, workspace_up


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text)


def _feature(path: Path, feature_id: str) -> None:
    _write(
        path / feature_id / "devcontainer-feature.json",
        json.dumps(
            {
                "id": feature_id,
                "version": "1.0.0",
                "name": feature_id,
                "description": feature_id,
            }
        ),
    )


def test_render_includes_optional_feature_ports_only_when_selected(
    tmp_path: Path, monkeypatch
) -> None:
    _feature(tmp_path, "with-port")
    _feature(tmp_path, "without-port")
    _write(
        tmp_path / "with-port" / "ports.json",
        json.dumps(
            {
                "ports": [
                    {
                        "env": "DEVCONTAINER_WITH_PORT",
                        "containerPort": 8123,
                        "defaultHostPort": 48123,
                    }
                ]
            }
        ),
    )
    monkeypatch.setattr(features, "SRC_DIR", tmp_path)

    without_port = render_devcontainer(["without-port"], gpu=False)
    with_port = render_devcontainer(["with-port"], gpu=False)

    assert without_port["appPort"] == ["${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222"]
    assert with_port["appPort"] == [
        "${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222",
        "${localEnv:DEVCONTAINER_WITH_PORT:48123}:8123",
    ]


def test_allocate_ports_scans_upward_for_requested_number(monkeypatch) -> None:
    free_ports = {40022, 40024, 40027}
    monkeypatch.setattr(
        "coding_agent_devcontainer.up.check_port_availability",
        lambda port: port in free_ports,
    )

    assert allocate_ports(40022, 3) == (40022, 40024, 40027)


def test_render_rejects_duplicate_port_environment_names(tmp_path: Path, monkeypatch) -> None:
    _feature(tmp_path, "first")
    _feature(tmp_path, "second")
    for feature_id in ("first", "second"):
        _write(
            tmp_path / feature_id / "ports.json",
            json.dumps(
                {
                    "ports": [
                        {
                            "env": "DEVCONTAINER_SHARED_PORT",
                            "containerPort": 8123,
                            "defaultHostPort": 48123,
                        }
                    ]
                }
            ),
        )
    monkeypatch.setattr(features, "SRC_DIR", tmp_path)

    with pytest.raises(ValueError, match="duplicate"):
        render_devcontainer(["first", "second"], gpu=False)


def test_load_feature_ports_rejects_invalid_port_metadata(tmp_path: Path) -> None:
    ports_path = tmp_path / "ports.json"
    _write(
        ports_path,
        json.dumps(
            {
                "ports": [
                    {
                        "env": "DEVCONTAINER_INVALID_PORT",
                        "containerPort": 0,
                        "defaultHostPort": 70000,
                    }
                ]
            }
        ),
    )

    with pytest.raises(ValueError, match="1..65535"):
        load_feature_ports(ports_path)


def test_load_feature_ports_rejects_non_object_metadata(tmp_path: Path) -> None:
    ports_path = tmp_path / "ports.json"
    _write(ports_path, "[]")

    with pytest.raises(ValueError, match="top-level object"):
        load_feature_ports(ports_path)


def test_workspace_up_injects_every_rendered_port(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / ".devcontainer" / "devcontainer.json"
    _write(
        config_path,
        json.dumps(
            {
                "appPort": [
                    "${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222",
                    "${localEnv:DEVCONTAINER_WITH_PORT:48123}:8123",
                ]
            }
        ),
    )
    captured: dict = {}

    monkeypatch.setattr(
        "coding_agent_devcontainer.up.allocate_ports",
        lambda start, count: (41000, 41003),
    )

    class Completed:
        returncode = 0

    def run(cmd, env):
        captured["cmd"] = cmd
        captured["env"] = env
        return Completed()

    monkeypatch.setattr("coding_agent_devcontainer.up.subprocess.run", run)

    assert workspace_up(["devcontainer"], str(tmp_path), 40022) == 0
    assert captured["env"]["DEVCONTAINER_SSH_PORT"] == "41000"
    assert captured["env"]["DEVCONTAINER_WITH_PORT"] == "41003"
