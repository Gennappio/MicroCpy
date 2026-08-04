import io
import queue
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "opencellcomms_gui" / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import api as api_module  # noqa: E402


@pytest.fixture()
def client():
    api_module.app.config.update(TESTING=True)
    return api_module.app.test_client()


@pytest.mark.parametrize(
    ("endpoint", "method", "payload"),
    [
        (
            "/api/function/source?name=x&file=../../CLAUDE.md",
            "get",
            None,
        ),
        (
            "/api/function/save",
            "post",
            {"name": "x", "source": "def x():\n    pass\n", "file": "../../outside.py"},
        ),
        (
            "/api/filesystem/write-file",
            "post",
            {"file_path": "../../outside.json", "content": "{}"},
        ),
        (
            "/api/function/scaffold",
            "post",
            {
                "file_path": "../../outside.py",
                "functions": [{"name": "outside"}],
            },
        ),
        (
            "/api/library/parse",
            "post",
            {"library_path": "../../outside.py"},
        ),
    ],
)
def test_filesystem_endpoints_reject_traversal(client, endpoint, method, payload):
    response = getattr(client, method)(endpoint, json=payload)

    assert response.status_code == 400


def test_filesystem_endpoints_reject_absolute_paths(client, tmp_path: Path):
    outside = tmp_path / "outside.py"
    outside.write_text("def outside():\n    return True\n", encoding="utf-8")

    source = client.get(
        "/api/function/source", query_string={"name": "outside", "file": str(outside)}
    )
    library = client.post("/api/library/parse", json={"library_path": str(outside)})
    write = client.post(
        "/api/filesystem/write-file",
        json={"file_path": str(outside), "content": "overwritten"},
    )

    assert source.status_code == 400
    assert library.status_code == 400
    assert write.status_code == 400
    assert outside.read_text(encoding="utf-8").startswith("def outside")
    assert not outside.with_suffix(".py.bak").exists()


