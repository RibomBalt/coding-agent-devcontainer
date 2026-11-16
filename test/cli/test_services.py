import json
import os
import subprocess
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest
from rich.console import Console

from coding_agent_devcontainer import cli, services
from coding_agent_devcontainer.constants import MANAGED_CONTAINER_LABEL
from coding_agent_devcontainer.render import render_devcontainer


def _container(
    container_id: str,
    name: str,
    workspace: str,
    *,
    running: bool,
    managed: bool,
) -> dict:
    labels = {"devcontainer.local_folder": workspace}
    if managed:
        labels[MANAGED_CONTAINER_LABEL] = "true"
    return {
        "Id": container_id,
        "Name": f"/{name}",
        "Config": {"Labels": labels},
        "State": {"Running": running},
        "Mounts": [
            {
                "Type": "bind",
                "Source": workspace,
                "Destination": "/workspace/project",
                "RW": True,
                "Mode": "",
                "Propagation": "rprivate",
            }
        ],
        "NetworkSettings": {"Ports": {"2222/tcp": [{"HostIp": "127.0.0.1", "HostPort": "40022"}]}},
    }


def test_discover_services_reads_workspace_mount_and_status(monkeypatch, tmp_path) -> None:
    workspace = str(tmp_path / "alpha")
    records = [
        _container("abc123456789", "alpha", workspace, running=True, managed=True),
        _container(
            "def123456789", "old-alpha", str(tmp_path / "old"), running=False, managed=False
        ),
    ]
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[1:3] == ["ps", "--all"]:
            return SimpleNamespace(stdout="abc123456789\ndef123456789\n")
        return SimpleNamespace(stdout=json.dumps(records))

    monkeypatch.setattr(services.subprocess, "run", fake_run)

    found = services.discover_services()

    assert [service.workspace for service in found] == [
        str((tmp_path / "alpha").resolve()),
        str((tmp_path / "old").resolve()),
    ]
    assert found[0].running is True
    assert found[0].mount_target == "/workspace/project"
    assert found[0].ssh_port == 40022
    assert found[0].managed is True
    assert found[1].running is False
    assert found[1].managed is False
    assert calls[0] == [
        "docker",
        "ps",
        "--all",
        "--quiet",
        "--filter",
        "label=devcontainer.local_folder",
    ]


def test_discover_services_skips_inspect_when_no_containers(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        services.subprocess,
        "run",
        lambda args, **kwargs: calls.append(args) or SimpleNamespace(stdout=""),
    )

    assert services.discover_services() == []
    assert len(calls) == 1


def test_connect_service_execs_zsh_as_node_with_host_terminal_vars(monkeypatch) -> None:
    service = services.Service(
        "abc123", "alpha", "/work/alpha", True, "/workspace/alpha", None, True
    )
    captured = {}
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("COLORTERM", "truecolor")

    def fake_run(args, **kwargs):
        captured["args"] = args
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(services.subprocess, "run", fake_run)

    assert services.connect_service(service) == 7
    assert captured["args"] == [
        "docker",
        "exec",
        "--interactive",
        "--tty",
        "--user",
        "node",
        "--env",
        "TERM=xterm-256color",
        "--env",
        "COLORTERM=truecolor",
        "--workdir",
        "/workspace/alpha",
        "abc123",
        "zsh",
    ]


def test_connect_service_does_not_invent_terminal_vars(monkeypatch) -> None:
    service = services.Service(
        "abc123", "alpha", "/work/alpha", True, "/workspace/alpha", None, True
    )
    captured = {}
    monkeypatch.delenv("TERM", raising=False)
    monkeypatch.delenv("COLORTERM", raising=False)

    def fake_run(args, **kwargs):
        captured["args"] = args
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(services.subprocess, "run", fake_run)

    assert services.connect_service(service) == 0
    assert captured["args"] == [
        "docker",
        "exec",
        "--interactive",
        "--tty",
        "--user",
        "node",
        "--workdir",
        "/workspace/alpha",
        "abc123",
        "zsh",
    ]


def test_connect_service_rejects_offline_container() -> None:
    service = services.Service("abc123", "alpha", "/work/alpha", False, None, None, True)

    with pytest.raises(ValueError, match="不在线"):
        services.connect_service(service)


