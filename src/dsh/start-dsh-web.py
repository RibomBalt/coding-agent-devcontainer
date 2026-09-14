#!/usr/bin/env python3

import fcntl
import os
import select
import shlex
import socket
import socketserver
import subprocess
import sys
import threading
import time
from pathlib import Path

PROXY_HOST = "0.0.0.0"
PROXY_PORT = 5000
DSH_HOST = "127.0.0.1"
DSH_PORT = 5001
DSH_SOURCE_DIR = Path.home() / "deepseek-harness"
DSH_COMMAND = [
    "pnpm",
    "dsh",
    "web",
    "--host",
    DSH_HOST,
    "--port",
    str(DSH_PORT),
]
PID_FILE = Path.home() / ".dsh" / "web.pid"
LOG_FILE = Path.home() / ".dsh" / "web.log"
LOCK_FILE = Path.home() / ".dsh" / "web.lock"


class TcpProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        try:
            upstream = socket.create_connection(self.server.target, timeout=10)
        except OSError:
            return

        with upstream:
            upstream.settimeout(None)
            client = self.request
            sockets = [client, upstream]
            while sockets:
                readable, _, _ = select.select(sockets, [], [])
                for source in readable:
                    target = upstream if source is client else client
                    try:
                        data = source.recv(65536)
                    except OSError:
                        return
                    if data:
                        try:
                            target.sendall(data)
                        except OSError:
                            return
                        continue

                    # Preserve half-close semantics: EOF in one direction
                    # must not discard data still flowing in the other one.
                    sockets.remove(source)
                    try:
                        target.shutdown(socket.SHUT_WR)
                    except OSError:
                        pass


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


def _is_service_process(pid: int) -> bool:
    try:
        command_line = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return True
    return b"start-dsh-web.py" in command_line and b"--serve" in command_line


def _existing_pid() -> int | None:
    try:
        pid = int(PID_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None
    return pid if _is_running(pid) and _is_service_process(pid) else None


def _wait_for_dsh(dsh: subprocess.Popen, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if dsh.poll() is not None:
            return False
        try:
            connection = socket.create_connection((DSH_HOST, DSH_PORT), timeout=1)
        except OSError:
            time.sleep(0.2)
        else:
            connection.close()
            return True
    return False


def _wait_for_proxy(service: subprocess.Popen, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service.poll() is not None:
            return False
        try:
            connection = socket.create_connection(("127.0.0.1", PROXY_PORT), timeout=1)
        except OSError:
            time.sleep(0.2)
        else:
            connection.close()
            return True
    return False


def _terminate_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _shutdown_when_dsh_exits(
    dsh: subprocess.Popen, proxy: TcpProxyServer
) -> None:
    dsh.wait()
    proxy.shutdown()


def _run_service() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))
    dsh_log = None
    dsh = None
    proxy = None
    monitor = None
    try:
        dsh_env = os.environ.copy()
        dsh_env["PATH"] = ":".join(
            [
                "/usr/local/share/pnpm-global/bin",
                "/usr/local/share/npm-global/bin",
                dsh_env.get("PATH", ""),
            ]
        )
        dsh_log = LOG_FILE.open("ab", buffering=0)
        dsh_command = DSH_COMMAND
        print(
            f"Starting DSH Web UI subprocess: {shlex.join(dsh_command)}",
            flush=True,
        )
        dsh = subprocess.Popen(
            dsh_command,
            cwd=DSH_SOURCE_DIR,
            env=dsh_env,
            stdin=subprocess.DEVNULL,
            stdout=dsh_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
        print(f"DSH Web UI subprocess started with pid {dsh.pid}", flush=True)
        if not _wait_for_dsh(dsh):
            raise RuntimeError("dsh Web UI did not become ready on port 5001")
        proxy = TcpProxyServer((PROXY_HOST, PROXY_PORT), (DSH_HOST, DSH_PORT))
        monitor = threading.Thread(
            target=_shutdown_when_dsh_exits,
            args=(dsh, proxy),
            daemon=True,
        )
        monitor.start()
        proxy.serve_forever()
    finally:
        _terminate_process(dsh)
        if monitor is not None:
            monitor.join(timeout=1)
        if proxy is not None:
            proxy.server_close()
        if dsh_log is not None:
            dsh_log.close()
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink(missing_ok=True)


def main() -> None:
    if "--serve" in sys.argv:
        _run_service()
        return

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK_FILE.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        existing_pid = _existing_pid()
        if existing_pid is not None:
            print(f"dsh Web UI already running with pid {existing_pid}")
            return

        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("ab", buffering=0) as log:
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve"],
                cwd=DSH_SOURCE_DIR,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        PID_FILE.write_text(str(process.pid))
        if not _wait_for_proxy(process):
            _terminate_process(process)
            raise RuntimeError("dsh Web UI proxy did not become ready on port 5000")
    print(f"dsh Web UI proxy started with pid {process.pid} on port {PROXY_PORT}")


if __name__ == "__main__":
    main()
