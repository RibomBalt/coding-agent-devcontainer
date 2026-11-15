import argparse
import json
import subprocess
import sys
from pathlib import Path

import argcomplete
import questionary
from rich.console import Console
from rich.table import Table

from .features import all_features, get_feature
from .render import render_devcontainer
from .services import Service, connect_service, discover_services
from .up import check_cli, parse_port_mapping, parse_workspace_mount_target, workspace_up

console = Console()


def _workspace_dir(workspace: str) -> Path:
    return Path(workspace).expanduser().resolve()


def _devcontainer_path(workspace: Path) -> Path:
    return workspace / ".devcontainer" / "devcontainer.json"


def _read_existing(workspace: Path) -> dict | None:
    path = _devcontainer_path(workspace)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        console.print(f"[red]无法解析现有 devcontainer.json: {exc}[/red]")
        return None


def _selected_from_config(config: dict) -> list[str]:
    """Extract optional feature ids referenced in an existing devcontainer.json."""
    selected = []
    for ref in (config.get("features") or {}).keys():
        feature_id = ref.rstrip("/").split("/")[-1].split(":")[0]
        if feature_id in {f.id for f in all_features()}:
            selected.append(feature_id)
    return selected


def _feature_options_from_config(config: dict) -> dict[str, dict]:
    """Extract option values for known features from an existing config."""
    options = {}
    known_features = {f.id for f in all_features()}
    for ref, feature_options in (config.get("features") or {}).items():
        feature_id = ref.rstrip("/").split("/")[-1].split(":")[0]
        if feature_id in known_features and isinstance(feature_options, dict):
            options[feature_id] = dict(feature_options)
    return options


def _gpu_from_config(config: dict) -> bool:
    return "--gpus=all" in (config.get("runArgs") or [])


def _write_config(workspace: Path, config: dict) -> Path:
    path = _devcontainer_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=4, ensure_ascii=False) + "\n")
    return path


def _prompt_features(current: list[str], default_checked: list[str] | None = None) -> list[str]:
    default_checked = default_checked or []
    choices = [
        questionary.Choice(
            title=f"{f.name} — {f.description}",
            value=f.id,
            checked=(f.id in current or f.id in default_checked),
        )
        for f in all_features()
    ]
    selected = questionary.checkbox(
        "选择本项目需要的可选 Feature（空格选择/取消，回车确认）：",
        choices=choices,
    ).ask()
    if selected is None:
        raise KeyboardInterrupt
    return list(selected)


def _prompt_gpu(current: bool) -> bool:
    answer = questionary.confirm("是否启用 GPU 支持？", default=current).ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


