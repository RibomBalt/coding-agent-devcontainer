import importlib.util
import socket
import threading
from pathlib import Path

from coding_agent_devcontainer import features
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


def test_dsh_feature_installs_startup_script() -> None:
    assert (Path("src/dsh") / "start-dsh-web.py").is_file()


def test_dsh_startup_uses_proxy_port_and_loopback_port() -> None:
    startup = _load_startup_module()

    assert startup.PROXY_PORT == 5000
    assert startup.DSH_PORT == 5001
    assert startup.DSH_HOST == "127.0.0.1"


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
