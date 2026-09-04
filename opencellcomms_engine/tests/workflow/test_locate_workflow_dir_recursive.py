"""_locate_workflow_dir must find a bare workflow name in workflows/ subfolders."""
from pathlib import Path

from src.workflow.executor import _locate_workflow_dir


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}")
    return path.parent


def test_bare_name_found_in_subfolder(tmp_path):
    sub = _touch(tmp_path / "opencellcomms_adapters" / "X" / "workflows" / "suite" / "foo.json")
    assert _locate_workflow_dir(Path("foo.json"), tmp_path) == sub


def test_bare_name_still_found_flat(tmp_path):
    flat = _touch(tmp_path / "opencellcomms_adapters" / "X" / "workflows" / "foo.json")
    assert _locate_workflow_dir(Path("foo.json"), tmp_path) == flat


def test_repo_relative_path_resolves_directly(tmp_path):
    sub = _touch(tmp_path / "opencellcomms_adapters" / "X" / "workflows" / "suite" / "foo.json")
    _touch(tmp_path / "opencellcomms_adapters" / "Y" / "workflows" / "foo.json")
    rel = Path("opencellcomms_adapters/X/workflows/suite/foo.json")
    assert _locate_workflow_dir(rel, tmp_path) == sub


def test_ambiguous_bare_name_returns_none(tmp_path, capsys):
    _touch(tmp_path / "opencellcomms_adapters" / "X" / "workflows" / "foo.json")
    _touch(tmp_path / "opencellcomms_adapters" / "X" / "workflows" / "suite" / "foo.json")
    assert _locate_workflow_dir(Path("foo.json"), tmp_path) is None
    assert "several adapters" in capsys.readouterr().out
