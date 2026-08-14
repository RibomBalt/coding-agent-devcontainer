#!/usr/bin/env python3

import os
import secrets
import subprocess


def check_environ():
    env = os.environ.copy()
    if "OPENCODE_SERVER_USERNAME" not in env or not env["OPENCODE_SERVER_USERNAME"]:
        env["OPENCODE_SERVER_USERNAME"] = "opencode"
    if "OPENCODE_SERVER_PASSWORD" not in env or not env["OPENCODE_SERVER_PASSWORD"]:
        env["OPENCODE_SERVER_PASSWORD"] = secrets.token_urlsafe(32)

    print(f"OPENCODE_SERVER_USERNAME: {env['OPENCODE_SERVER_USERNAME']}")
    print(f"OPENCODE_SERVER_PASSWORD: {env['OPENCODE_SERVER_PASSWORD']}")
    print(f"DEVCONTAINER_OPCD_PORT: {env.get('DEVCONTAINER_OPCD_PORT')}")
    return env


def start_opencode_web(env: dict | None = None):
    env = check_environ() if env is None else env
    pid = subprocess.Popen(
        ["opencode", "serve", "--port", "4096", "--hostname", "0.0.0.0"],
        env=env,
        cwd="/workspace",
        start_new_session=True,
        close_fds=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return pid


def main():
    env = check_environ()
    pid = start_opencode_web(env)
    DEVCONTAINER_OPCD_PORT = os.environ.get("DEVCONTAINER_OPCD_PORT", "<port>")
    print(
        f"""opencode serve process started with pid: {pid.pid}
        You can access the web UI at http://localhost:{DEVCONTAINER_OPCD_PORT}
        or you can use `opencode attach {DEVCONTAINER_OPCD_PORT} -u "{env.get("OPENCODE_SERVER_USERNAME", "opencode")}" -p "{env.get("OPENCODE_SERVER_PASSWORD")}"`
        where {DEVCONTAINER_OPCD_PORT} is maps to 4096 inside container (default 40096).
        """
    )


if __name__ == "__main__":
    main()
