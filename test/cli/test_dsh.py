import importlib.util
import json
import socket
import threading
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest

from coding_agent_devcontainer import features
from coding_agent_devcontainer.cli import _feature_options_from_config
from coding_agent_devcontainer.render import render_devcontainer


def _load_startup_module():
    path = Path("src/dsh/start-dsh-web.py")
    spec = importlib.util.spec_from_file_location("start_dsh_web", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dsh_feature_is_discovered_with_port_sidecar() -> None:
    feature = features.get_feature("dsh")

    assert feature is not None
    assert feature.reference.endswith("/dsh:1")
    assert len(feature.ports) == 1
    assert feature.ports[0].env == "DEVCONTAINER_DSH_PORT"
    assert feature.ports[0].container_port == 5000


def test_render_maps_dsh_only_when_selected() -> None:
    without_dsh = render_devcontainer([], gpu=False)
    with_dsh = render_devcontainer(["dsh"], gpu=False)

    assert without_dsh["appPort"] == ["${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222"]
    assert with_dsh["appPort"] == [
        "${localEnv:DEVCONTAINER_SSH_PORT:40022}:2222",
        "${localEnv:DEVCONTAINER_DSH_PORT:40097}:5000",
    ]


def test_dsh_feature_option_is_preserved_when_rendering() -> None:
    rendered = render_devcontainer(
        ["dsh"], gpu=False, feature_options={"dsh": {"version": "feature-branch"}}
    )

    assert rendered["features"]["ghcr.io/ribombalt/coding-agent-devcontainer/dsh:1"] == {
        "version": "feature-branch"
    }


def test_feature_options_are_read_from_existing_config() -> None:
    config = {
        "features": {
            "ghcr.io/ribombalt/coding-agent-devcontainer/dsh:1": {
                "version": "feature-branch"
            }
        }
    }

    assert _feature_options_from_config(config) == {"dsh": {"version": "feature-branch"}}


def test_dsh_feature_installs_startup_script() -> None:
    assert (Path("src/dsh") / "start-dsh-web.py").is_file()


def test_dsh_feature_uses_source_install_script() -> None:
    metadata = json.loads(Path("src/dsh/devcontainer-feature.json").read_text())
    install_script = Path("src/dsh/install-dsh-source.sh").read_text()
    feature_install = Path("src/dsh/install.sh").read_text()

    assert metadata["version"] == "1.0.1"
    assert metadata["options"]["version"]["default"] == "master"
    assert metadata["postCreateCommand"] == "/home/node/.local/bin/install-dsh-source.sh"
    assert "pnpm add -g" not in metadata["postCreateCommand"]
    assert "git clone" in install_script
    assert "deepseek-harness" in install_script
    assert "pnpm install --dangerously-allow-all-builds" in install_script
    assert "pnpm run build" in install_script
    assert 'DSH_SOURCE_REF="${VERSION:-master}"' in feature_install


def test_dsh_startup_uses_proxy_port_and_loopback_port() -> None:
    startup = _load_startup_module()

    assert startup.PROXY_PORT == 5000
    assert startup.DSH_PORT == 5001
    assert startup.DSH_HOST == "127.0.0.1"
    assert startup.DSH_SOURCE_DIR == Path.home() / "deepseek-harness"
    assert startup.DSH_COMMAND == [
        "pnpm",
        "dsh",
        "web",
        "--host",
        "127.0.0.1",
        "--port",
        "5001",
    ]


def test_tcp_proxy_forwards_data_in_both_directions() -> None:
    startup = _load_startup_module()
    backend = socket.socket()
    backend.bind(("127.0.0.1", 0))
    backend.listen(1)
    backend_port = backend.getsockname()[1]
    received: list[bytes] = []

    def serve_backend() -> None:
        connection, _ = backend.accept()
        with connection:
            received.append(connection.recv(1024))
            connection.sendall(b"response")

    backend_thread = threading.Thread(target=serve_backend)
    backend_thread.start()
    proxy = startup.TcpProxyServer(("127.0.0.1", 0), ("127.0.0.1", backend_port))
    proxy_thread = threading.Thread(target=proxy.serve_forever)
    proxy_thread.start()

    try:
        with socket.create_connection(proxy.server_address) as client:
            client.sendall(b"request")
            assert client.recv(1024) == b"response"
        backend_thread.join(timeout=2)
        assert received == [b"request"]
    finally:
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join(timeout=2)
        backend.close()


def test_tcp_proxy_preserves_backend_data_after_client_half_close() -> None:
    startup = _load_startup_module()
    backend = socket.socket()
    backend.bind(("127.0.0.1", 0))
    backend.listen(1)
    backend_port = backend.getsockname()[1]
    backend_received = Event()
    send_response = Event()

    def serve_backend() -> None:
        connection, _ = backend.accept()
        with connection:
            assert connection.recv(1024) == b"request"
            backend_received.set()
            assert send_response.wait(timeout=2)
            connection.sendall(b"response")

    backend_thread = threading.Thread(target=serve_backend)
    backend_thread.start()
    proxy = startup.TcpProxyServer(("127.0.0.1", 0), ("127.0.0.1", backend_port))
    proxy_thread = threading.Thread(target=proxy.serve_forever)
    proxy_thread.start()

    try:
        with socket.create_connection(proxy.server_address) as client:
            client.sendall(b"request")
            client.shutdown(socket.SHUT_WR)
            assert backend_received.wait(timeout=2)
            send_response.set()
            assert client.recv(1024) == b"response"
        backend_thread.join(timeout=2)
    finally:
        send_response.set()
        proxy.shutdown()
        proxy.server_close()
        proxy_thread.join(timeout=2)
        backend.close()


def test_dsh_readiness_fails_when_process_exits() -> None:
    startup = _load_startup_module()
    dsh = Mock()
    dsh.poll.return_value = 1

    assert startup._wait_for_dsh(dsh, timeout=0) is False


def test_dsh_proxy_readiness_fails_when_service_exits() -> None:
    startup = _load_startup_module()
    service = Mock()
    service.poll.return_value = 1

    assert startup._wait_for_proxy(service, timeout=0) is False


def test_startup_reports_proxy_readiness_failure(tmp_path, monkeypatch) -> None:
    startup = _load_startup_module()
    startup.PID_FILE = tmp_path / "web.pid"
    startup.LOG_FILE = tmp_path / "web.log"
    startup.LOCK_FILE = tmp_path / "web.lock"
    service = Mock()
    service.poll.return_value = None
    monkeypatch.setattr(startup.subprocess, "Popen", lambda *args, **kwargs: service)
    monkeypatch.setattr(startup, "_wait_for_proxy", lambda process: False)
    monkeypatch.setattr(startup.sys, "argv", ["start-dsh-web.py"])

    with pytest.raises(RuntimeError, match="proxy did not become ready"):
        startup.main()

    service.terminate.assert_called_once_with()
    service.wait.assert_called_once_with(timeout=5)


def test_run_service_cleans_up_when_proxy_bind_fails(tmp_path, monkeypatch) -> None:
    startup = _load_startup_module()
    startup.PID_FILE = tmp_path / "web.pid"
    startup.LOG_FILE = tmp_path / "web.log"
    dsh = Mock()
    dsh.poll.return_value = None
    popen_calls = []

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        return dsh

    monkeypatch.setattr(startup.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(startup, "_wait_for_dsh", lambda process: True)

    class FailingProxy:
        def __init__(self, *args, **kwargs):
            raise OSError("address already in use")

    monkeypatch.setattr(startup, "TcpProxyServer", FailingProxy)

    with pytest.raises(OSError, match="address already in use"):
        startup._run_service()

    dsh.terminate.assert_called_once_with()
    dsh.wait.assert_called_once_with(timeout=5)
    assert not startup.PID_FILE.exists()
    assert popen_calls[0][0][0] == startup.DSH_COMMAND
    assert popen_calls[0][1]["cwd"] == startup.DSH_SOURCE_DIR


def test_dsh_watcher_requests_proxy_shutdown_after_process_exit() -> None:
    startup = _load_startup_module()
    dsh = Mock()
    proxy = Mock()

    startup._shutdown_when_dsh_exits(dsh, proxy)

    dsh.wait.assert_called_once_with()
    proxy.shutdown.assert_called_once_with()