def test_connect_list_shows_workspace_status_and_mount(monkeypatch) -> None:
    monkeypatch.setattr(cli, "console", Console(width=180))
    monkeypatch.setattr(
        cli,
        "discover_services",
        lambda: [
            services.Service(
                "abc123", "alpha", "/work/alpha", True, "/workspace/alpha", 40022, True
            ),
            services.Service("def456", "old", "/work/old", False, None, None, False),
        ],
    )

    with cli.console.capture() as capture:
        result = cli.cmd_connect(Namespace(list=True, service=None))

    output = capture.get()
    assert result == 0
    assert "在线" in output
    assert "离线" in output
    assert "/work/alpha" in output
    assert "/workspace/alpha" in output
    assert "旧版/其他 Dev Container" in output


def test_connect_by_workspace_path_selects_matching_online_service(monkeypatch) -> None:
    service = services.Service(
        "abc123", "alpha", "/work/alpha", True, "/workspace/alpha", None, True
    )
    monkeypatch.setattr(cli, "discover_services", lambda: [service])
    connected = []
    monkeypatch.setattr(cli, "connect_service", lambda item: connected.append(item) or 0)

    result = cli.cmd_connect(Namespace(list=False, service="/work/alpha"))

    assert result == 0
    assert connected == [service]


def test_connect_prompt_contains_only_online_services(monkeypatch) -> None:
    online = services.Service(
        "abc123", "alpha", "/work/alpha", True, "/workspace/alpha", None, True
    )
    offline = services.Service("def456", "old", "/work/old", False, None, None, False)
    monkeypatch.setattr(cli, "discover_services", lambda: [online, offline])
    selected = {}

    class Prompt:
        def ask(self):
            return 0

    def fake_select(message, choices):
        selected["choices"] = choices
        return Prompt()

    monkeypatch.setattr(cli.questionary, "select", fake_select)
    connected = []
    monkeypatch.setattr(cli, "connect_service", lambda item: connected.append(item) or 0)

    assert cli.cmd_connect(Namespace(list=False, service=None)) == 0
    assert len(selected["choices"]) == 1
    assert connected == [online]


def test_service_completion_returns_online_workspace_and_basename(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "discover_services",
        lambda: [
            services.Service("abc123", "alpha", "/work/alpha", True, None, None, True),
            services.Service("def456", "offline", "/work/offline", False, None, None, False),
        ],
    )

    assert cli._service_completer("", Namespace()) == ["/work/alpha", "alpha"]


def test_rendered_config_marks_managed_container(tmp_path) -> None:
    config = render_devcontainer([], False, workspace_path=tmp_path)

    assert f"--label={MANAGED_CONTAINER_LABEL}=true" in config["runArgs"]


def test_post_create_rewrites_term_fallback_and_preserves_exec_value(tmp_path) -> None:
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text("export TERM=xterm\n")
    config = render_devcontainer([], False, workspace_path=tmp_path)
    env = os.environ | {"HOME": str(tmp_path), "TERM": "xterm-256color"}

    subprocess.run(["sh", "-c", config["postCreateCommand"]], env=env, check=True)
    result = subprocess.run(
        ["sh", "-c", '. "$HOME/.zshrc"; printf %s "$TERM"'],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert zshrc.read_text() == 'export TERM="${TERM:-xterm}"\n'
    assert result.stdout == "xterm-256color"


def test_workspace_up_injects_label_and_preserves_run_args(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / ".devcontainer" / "devcontainer.json"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({"runArgs": ["--cap-add=SYS_PTRACE"], "appPort": []}))
    monkeypatch.setattr(
        "coding_agent_devcontainer.up._devcontainer_host_ports", lambda path: (set(), set())
    )
    monkeypatch.setattr("coding_agent_devcontainer.up.allocate_ports", lambda *args, **kwargs: ())
    monkeypatch.setattr("coding_agent_devcontainer.up._port_env_names", lambda path: [])
    monkeypatch.setattr("coding_agent_devcontainer.up.resolve_env", lambda path, env: env)
    monkeypatch.setattr("coding_agent_devcontainer.up._workspace_ssh_port", lambda path, env: None)
    captured = {}

    def fake_run(args, **kwargs):
        override_index = args.index("--override-config") + 1
        captured["override"] = json.loads(Path(args[override_index]).read_text())
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("coding_agent_devcontainer.up.subprocess.run", fake_run)

    from coding_agent_devcontainer.up import workspace_up

    assert workspace_up(["devcontainer"], str(tmp_path), 40022) == 0
    assert captured["override"]["runArgs"] == [
        "--cap-add=SYS_PTRACE",
        f"--label={MANAGED_CONTAINER_LABEL}=true",
    ]
