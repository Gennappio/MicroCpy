"""Execute workflow-owned Planner definitions from the GUI, CLI and scheduler.

A configuration owns biological parameters. A replicate owns a seed. Attempts
are retained independently, and never counted as additional observations. The
workflow JSON is the only editable plan; batch metadata is an immutable record
of what the runner resolved and executed.
"""
import copy
import contextlib
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .planner import apply_overrides, enabled_tabs, planner_tabs
from .randomness import RNG_SCHEME

REPO = Path(__file__).resolve().parents[3]
DEFAULT_REPLICATION = {"replicates": 1, "seedMode": "generated", "masterSeed": "42",
                       "pairing": "shared", "pairingGroup": "default", "seeds": []}
INTERNAL_DIRECTORY = ".opencellcomms"
EXECUTION_RECORD = "execution.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def integer(value, label, minimum=1, maximum=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label} must be an integer") from None
    if isinstance(value, bool) or str(value).strip() != str(parsed):
        raise ValueError(f"{label} must be an integer")
    value = int(value)
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{label} must be between {minimum} and {maximum or 'an integer'}")
    return value


def replication_settings(workflow):
    planner = workflow.get("metadata", {}).get("gui", {}).get("planner", {})
    if planner.get("version", 1) not in (1, 2):
        raise ValueError("Unsupported Planner version")
    settings = {**DEFAULT_REPLICATION, "masterSeed": str(workflow.get("seed") or 42),
                "seedMode": "fresh" if workflow.get("seed") == 0 else "generated",
                **(planner.get("replication") or {})}
    if settings["seedMode"] not in ("generated", "explicit", "fresh"):
        raise ValueError("Seed mode must be generated, explicit or fresh")
    if settings["pairing"] not in ("shared", "independent"):
        raise ValueError("Pairing must be shared or independent")
    settings["replicates"] = integer(settings["replicates"], "Replicates", maximum=10000)
    if settings["seedMode"] == "explicit":
        seeds = settings.get("seeds")
        if not isinstance(seeds, list) or not seeds:
            raise ValueError("Enter a non-empty explicit seed list")
        settings["seeds"] = [str(integer(v, "Seed", maximum=2**128-1)) for v in seeds]
        if len(set(settings["seeds"])) != len(seeds):
            raise ValueError("Duplicate seeds are replays, not independent replicates")
        settings["replicates"] = len(seeds)
        if settings["pairing"] != "shared":
            raise ValueError("Explicit seeds are shared across configurations")
    elif settings["seedMode"] == "generated":
        settings["masterSeed"] = str(integer(settings["masterSeed"], "Master seed", maximum=2**128-1))
    return settings


def replicate_seed(settings, tab_id, replicate):
    if settings["seedMode"] == "explicit":
        return settings["seeds"][replicate - 1]
    identity = [RNG_SCHEME, settings["masterSeed"], settings["pairingGroup"], replicate]
    if settings["pairing"] == "independent":
        identity.append(tab_id)
    return str(int(digest(identity)[:32], 16) or 1)


def semantic_workflow(document):
    """Ignore canvas presentation, never arbitrary biological parameter keys."""
    result = copy.deepcopy(document)
    for key in ("name", "description", "seed"):
        result.pop(key, None)
    # GUI also owns biological routing (agent/resource kinds, world and
    # scheduler), so remove only Planner settings and known view state.
    metadata = result.setdefault("metadata", {})
    for key in ("workflow_source_path", "replicate"):
        metadata.pop(key, None)
    gui = metadata.get('gui', {})
    for key in ('planner', 'viewport', 'currentStage', 'currentMainTab', 'node_positions'):
        gui.pop(key, None)
    for sw in result.get("subworkflows", {}).values():
        for obj in [sw, sw.get("controller", {})] + [
            n for key in ("functions", "parameters", "subworkflow_calls")
            for n in (sw.get(key) or [])]:
            for key in ("label", "description", "position", "custom_name", "color"):
                obj.pop(key, None)
    return result


