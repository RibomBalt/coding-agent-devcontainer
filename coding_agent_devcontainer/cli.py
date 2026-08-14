import argparse
import json
import sys
from pathlib import Path

import questionary
from rich.console import Console

from .constants import OPTIONAL_FEATURE_IDS
from .features import get_feature, optional_features
from .render import render_devcontainer

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
        if feature_id in OPTIONAL_FEATURE_IDS:
            selected.append(feature_id)
    return selected


def _gpu_from_config(config: dict) -> bool:
    return "--gpus=all" in (config.get("runArgs") or [])


def _write_config(workspace: Path, config: dict) -> Path:
    path = _devcontainer_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=4, ensure_ascii=False) + "\n")
    return path


def _prompt_features(current: list[str]) -> list[str]:
    choices = [
        questionary.Choice(
            title=f"{f.name} — {f.description}",
            value=f.id,
            checked=(f.id in current),
        )
        for f in optional_features()
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
    for f in optional_features():
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
            [f.strip() for f in args.features.split(",") if f.strip()]
            if args.features
            else []
        )
        gpu = args.gpu
    else:
        selected = _prompt_features(current_selected)
        gpu = _prompt_gpu(current_gpu)

    for feature_id in selected:
        if get_feature(feature_id) is None:
            console.print(f"[red]未知 feature: {feature_id}[/red]")
            return 1

    config = render_devcontainer(selected, gpu)
    path = _write_config(workspace, config)
    console.print(f"[green]✓ 已生成 {path}[/green]")
    console.print(f"  已选择: {', '.join(selected) or '(无)'}")
    console.print(f"  GPU: {'是' if gpu else '否'}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    workspace = _workspace_dir(args.workspace)
    existing = _read_existing(workspace)
    if existing is None:
        console.print(
            f"[yellow]{_devcontainer_path(workspace)} 不存在，改用 `init` 创建[/yellow]"
        )
        return 1

    current_selected = _selected_from_config(existing)
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

    config = render_devcontainer(selected, gpu)
    path = _write_config(workspace, config)
    console.print(f"[green]✓ 已更新 {path}[/green]")
    console.print(f"  已选择: {', '.join(selected) or '(无)'}")
    console.print(f"  GPU: {'是' if gpu else '否'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencode-devcontainer",
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
    update_parser.add_argument(
        "--non-interactive", action="store_true", help="非交互模式"
    )
    update_parser.set_defaults(func=cmd_update)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
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
