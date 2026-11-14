import json
from argparse import Namespace

from coding_agent_devcontainer import cli


def test_init_defaults_to_codex_git_delta_agent_browser_and_pi(
    monkeypatch, tmp_path
) -> None:
    captured: dict[str, list[str]] = {}

    def prompt_features(current: list[str], default_checked: list[str]) -> list[str]:
        captured["default_checked"] = default_checked
        return default_checked

    monkeypatch.setattr(cli, "_prompt_features", prompt_features)
    monkeypatch.setattr(cli, "_prompt_gpu", lambda current: False)

    args = Namespace(
        workspace=str(tmp_path),
        force=False,
        non_interactive=False,
    )

    assert cli.cmd_init(args) == 0

    expected = ["codex", "git-delta", "agent-browser", "pi"]
    assert captured["default_checked"] == expected
    config = json.loads((tmp_path / ".devcontainer" / "devcontainer.json").read_text())
    workspace_folder = f"/workspace/{tmp_path.name}"
    assert config["workspaceMount"] == (
        "source=${localWorkspaceFolder},"
        f"target={workspace_folder},type=bind,consistency=delegated"
    )
    assert config["workspaceFolder"] == workspace_folder
    configured = {reference.rsplit("/", 1)[-1].split(":", 1)[0] for reference in config["features"]}
    assert configured == set(expected)