def test_rejected_upload_creates_no_target_or_backup(client, tmp_path: Path):
    outside = tmp_path / "uploaded.py"

    response = client.post(
        "/api/function/upload",
        data={
            "function_name": "uploaded",
            "target_path": str(outside),
            "file": (io.BytesIO(b"def uploaded():\n    return True\n"), "uploaded.py"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert not outside.exists()
    assert not (tmp_path / "backups").exists()


def test_source_and_library_reads_work_inside_engine_tree(client):
    path = "opencellcomms_engine/src/workflow/registry.py"

    source = client.get(
        "/api/function/source", query_string={"name": "registry", "file": path}
    )
    library = client.post("/api/library/parse", json={"library_path": path})

    assert source.status_code == 200
    assert "class FunctionRegistry" in source.get_json()["source"]
    assert library.status_code == 200
    assert any(item["name"] == "discover_adapter_names" for item in library.get_json()["functions"])


def test_valid_engine_and_adapter_writes_stay_within_scoped_roots(
    client, tmp_path: Path, monkeypatch
):
    fake_repo = tmp_path / "repo"
    fake_engine = fake_repo / "opencellcomms_engine"
    engine_source = fake_engine / "src"
    adapters = fake_repo / "opencellcomms_adapters"
    engine_source.mkdir(parents=True)
    adapters.mkdir(parents=True)
    engine_file = engine_source / "editable.py"
    engine_file.write_text("def editable():\n    return 1\n", encoding="utf-8")

    monkeypatch.setattr(api_module, "REPO_ROOT", fake_repo)
    monkeypatch.setattr(api_module, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(api_module, "ENGINE_SOURCE_DIR", engine_source)
    monkeypatch.setattr(api_module, "ADAPTERS_DIR", adapters)
    monkeypatch.setattr(api_module, "EXPORTS_DIR", fake_engine / "exports")
    monkeypatch.setattr(
        api_module, "get_engine_path", lambda: fake_engine / "run_workflow.py"
    )
    monkeypatch.setattr(api_module, "_enabled_code_roots", lambda: [engine_source])

    save = client.post(
        "/api/function/save",
        json={
            "name": "editable",
            "file": "src/editable.py",
            "source": "def editable():\n    return 2\n",
        },
    )
    write = client.post(
        "/api/filesystem/write-file",
        json={
            "file_path": "opencellcomms_adapters/new_adapter/behavior.json",
            "content": "{}",
        },
    )

    assert save.status_code == 200
    assert "return 2" in engine_file.read_text(encoding="utf-8")
    assert engine_file.with_suffix(".py.bak").is_file()
    assert write.status_code == 200
    assert (adapters / "new_adapter" / "behavior.json").read_text() == "{}"


def test_source_save_rejects_backup_symlink_without_side_effects(
    client, tmp_path: Path, monkeypatch
):
    fake_repo = tmp_path / "repo"
    fake_engine = fake_repo / "opencellcomms_engine"
    engine_source = fake_engine / "src"
    engine_source.mkdir(parents=True)
    source = engine_source / "editable.py"
    source.write_text("def editable():\n    return 1\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("do not overwrite", encoding="utf-8")
    try:
        source.with_suffix(".py.bak").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    monkeypatch.setattr(api_module, "REPO_ROOT", fake_repo)
    monkeypatch.setattr(api_module, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(api_module, "ENGINE_SOURCE_DIR", engine_source)
    monkeypatch.setattr(
        api_module, "get_engine_path", lambda: fake_engine / "run_workflow.py"
    )
    monkeypatch.setattr(api_module, "_enabled_code_roots", lambda: [engine_source])

    response = client.post(
        "/api/function/save",
        json={
            "name": "editable",
            "file": "src/editable.py",
            "source": "def editable():\n    return 2\n",
        },
    )

    assert response.status_code == 400
    assert "return 1" in source.read_text(encoding="utf-8")
    assert outside.read_text(encoding="utf-8") == "do not overwrite"


def test_upload_rejects_backup_directory_symlink_without_side_effects(
    client, tmp_path: Path, monkeypatch
):
    fake_repo = tmp_path / "repo"
    fake_engine = fake_repo / "opencellcomms_engine"
    engine_source = fake_engine / "src"
    engine_source.mkdir(parents=True)
    source = engine_source / "editable.py"
    source.write_text("def editable():\n    return 1\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (engine_source / "backups").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    monkeypatch.setattr(api_module, "REPO_ROOT", fake_repo)
    monkeypatch.setattr(api_module, "ENGINE_DIR", fake_engine)
    monkeypatch.setattr(api_module, "ENGINE_SOURCE_DIR", engine_source)
    monkeypatch.setattr(
        api_module, "get_engine_path", lambda: fake_engine / "run_workflow.py"
    )
    monkeypatch.setattr(api_module, "_enabled_code_roots", lambda: [engine_source])

    response = client.post(
        "/api/function/upload",
        data={
            "function_name": "editable",
            "target_path": "src/editable.py",
            "file": (io.BytesIO(b"def editable():\n    return 2\n"), "editable.py"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
    assert "return 1" in source.read_text(encoding="utf-8")
    assert list(outside.iterdir()) == []


def test_valid_result_read_is_limited_to_runs(client, tmp_path: Path, monkeypatch):
    runs = tmp_path / "runs"
    plot = runs / "example" / "plot.png"
    plot.parent.mkdir(parents=True)
    plot.write_bytes(b"not-a-real-png-but-safe-to-serve")
    monkeypatch.setattr(api_module, "RUNS_DIR", runs)

    response = client.get("/api/results/plot/example/plot.png")

    assert response.status_code == 200
    assert response.data == b"not-a-real-png-but-safe-to-serve"


def test_result_listing_ignores_symlinked_artifacts(client, tmp_path: Path, monkeypatch):
    runs = tmp_path / "runs"
    group = runs / "example"
    group.mkdir(parents=True)
    outside = tmp_path / "secret.png"
    outside.write_bytes(b"secret")
    try:
        (group / "secret.png").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this platform")
    monkeypatch.setattr(api_module, "RUNS_DIR", runs)

    response = client.get("/api/results/list")

    assert response.status_code == 200
    assert response.get_json()["results"] == []


def test_resolver_rejects_prefix_confusion_and_symlink_escape(tmp_path: Path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    confusing = tmp_path / "allowed-other" / "file.py"
    confusing.parent.mkdir()
    confusing.write_text("", encoding="utf-8")

    with pytest.raises(api_module.PathPolicyError):
        api_module._resolve_allowed_path(
            confusing,
            roots=(allowed,),
            allow_absolute=True,
        )

    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "secret.py"
    target.write_text("secret = True\n", encoding="utf-8")
    link = allowed / "link.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks are not available on this platform")

    with pytest.raises(api_module.PathPolicyError):
        api_module._resolve_allowed_path(
            link,
            roots=(allowed,),
            allow_absolute=True,
        )


def test_results_and_observability_reject_escape_paths(client):
    plot = client.get("/api/results/plot/%2E%2E%2FCLAUDE.md")
    artifact = client.get(
        "/api/observability/artifact", query_string={"path": "../../CLAUDE.md"}
    )
    context = client.get(
        "/api/observability/context", query_string={"scopeKey": "../../escape"}
    )

    assert plot.status_code in {400, 404}
    assert artifact.status_code == 400
    assert context.status_code == 400


def test_observability_rejects_snapshot_symlink_escape(
    client, tmp_path: Path, monkeypatch
):
    obs = tmp_path / "observability"
    scope = obs / "context" / "main"
    scope.mkdir(parents=True)
    outside = tmp_path / "secret.json"
    outside.write_text('{"secret": true}', encoding="utf-8")
    try:
        (scope / "v000001.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are not available on this platform")
    monkeypatch.setattr(api_module, "get_observability_dir", lambda: obs)

    response = client.get(
        "/api/observability/context",
        query_string={"scopeKey": "main", "version": "1"},
    )

    assert response.status_code == 400
    assert b"secret" not in response.data


def test_cors_is_limited_to_local_vite_origins(client):
    allowed = client.get(
        "/api/health", headers={"Origin": "http://localhost:3000"}
    )
    rejected = client.get(
        "/api/health", headers={"Origin": "https://example.com"}
    )

    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert "Access-Control-Allow-Origin" not in rejected.headers


def test_registry_api_exposes_both_compatibility_contracts(client):
    response = client.get("/api/registry")

    assert response.status_code == 200
    functions = response.get_json()["functions"]
    assert functions
    for metadata in functions.values():
        assert "requires" in metadata
        assert "compatible_kernels" in metadata


def test_server_uses_loopback_and_disables_debug(monkeypatch):
    captured = {}
    monkeypatch.setattr(api_module.app, "run", lambda **kwargs: captured.update(kwargs))

    api_module.run_server()

    assert captured["host"] == "127.0.0.1"
    assert captured["debug"] is False
    assert captured["use_reloader"] is False


def test_gui_subprocess_reports_failed_exit_status():
    messages = queue.Queue()
    process = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(7)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    api_module.stream_output(process, messages)

    assert api_module.last_run_status == "failed"
    assert api_module.last_exit_code == 7
    queued = []
    while not messages.empty():
        queued.append(messages.get_nowait())
    assert any("[FAILED]" in message and "7" in message for message in queued)
