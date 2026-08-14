#!/usr/bin/env python3
"""兼容入口：转发到 `coding-agent-devcontainer up`。

此脚本已被 `coding-agent-devcontainer up` 取代，保留以兼容旧用法。
注意：`--gpus` 参数已废弃，GPU 支持由项目 devcontainer.json 的 `runArgs`（`--gpus=all`）决定。
"""
import argparse
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Start a devcontainer workspace "
            "(deprecated, use `coding-agent-devcontainer up`)"
        )
    )
    parser.add_argument("-w", "--workspace-path", help="Path to the workspace folder")
    parser.add_argument(
        "--gpus",
        action="store_true",
        default=False,
        help="DEPRECATED: GPU is controlled by devcontainer.json",
    )
    parser.add_argument(
        "-p",
        "--port",
        "--ssh-port",
        type=int,
        default=40022,
        help="SSH port to use",
    )

    args = parser.parse_args()
    if not args.workspace_path:
        parser.error("Workspace path is required")

    if args.gpus:
        print("提示：--gpus 已废弃，GPU 支持由项目的 devcontainer.json 决定，已忽略。")

    cli = shutil.which("coding-agent-devcontainer")
    if not cli:
        print("未找到 coding-agent-devcontainer，请先安装：`pip install .` 或 `uv tool install .`")
        return 1

    return subprocess.call(
        [cli, "up", "-w", args.workspace_path, "-p", str(args.port)]
    )


if __name__ == "__main__":
    sys.exit(main())