def _resolve_inputs(document, source, destination=None):
    """Freeze existing path-valued parameters; use content identities for matching.

    Only existing files are inputs. Output directories and scalar strings stay
    untouched. Relative resolution is shared with the workflow executor.
    """
    from .executor import create_path_resolver, _locate_workflow_dir
    source = Path(source or document.get("metadata", {}).get("workflow_source_path") or "")
    directory = _locate_workflow_dir(source, REPO) or (source.parent if source.is_file() else None)
    resolve = create_path_resolver(REPO / "opencellcomms_engine", directory)
    files = {}
    def visit(value, key=""):
        if isinstance(value, dict):
            return {k: visit(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [visit(v, key) for v in value]
        if not isinstance(value, str) or not any(t in key.lower() for t in ("file", "path")):
            return value
        if key in ("workflow_source_path", "csv_filename", "plot_filename") or not value.strip():
            return value
        if Path(value).suffix.lower() not in {".csv", ".bnd", ".cfg", ".json", ".yaml", ".yml", ".npz", ".npy", ".xml", ".txt", ".vtk", ".py"}:
            return value
        path = resolve(value)
        if not path.is_file():
            return value
        if not path.resolve().is_relative_to(REPO):
            raise ValueError(f"Input must be inside the project before freezing: {value}")
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        files[sha] = {"sha256": sha, "source": str(path.resolve()), "name": path.name}
        if destination:
            target = Path(destination) / "inputs" / (sha + path.suffix)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                shutil.copyfile(path, target)
            if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                raise ValueError(f'Input changed while copying: {path}')
            return str(target.resolve())
        return "sha256:" + sha
    return visit(copy.deepcopy(document)), files


def compile_plan(documents, fresh_seed=None):
    """Pure plan expansion; no simulation and no output mutation."""
    runs, configurations, requests, seen = [], {}, [], {}
    fresh_seed = str(fresh_seed or secrets.randbits(128) or 1)
    for entry in documents:
        workflow = entry["workflow"]
        source = entry.get("source", "")
        settings = replication_settings(workflow)
        if settings["seedMode"] == "fresh":
            settings = {**settings, "seedMode": "generated", "masterSeed": fresh_seed}
        tabs = enabled_tabs(workflow)
        if not tabs and planner_tabs(workflow):
            continue
        if not tabs:
            tabs = [{"id": "canvas", "name": workflow.get("name", "Canvas"), "parameterOverrides": {}}]
        if len({t.get("id") for t in tabs}) != len(tabs) or any(not t.get("id") for t in tabs):
            raise ValueError("Planner configurations need unique persistent IDs")
        references = [t for t in tabs if t.get("role") == "reference"]
        if len(references) > 1:
            raise ValueError("Select at most one reference configuration per workflow")
        for tab in tabs:
            override = tab.get("replicationOverride")
            count = integer(settings["replicates"] if override is None else override, "Replicates", maximum=10000)
            if settings["seedMode"] == "explicit" and count > len(settings["seeds"]):
                raise ValueError("Replicate override exceeds the explicit seed list")
            effective = apply_overrides(workflow, tab.get("parameterOverrides") or {})
            normalized, inputs = _resolve_inputs(effective, source)
            config_id = digest(semantic_workflow(normalized))[:24]
            label = str(tab.get("name") or tab["id"])
            config = configurations.setdefault(config_id, {"id": config_id, "name": label,
                "aliases": [], "role": tab.get("role", "configuration"),
                "source": source, "workflow": effective, "inputs": inputs})
            if label not in config["aliases"]:
                config["aliases"].append(label)
            if tab.get("role") == "reference":
                config["role"] = "reference"
            spec = {"configuration_id": config_id, "tab_id": tab["id"], "name": label,
                    "settings": settings, "replicates": count,
                    "source": source or workflow.get("metadata", {}).get("workflow_source_path", "")}
            requests.append(spec)
            seeds = [replicate_seed(settings, tab["id"], r) for r in range(1, count+1)]
            if len(seeds) != len(set(seeds)):
                raise ValueError("Seed collision within a configuration")
            for replicate, seed in enumerate(seeds, 1):
                identity = digest([config_id, seed, RNG_SCHEME])[:32]
                if identity in seen:
                    continue
                run = {"id": identity, "configuration_id": config_id, "replicate": replicate,
                       "seed": seed, "pairing": settings["pairing"], "pairing_group": settings["pairingGroup"]}
                seen[identity] = run
                runs.append(run)
    if sum(c.get('role') == 'reference' for c in configurations.values()) > 1:
        raise ValueError('A batch supports one distinct reference configuration')
    if not runs:
        raise ValueError("Enable at least one Planner configuration")
    if len(runs) > 100000:
        raise ValueError("A batch may contain at most 100000 runs")
    return {"version": 1, "rng_scheme": RNG_SCHEME, "runs": runs,
            "configurations": list(configurations.values()), "requests": requests,
            "requested_runs": sum(r["replicates"] for r in requests),
            "unique_runs": len(runs)}


def code_files():
    paths = set()
    for root in [REPO / "opencellcomms_engine/src", REPO / "opencellcomms_engine/tools", REPO / "opencellcomms_adapters"]:
        paths.update(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)
        paths.update(root.rglob("plugin.toml"))
    paths.update((REPO / "opencellcomms_engine").glob("*.py"))
    return sorted(paths)


def code_fingerprint():
    return digest({str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in code_files()})


def environment():
    versions = {}
    for name in ("numpy", "scipy", "fipy", "pandas", "matplotlib", "networkx", "PyYAML", "maboss", "pymaboss"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    return {"python": sys.version, "platform": platform.platform(), "packages": versions,
            "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}}


def folder_name(name):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', str(name)).strip('._-')[:80] or 'configuration'


def batch_display_name(manifest):
    title = manifest.get('name')
    if not title:
        sources = {Path(c['source']).stem for c in manifest['configurations'] if c.get('source')}
        title = next(iter(sources)) if len(sources) == 1 else 'Experiment'
    created = manifest.get('created_at')
    date = datetime.fromisoformat(created).astimezone().strftime('%Y-%m-%d %H:%M:%S') if created else ''
    return f'{title} · {date}' if date else title


def _assign_run_folders(plan):
    """Readable paths are presentation; hashes and seeds retain their identities."""
    configs = {c['id']: c for c in plan['configurations']}
    counts = {}
    for run in plan['runs']:
        config_id = run['configuration_id']
        counts[config_id] = counts.get(config_id, 0) + 1
        folder = configs[config_id].get('output_folder')
        if folder and 'output_dir' not in run:
            run['output_index'] = counts[config_id]
            run['output_dir'] = f"{folder}/replicate-{counts[config_id]:03d}"


def _assign_configuration_folders(plan):
    """Give every effective configuration one readable, collision-free folder."""
    used = {INTERNAL_DIRECTORY}
    for config in plan['configurations']:
        base = folder_name(config['name'])
        if re.fullmatch(r'plan-\d+\.json', base, re.IGNORECASE):
            base = 'configuration_' + base
        folder, suffix = base, 1
        while folder.casefold() in used:
            suffix += 1
            folder = f'{base}_{suffix}'
        used.add(folder.casefold())
        config['output_folder'] = folder
    _assign_run_folders(plan)


def _new_experiment_directory(runs_dir, name):
    base = folder_name(name).replace('.', '_') + datetime.now().strftime('_%Y-%m-%d_%H-%M-%S')
    suffix = 1
    while True:
        folder = base if suffix == 1 else f'{base}_{suffix}'
        path = Path(runs_dir).resolve() / folder
        try:
            path.mkdir(parents=True)
            return path
        except FileExistsError:
            suffix += 1


def run_directory(batch, run):
    # Older batches retain their original paths and remain readable.
    return Path(batch) / run.get('output_dir', f"{run['configuration_id']}/{run['id']}")


def execution_record_path(batch):
    """Return the hidden execution record, or a legacy manifest when present."""
    batch = Path(batch)
    current = batch / INTERNAL_DIRECTORY / EXECUTION_RECORD
    legacy = batch / "manifest.json"
    return current if current.is_file() or not legacy.is_file() else legacy


def internal_directory(batch):
    """Internal storage for new batches; legacy batches kept theirs at the root."""
    record = execution_record_path(batch)
    return record.parent if record.name == EXECUTION_RECORD else Path(batch)


def read_execution_record(batch):
    return read_json(execution_record_path(batch))


def batch_directory_from_record(record):
    record = Path(record).resolve()
    return record.parent.parent if record.parent.name == INTERNAL_DIRECTORY else record.parent


def create_batch(documents, runs_dir, plan=None):
    plan = copy.deepcopy(plan or compile_plan(documents))
    names = {c['workflow'].get('name') or 'Experiment' for c in plan['configurations']}
    plan['name'] = next(iter(names)) if len(names) == 1 else 'Experiments'
    batch = _new_experiment_directory(runs_dir, plan['name'])
    batch_id = batch.name
    internal = batch / INTERNAL_DIRECTORY
    _assign_configuration_folders(plan)
    for config in plan["configurations"]:
        folder = config['output_folder']
        frozen, inputs = _resolve_inputs(config.pop("workflow"), config["source"], internal)
        if set(inputs) != set(config['inputs']):
            raise ValueError('Inputs changed while saving the workflows; launch again')
        target = internal / "workflows" / (folder + ".json")
        write_json(target, frozen)
        config["workflow_file"] = str(target.relative_to(batch))
        config["workflow_hash"] = digest(frozen)
        config["inputs"] = inputs
    source_hash = code_fingerprint()
    with tarfile.open(internal / "source.tar.gz", "w:gz") as archive:
        for path in code_files():
            archive.add(path, arcname=str(path.relative_to(REPO)))
    if source_hash != code_fingerprint():
        raise ValueError('Source changed while saving the run; launch again')
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True)
    plan.update(batch_id=batch_id, created_at=now(), code_hash=source_hash,
                git_revision=git.stdout.strip(), environment=environment())
    write_json(internal / EXECUTION_RECORD, plan)
    return batch


def attempt_dirs(batch, run):
    parent = run_directory(batch, run)
    attempts = [parent] if (parent / "status.json").is_file() else []
    attempts.extend(sorted(parent.glob("attempt-*")))  # legacy batches
    attempts.extend(sorted(parent.glob("retry-*")))  # early development layout
    attempts.extend(sorted(parent.parent.glob(parent.name + "_retry-*")))
    return attempts


def run_status(batch, run):
    attempts = attempt_dirs(batch, run)
    statuses = []
    for path in attempts:
        if (path / "status.json").is_file():
            status = read_json(path / "status.json")
            if status.get("status") == "running" and status.get("host") == socket.gethostname():
                try:
                    os.kill(status["pid"], 0)
                except ProcessLookupError:
                    status["status"] = "interrupted"
            status["attempt_dir"] = str(path.relative_to(batch))
            statuses.append(status)
    successful = [s for s in statuses if s.get("status") == "completed" and s.get("numerical_valid") is not False and s.get("replay_matches") is not False]
    # A failed replay never erases the earlier successful observation.
    selected = successful[-1] if successful else (statuses[-1] if statuses else {"status": "planned"})
    return {**run, **selected, "attempts": statuses}


def batch_status(batch):
    manifest = read_execution_record(batch)
    states = [run_status(batch, r) for r in manifest["runs"]]
    return {**manifest, "runs": states,
            "replay_mismatches": sum(a.get("replay_matches") is False for s in states for a in s["attempts"]),
            "completed": sum(s["status"] == "completed" and s.get("numerical_valid") is not False for s in states),
            "failed": sum(s["status"] in ("failed", "cancelled", "interrupted") or s.get("numerical_valid") is False for s in states)}


def execute_run(batch, run, manifest, replay=False):
    """Run one fresh process per attempt and prevent concurrent duplicates."""
    batch = Path(batch).resolve()
    parent = run_directory(batch, run)
    parent.mkdir(parents=True, exist_ok=True)
    lock = parent / ".claim"
    with batch_mutation_lock(batch):
        latest = run_status(batch, run)
        if not replay and latest['status'] == 'completed' and latest.get('numerical_valid') is not False:
            return True
        if lock.exists():
            owner = read_json(lock)
            alive = True
            if owner.get('host') == socket.gethostname():
                try:
                    os.kill(owner['pid'], 0)
                except ProcessLookupError:
                    alive = False
            if alive:
                raise RuntimeError(f"Replicate {run['id']} is already claimed on {owner.get('host')}")
            lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump({'pid': os.getpid(), 'host': socket.gethostname()}, stream)
        attempts = attempt_dirs(batch, run)
        if execution_record_path(batch).parent.name == INTERNAL_DIRECTORY and not attempts:
            attempt = parent
        else:
            if execution_record_path(batch).parent.name == INTERNAL_DIRECTORY:
                attempt = parent.with_name(parent.name + f"_retry-{len(attempts)+1:03d}")
            else:
                attempt = parent / f"attempt-{len(attempts)+1:03d}"
            attempt.mkdir()
        state = {'status': 'running', 'started_at': now(), 'seed': run['seed'],
                 'pid': os.getpid(), 'host': socket.gethostname(), 'environment': environment()}
        write_json(attempt / 'status.json', state)
    prior = run_status(batch, run)
    process = None
    try:
        config = next(c for c in manifest["configurations"] if c["id"] == run["configuration_id"])
        workflow = read_json(batch / config["workflow_file"])
        if digest(workflow) != config["workflow_hash"]:
            raise ValueError("Frozen configuration has been modified")
        for sha, info in config["inputs"].items():
            frozen_input = internal_directory(batch) / "inputs" / (sha + Path(info["name"]).suffix)
            if hashlib.sha256(frozen_input.read_bytes()).hexdigest() != sha:
                raise ValueError(f"Frozen input has been modified: {info['name']}")
        # Frozen workflows are portable when the experiment directory moves.
        # Verify their stored hash first, then rebase only known snapshot paths.
        input_names = {sha + Path(info['name']).suffix for sha, info in config['inputs'].items()}
        def rebase(value):
            if isinstance(value, dict):
                return {k: rebase(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rebase(v) for v in value]
            if isinstance(value, str) and Path(value).name in input_names:
                return str(internal_directory(batch) / 'inputs' / Path(value).name)
            return value
        workflow = rebase(workflow)
        workflow["seed"] = int(run["seed"])
        workflow.setdefault("metadata", {})["replicate"] = {**run, "batch_id": manifest["batch_id"], "rng_scheme": RNG_SCHEME}
        write_json(attempt / "workflow.json", workflow)
        command = [sys.executable, str(REPO / "opencellcomms_engine/tools/run_sim.py"),
                   "--workflow", str(attempt / "workflow.json"), "--no-planner", "--no-observability",
                   "--gui-results-dir", str(attempt)]
        env = {**os.environ, "PYTHONHASHSEED": "0", "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg"}
        process = subprocess.Popen(command, cwd=REPO / "opencellcomms_engine", env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        with (attempt / "run.log").open("w", encoding="utf-8") as output:
            for line in process.stdout:
                output.write(line)
                print(line, end="", flush=True)
        code = process.wait()
        execution = read_json(attempt / "execution.json") if (attempt / "execution.json").exists() else {}
        state.update(status="completed" if code == 0 and execution.get("status") == "completed" else "failed",
                     exit_code=code, numerical_valid=execution.get("numerical_valid"), execution=execution)
        if manifest['code_hash'] != code_fingerprint():
            state.update(status='failed', numerical_valid=False, error='Source changed during this attempt')
        state["metrics"] = endpoint_metrics(attempt)
        if prior['status'] == 'completed' and state['status'] == 'completed':
            state['replay_matches'] = prior.get('metrics', {}) == state['metrics']
    except BaseException as exc:
        state["status"] = "cancelled" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed"
        state["error"] = str(exc)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        raise
    finally:
        state["finished_at"] = now()
        write_json(attempt / "status.json", state)
        lock.unlink(missing_ok=True)
    return state["status"] == "completed" and state.get("numerical_valid") is not False


def execute_batch(batch, action="continue", run_id=None, index=None):
    batch = Path(batch).resolve()
    manifest = read_execution_record(batch)
    if manifest["code_hash"] != code_fingerprint():
        raise ValueError("Model code changed since this batch was saved. Return to its recorded code version or create a new batch.")
    recorded, current = manifest['environment'], environment()
    if (recorded['python'].split()[0] != current['python'].split()[0]
            or recorded['packages'] != current['packages']
            or recorded['threads'] != current['threads']):
        raise ValueError('Python, package versions or thread settings differ from the saved environment. Restore that environment or create a new batch.')
    selected = manifest["runs"]
    if index is not None:
        if index < 0 or index >= len(selected):
            raise ValueError("Run index is outside the execution record")
        selected = [selected[index]]
    if run_id:
        selected = [r for r in selected if r["id"] == run_id]
        if not selected:
            raise ValueError("Unknown replicate identity")
    if action == "replay" and not run_id:
        raise ValueError("Replay requires one replicate identity")
    ok = True
    for run in selected:
        if manifest["code_hash"] != code_fingerprint():
            raise ValueError("Model code changed during execution; remaining replicates were not started")
        state = run_status(batch, run)
        valid = state["status"] == "completed" and state.get("numerical_valid") is not False
        if action != "replay" and valid:
            continue
        if action == "retry" and state["status"] == "planned":
            continue
        config = next(c for c in manifest['configurations'] if c['id'] == run['configuration_id'])
        print(f"[PLANNER] {config['name']} / Replicate {run.get('output_index', run['replicate'])}", flush=True)
        ok = execute_run(batch, run, manifest, replay=action == "replay") and ok
    return 0 if ok else 1


def endpoint_metrics(attempt):
    """One endpoint per recorded time series, retaining the endpoint coordinate.

    This reads reporters' existing output; it does not redefine biological
    metrics or count time points/cells as independent observations.
    """
    metrics = {}
    for path in sorted(Path(attempt).glob('*/timeseries/*.csv')):
        with path.open(newline='', encoding='utf-8') as stream:
            last = None
            for row in csv.DictReader(stream):
                last = row
        if not last:
            continue
        coordinate = next((k for k in ('gene_steps', 'iteration', 'time', 'step') if k in last), None)
        endpoint = [coordinate, last[coordinate]] if coordinate else None
        for key, value in last.items():
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(number):
                metrics[f'{path.relative_to(attempt)}:{key}'] = {'value': number, 'endpoint': endpoint}
    return metrics


def sample_summary(values):
    import statistics
    n = len(values)
    if not n:
        return {'n': 0, 'mean': None, 'sd': None, 'ci95': None}
    mean = statistics.mean(values)
    if n < 2:
        return {'n': n, 'mean': mean, 'sd': None, 'ci95': None}
    from scipy.stats import t
    sd = statistics.stdev(values)
    width = float(t.ppf(0.975, n-1)) * sd / math.sqrt(n)
    return {'n': n, 'mean': mean, 'sd': sd, 'ci95': [mean-width, mean+width]}


def summarize_batch(batch, metric=None):
    state = batch_status(batch)
    valid = [r for r in state['runs'] if r['status'] == 'completed' and r.get('numerical_valid') is not False]
    available = sorted({key for r in valid for key in r.get('metrics', {})})
    metric = metric or (available[0] if available else None)
    reference = next((c['id'] for c in state['configurations'] if c.get('role') == 'reference'), None)
    def observations(config_id):
        return [r for r in valid if r['configuration_id'] == config_id and metric in r.get('metrics', {})]
    refs = {(r['seed'], r['pairing_group']): r for r in observations(reference) if r['pairing'] == 'shared'}
    reference_records = observations(reference)
    reference_endpoints = {json.dumps(r['metrics'][metric]['endpoint']) for r in reference_records}
    groups = []
    for config in state['configurations']:
        records = observations(config['id'])
        # Do not silently pool endpoints from different horizons.
        endpoints = {json.dumps(r['metrics'][metric]['endpoint']) for r in records}
        values = [r['metrics'][metric]['value'] for r in records] if len(endpoints) <= 1 else []
        differences = []
        for r in records:
            ref = refs.get((r['seed'], r['pairing_group'])) if r['pairing'] == 'shared' else None
            if ref and ref['metrics'][metric]['endpoint'] == r['metrics'][metric]['endpoint']:
                differences.append(r['metrics'][metric]['value'] - ref['metrics'][metric]['value'])
        independent = (records and reference_records and config['id'] != reference
                       and all(r['pairing'] == 'independent' for r in records + reference_records)
                       and len(endpoints) == 1 and endpoints == reference_endpoints)
        unpaired = independent_difference(values, [r['metrics'][metric]['value'] for r in reference_records]) if independent else None
        groups.append({'id': config['id'], 'name': config['name'], 'aliases': config['aliases'],
            'planned': sum(r['configuration_id'] == config['id'] for r in state['runs']),
            'valid': sum(r['configuration_id'] == config['id'] for r in valid),
            'endpoint': json.loads(next(iter(endpoints))) if len(endpoints) == 1 else None,
            'mixed_endpoints': len(endpoints) > 1, **sample_summary(values),
            'independent_difference': unpaired,
            'paired_difference': sample_summary(differences) if reference and reference != config['id'] and not independent else None})
    return {'metric': metric, 'available_metrics': available, 'reference_id': reference, 'groups': groups,
            'interval_method': '95% Student t interval across independent replicate endpoints; paired intervals use matched seed differences; independent contrasts use Welch intervals.'}


@contextlib.contextmanager
def batch_mutation_lock(batch):
    """Serialize replicate claims on the same shared filesystem."""
    lock = internal_directory(batch) / '.batch-lock'
    for _ in range(200):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            time.sleep(0.05)
    else:
        raise ValueError('The batch is locked. If a worker was killed, inspect .batch-lock before removing it.')
    with os.fdopen(fd, 'w') as stream:
        json.dump({'pid': os.getpid(), 'host': socket.gethostname()}, stream)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def independent_difference(treatment, reference):
    import statistics
    from scipy.stats import t
    n, m = len(treatment), len(reference)
    mean = statistics.mean(treatment) - statistics.mean(reference)
    result = {'n': n, 'reference_n': m, 'mean': mean, 'ci95': None}
    if min(n, m) < 2:
        return result
    a, b = statistics.variance(treatment)/n, statistics.variance(reference)/m
    if a + b == 0:
        result['ci95'] = [mean, mean]
    else:
        df = (a+b)**2 / (a*a/(n-1) + b*b/(m-1))
        width = float(t.ppf(0.975, df)) * math.sqrt(a+b)
        result['ci95'] = [mean-width, mean+width]
    return result
