from pathlib import Path

from coding_agent_devcontainer.up import load_env_file, resolve_env


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text)


def test_load_env_file_skips_comments_and_blanks(tmp_path: Path) -> None:
    f = tmp_path / ".env"
    _write(f, "# comment\n\nKEY=value\nEMPTY=\n# trailing\n")
    assert load_env_file(f) == {"KEY": "value", "EMPTY": ""}


def test_load_env_file_missing_returns_empty(tmp_path: Path) -> None:
    assert load_env_file(tmp_path / "nope.env") == {}


def test_shell_export_wins_over_all(tmp_path: Path) -> None:
    global_env = tmp_path / "global.env"
    project_env = tmp_path / ".devcontainer" / ".env"
    _write(global_env, "OPENCODE_SERVER_PASSWORD=global\n")
    _write(project_env, "OPENCODE_SERVER_PASSWORD=project\n")

    base = {"OPENCODE_SERVER_PASSWORD": "shell", "OTHER": "keep"}
    result = resolve_env(tmp_path, base, global_env=global_env)

    assert result["OPENCODE_SERVER_PASSWORD"] == "shell"
    assert result["OTHER"] == "keep"


def test_project_overrides_global(tmp_path: Path) -> None:
    global_env = tmp_path / "global.env"
    project_env = tmp_path / ".devcontainer" / ".env"
    _write(global_env, "OPENCODE_SERVER_PASSWORD=global\nOPENCODE_SERVER_USERNAME=globaluser\n")
    _write(project_env, "OPENCODE_SERVER_PASSWORD=project\n")

    result = resolve_env(tmp_path, {}, global_env=global_env)

    assert result["OPENCODE_SERVER_PASSWORD"] == "project"
    assert result["OPENCODE_SERVER_USERNAME"] == "globaluser"


def test_global_applies_when_nothing_else(tmp_path: Path) -> None:
    global_env = tmp_path / "global.env"
    _write(global_env, "OPENCODE_SERVER_PASSWORD=global\n")

    result = resolve_env(tmp_path, {}, global_env=global_env)

    assert result["OPENCODE_SERVER_PASSWORD"] == "global"


def test_workspace_path_str_supported(tmp_path: Path) -> None:
    global_env = tmp_path / "global.env"
    project_env = tmp_path / ".devcontainer" / ".env"
    _write(global_env, "OPENCODE_SERVER_PASSWORD=global\n")
    _write(project_env, "OPENCODE_SERVER_PASSWORD=project\n")

    result = resolve_env(str(tmp_path), {}, global_env=global_env)

    assert result["OPENCODE_SERVER_PASSWORD"] == "project"