def cmd_list(args: argparse.Namespace) -> int:
    console.print("[bold]Optional Features（按需选择）[/bold]")
    for f in all_features():
        console.print(f"  • {f.id}: {f.name} — {f.description}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    workspace = _workspace_dir(args.workspace)
    existing = _read_existing(workspace)

    if existing is not None and not args.force:
        console.print(
            f"[yellow]{_devcontainer_path(workspace)} 已存在，"
            "使用 `update` 命令修改，或加 --force 覆盖[/yellow]"
        )
        return 1

    current_selected = _selected_from_config(existing) if existing else []
    current_gpu = _gpu_from_config(existing) if existing else False

    if args.non_interactive:
        selected = (
            [f.strip() for f in args.features.split(",") if f.strip()] if args.features else []
        )
        gpu = args.gpu
    else:
        selected = _prompt_features(
            current_selected,
            default_checked=["codex", "git-delta", "agent-browser", "pi"],
        )
        gpu = _prompt_gpu(current_gpu)

    for feature_id in selected:
        if get_feature(feature_id) is None:
            console.print(f"[red]未知 feature: {feature_id}[/red]")
            return 1

    config = render_devcontainer(selected, gpu, workspace_path=workspace)
    path = _write_config(workspace, config)
    console.print(f"[green]✓ 已生成 {path}[/green]")
    console.print(f"  已选择: {', '.join(selected) or '(无)'}")
    console.print(f"  GPU: {'是' if gpu else '否'}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    workspace = _workspace_dir(args.workspace)
    existing = _read_existing(workspace)
    if existing is None:
        console.print(f"[yellow]{_devcontainer_path(workspace)} 不存在，改用 `init` 创建[/yellow]")
        return 1

    current_selected = _selected_from_config(existing)
    current_feature_options = _feature_options_from_config(existing)
    current_gpu = _gpu_from_config(existing)

    if args.non_interactive:
        selected = (
            [f.strip() for f in args.features.split(",") if f.strip()]
            if args.features
            else current_selected
        )
        gpu = args.gpu if args.gpu is not None else current_gpu
    else:
        selected = _prompt_features(current_selected)
        gpu = _prompt_gpu(current_gpu)

    config = render_devcontainer(
        selected, gpu, current_feature_options, workspace_path=workspace
    )
    path = _write_config(workspace, config)
    console.print(f"[green]✓ 已更新 {path}[/green]")
    console.print(f"  已选择: {', '.join(selected) or '(无)'}")
    console.print(f"  GPU: {'是' if gpu else '否'}")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    workspace = _workspace_dir(args.workspace)

    if not _devcontainer_path(workspace).exists():
        console.print(
            f"[yellow]{_devcontainer_path(workspace)} 不存在，"
            f"请先运行 `coding-agent-devcontainer init -w {workspace}`[/yellow]"
        )
        return 1

    cmd = check_cli()
    if not cmd:
        console.print("[red]未找到 devcontainer CLI（devcontainer / npx / pnpx / bunx）[/red]")
        return 1
    console.print(f"Using devcontainer CLI: {cmd[0]}")

    return workspace_up(
        cmd,
        str(workspace),
        args.ssh_port,
        args.force_recreate,
        args.add_ports,
        args.workspace_mount_target,
    )


def _service_completer(prefix: str, parsed_args: argparse.Namespace, **kwargs) -> list[str]:
    """Complete workspace paths for online services."""
    try:
        completions = set()
        for service in discover_services():
            if not service.running:
                continue
            short_name = Path(service.workspace).name
            if service.workspace.startswith(prefix):
                completions.add(service.workspace)
            if short_name.startswith(prefix):
                completions.add(short_name)
        return sorted(completions)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return []


def _format_service(service: Service) -> str:
    return f"{Path(service.workspace).name} ({service.workspace})"


def cmd_connect(args: argparse.Namespace) -> int:
    try:
        services = discover_services()
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        console.print(f"[red]无法读取 Docker 服务：{exc}[/red]")
        return 1

    if not services:
        console.print("[yellow]没有发现 Dev Container 服务[/yellow]")
        return 0 if args.list else 1

    if args.list:
        table = Table(
            "服务",
            "状态",
            "workspace（宿主机）",
            "挂载目标（容器内）",
            "SSH 端口",
            "来源",
        )
        for service in services:
            table.add_row(
                service.name or service.container_id[:12],
                "在线" if service.running else "离线",
                service.workspace,
                service.mount_target or "未知",
                str(service.ssh_port) if service.ssh_port is not None else "未知",
                "本工具" if service.managed else "旧版/其他 Dev Container",
            )
        console.print(table)
        return 0

    online = [service for service in services if service.running]
    if not online:
        console.print("[yellow]没有在线服务可连接；使用 `connect -l` 查看离线服务[/yellow]")
        return 1

    selected: Service | None = None
    if args.service:
        query = args.service
        try:
            query_path = str(Path(query).expanduser().resolve())
        except (OSError, RuntimeError):
            query_path = query
        matches = [
            service
            for service in online
            if query
            in {
                service.workspace,
                service.name,
                service.container_id,
                service.container_id[:12],
            }
            or query_path == service.workspace
            or query == Path(service.workspace).name
        ]
        if len(matches) == 1:
            selected = matches[0]
        elif not matches:
            console.print(f"[red]找不到在线服务：{query}[/red]")
            return 1

    if selected is None:
        choices = [
            questionary.Choice(_format_service(service), value=index)
            for index, service in enumerate(online)
        ]
        answer = questionary.select("选择要连接的在线服务：", choices=choices).ask()
        if answer is None:
            return 130
        selected = online[answer]

    try:
        return connect_service(selected)
    except (OSError, ValueError) as exc:
        console.print(f"[red]无法连接服务：{exc}[/red]")
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coding-agent-devcontainer",
        description="为项目生成/管理 devcontainer.json，按需组合 dev container features。",
    )
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="列出所有可用 feature")
    list_parser.set_defaults(func=cmd_list)

    init_parser = sub.add_parser("init", help="交互式创建 .devcontainer/devcontainer.json")
    init_parser.add_argument("-w", "--workspace", default=".", help="目标项目路径（默认当前目录）")
    init_parser.add_argument(
        "--features",
        help="逗号分隔的 feature id（用于非交互模式）",
    )
    init_parser.add_argument(
        "--gpu",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="启用/禁用 GPU 支持（默认禁用）",
    )
    init_parser.add_argument(
        "--non-interactive", action="store_true", help="非交互模式（配合 --features/--gpu）"
    )
    init_parser.add_argument("--force", action="store_true", help="覆盖已存在的配置")
    init_parser.set_defaults(func=cmd_init)

    update_parser = sub.add_parser("update", help="交互式更新已有 devcontainer.json")
    update_parser.add_argument(
        "-w", "--workspace", default=".", help="目标项目路径（默认当前目录）"
    )
    update_parser.add_argument(
        "--features",
        help="逗号分隔的 feature id（用于非交互模式）",
    )
    update_parser.add_argument(
        "--gpu",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="启用/禁用 GPU 支持（默认保持现有配置）",
    )
    update_parser.add_argument("--non-interactive", action="store_true", help="非交互模式")
    update_parser.set_defaults(func=cmd_update)

    up_parser = sub.add_parser("up", help="启动 devcontainer 容器")
    up_parser.add_argument("-w", "--workspace", default=".", help="项目路径（默认当前目录）")
    up_parser.add_argument(
        "--workspace-mount-target",
        type=parse_workspace_mount_target,
        help="覆写容器内项目挂载路径（默认 /workspace/<项目目录名>）",
    )
    up_parser.add_argument(
        "-p",
        "--port",
        "--ssh-port",
        dest="ssh_port",
        type=int,
        default=40022,
        help="宿主机端口分配起始值（默认 40022，按需向上寻找空闲端口）",
    )
    up_parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="拉取最新 base image、升级 Feature 锁文件，删除已有容器并无缓存重建",
    )
    up_parser.add_argument(
        "--add-port",
        dest="add_ports",
        type=parse_port_mapping,
        action="append",
        default=[],
        metavar="HOST_PORT:CONTAINER_PORT",
        help="临时追加端口映射，可重复指定，例如 --add-port 8080:80",
    )
    up_parser.set_defaults(func=cmd_up)

    connect_parser = sub.add_parser("connect", help="列出或连接 Dev Container 服务")
    connect_parser.add_argument(
        "-l", "--list", action="store_true", help="列出在线和离线服务及 workspace 挂载信息"
    )
    connect_parser.add_argument(
        "service",
        nargs="?",
        help="workspace 路径、项目目录名、容器名或容器 ID（默认交互选择）",
    ).completer = _service_completer
    connect_parser.set_defaults(func=cmd_connect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]已取消[/yellow]")
        return 130


if __name__ == "__main__":
    sys.exit(main())
