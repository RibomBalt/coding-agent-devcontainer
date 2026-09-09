#!/usr/bin/env python3

import os
import select
import socket
import socketserver
import subprocess
import sys
from pathlib import Path


PROXY_HOST = "0.0.0.0"
PROXY_PORT = 5000
DSH_HOST = "127.0.0.1"
DSH_PORT = 5001
PID_FILE = Path.home() / ".dsh" / "web.pid"
LOG_FILE = Path.home() / ".dsh" / "web.log"


class TcpProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            upstream = socket.create_connection(self.server.target, timeout=10)
        except OSError:
            return

        with upstream:
            sockets = (self.request, upstream)
            while True:
                readable, _, _ = select.select(sockets, [], [])
                for source in readable:
                    target = (
                        upstream
                        if source.fileno() == self.request.fileno()
                        else self.request
                    )
                    data = source.recv(65536)
                    if not data:
                        return
                    target.sendall(data)


class TcpProxyServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address, target):
        self.target = target
        super().__init__(server_address, TcpProxyHandler)


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _existing_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None
    return pid if _is_running(pid) else None


def _run_service() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    dsh_log = LOG_FILE.open("ab", buffering=0)
    dsh = subprocess.Popen(
        ["dsh", "web", "--host", DSH_HOST, "--port", str(DSH_PORT)],
        cwd="/workspace",
        stdin=subprocess.DEVNULL,
        stdout=dsh_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        close_fds=True,
    )
    proxy = TcpProxyServer((PROXY_HOST, PROXY_PORT), (DSH_HOST, DSH_PORT))
    try:
        proxy.serve_forever()
    finally:
        proxy.server_close()
        if dsh.poll() is None:
            dsh.terminate()
            try:
                dsh.wait(timeout=5)
            except subprocess.TimeoutExpired:
                dsh.kill()
        dsh_log.close()
        if _existing_pid() == os.getpid():
            PID_FILE.unlink(missing_ok=True)


def main() -> None:
    if "--serve" in sys.argv:
        _run_service()
        return

    existing_pid = _existing_pid()
    if existing_pid is not None:
        print(f"dsh Web UI already running with pid {existing_pid}")
        return

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve"],
            cwd="/workspace",
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    print(f"dsh Web UI proxy started with pid {process.pid} on port {PROXY_PORT}")


if __name__ == "__main__":
    main()
