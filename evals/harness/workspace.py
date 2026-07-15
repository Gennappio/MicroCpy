"""Build a quarantined workspace for one generation run — the contamination control.

The benchmark answer is in this repo, and CLAUDE.md + /occ_new-model *tell the agent
to read the canonical workflows as examples* — including the target's own. Running a
generation against the live tree measures nothing. So each run gets an isolated copy:

  1. **Copy the repo tree without ``.git``** (so deleted files can't be recovered from
     history) and without the heavy/irrelevant dirs.
  2. **Strip the target plugin** to ``MODEL.md`` + declared inputs (``data/``,
     ``plugin.toml``): the agent must regenerate ``functions/``, ``workflows/``,
     ``behaviors/``, ``register.py`` from scratch.
  3. **Rewrite the reference lists** in ``CLAUDE.md`` and ``.claude/commands/*.md`` so
     the canonical-examples pointers name only the *other* models. Cross-model priming
     is the intended protocol; self-priming is the leak.
  4. **Apply the condition** (``full`` / ``no_validator`` / ``no_protocol`` / ``naked``):
     remove CLAUDE.md, the ``occ_*`` commands, the validator, and/or *all* example
     workflows as the condition dictates.

It returns the workspace path plus the **quarantine manifest** — the original-repo
paths and benchmark-distinctive identifiers that ``trace.detect_leaks`` treats as
out-of-bounds (an in-workspace read is impossible because the files are gone; this
catches an agent that reaches back to the original tree).
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from evals.harness import _engine as E

# Small, mutable/quarantined top-level items are COPIED (the agent edits these, or
# we strip/rewrite them). The heavy, immutable engine + GUI are SYMLINKED — a valid
# generation run never edits engine code, and the 1.5 GB results/ tree must never be
# copied. This keeps a workspace ~5 MB instead of ~100 MB and dodges slow-FS copies.
_COPY_DIRS = ["opencellcomms_adapters", ".claude", "docs"]
_COPY_FILES = ["CLAUDE.md", "README.md", "setup.py", "requirements.txt",
               "FIRST_STEPS.md", "run.sh", "install.sh"]
_SYMLINK = ["opencellcomms_gui"]  # engine handled specially (scripts/ copied)
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak", ".pytest_cache")


@dataclass
class Workspace:
    root: Path
    case: str
    condition: str
    quarantined_paths: List[str] = field(default_factory=list)   # original-repo paths, off-limits
    identifiers: List[str] = field(default_factory=list)          # benchmark-distinctive strings
    stripped: List[str] = field(default_factory=list)
    rewrote: List[str] = field(default_factory=list)
    manifest: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "root": str(self.root), "case": self.case, "condition": self.condition,
            "quarantined_paths": self.quarantined_paths, "identifiers": self.identifiers,
            "stripped": self.stripped, "rewrote": self.rewrote, "manifest": self.manifest,
        }


def build_workspace(case: dict, condition: dict, dest: Path,
                    source_root: Optional[Path] = None) -> Workspace:
    """Materialize a quarantined workspace under ``dest`` for one (case, condition)."""
    source_root = Path(source_root or E.REPO_ROOT)
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    _provision_tree(source_root, dest)

    ws = Workspace(root=dest, case=case["name"], condition=condition["id"])
    plugin_ws = dest / case["plugin"]

    _strip_target(plugin_ws, case, ws, source_root)
    _record_identifiers(case, ws, source_root)
    _rewrite_references(dest, case, condition, ws)
    _apply_condition(dest, case, condition, ws)

    (dest / ".eval_manifest.json").write_text(
        __import__("json").dumps(ws.to_dict(), indent=2), encoding="utf-8")
    return ws


def _provision_tree(source_root: Path, dest: Path) -> None:
    """Copy the small mutable/quarantined items; symlink the heavy immutable ones.

    The engine is symlinked child-by-child EXCEPT ``scripts/`` (copied, 48 KB) so
    the validator can be physically removed for the no_validator/naked conditions,
    and except ``results/`` (1.5 GB) which is never provisioned."""
    for name in _COPY_DIRS:
        src = source_root / name
        if src.exists():
            shutil.copytree(src, dest / name, ignore=_IGNORE, symlinks=True,
                            ignore_dangling_symlinks=True)
    for name in _COPY_FILES:
        src = source_root / name
        if src.exists():
            shutil.copy(src, dest / name)
    for name in _SYMLINK:
        src = source_root / name
        if src.exists():
            (dest / name).symlink_to(src)

    # engine: symlink every child except scripts/ (copied) and results/ (skipped)
    eng_src = source_root / "opencellcomms_engine"
    eng_dst = dest / "opencellcomms_engine"
    eng_dst.mkdir()
    for child in eng_src.iterdir():
        if child.name == "results":
            continue
        if child.name == "scripts":
            shutil.copytree(child, eng_dst / child.name, ignore=_IGNORE)
        else:
            (eng_dst / child.name).symlink_to(child)


def _strip_target(plugin_ws: Path, case: dict, ws: Workspace, source_root: Path) -> None:
    """Remove the target plugin's generated code; keep MODEL.md + declared inputs."""
    strip = set((case.get("quarantine") or {}).get("strip") or [])
    for item in strip:
        target = plugin_ws / item
        original = source_root / case["plugin"] / item
        if target.exists():
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            ws.stripped.append(str(Path(case["plugin"]) / item))
        # the ORIGINAL location is what an agent could leak by reading the live tree
        if original.exists():
            ws.quarantined_paths.append(str(original))


def _record_identifiers(case: dict, ws: Workspace, source_root: Path) -> None:
    """Benchmark-distinctive strings: the target's own function/subworkflow names.
    Their appearance in the agent's reads/output before it invented them is a leak."""
    bench = source_root / case["benchmark_workflow"]
    ws.quarantined_paths.append(str(bench))
    try:
        doc = E.load_workflow_json(bench)
    except Exception:
        return
    names = set((doc.get("subworkflows") or {}).keys())
    names.discard("main")
    names = {n for n in names if not n.startswith("__")}
    for sw in (doc.get("subworkflows") or {}).values():
        for f in sw.get("functions") or []:
            if f.get("function_name"):
                names.add(f["function_name"])
    # keep only distinctive (>4 char, not generic engine funcs) identifiers
    generic = {"setup_world", "plot_world", "setup_resource", "plot_resources",
               "plot_agents", "apply_reconciliation", "write_run_summary"}
    ws.identifiers = sorted(n for n in names if len(n) > 4 and n not in generic)


def _rewrite_references(dest: Path, case: dict, condition: dict, ws: Workspace) -> None:
    """In CLAUDE.md and the /occ_* commands, drop the target's own workflow from the
    canonical-examples lists so the agent is primed only from the OTHER models."""
    target_wf = Path(case["benchmark_workflow"]).name           # e.g. sugarscape.json
    files = [dest / "CLAUDE.md"] + sorted((dest / ".claude" / "commands").glob("*.md"))
    for f in files:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        # remove any line mentioning the target workflow filename (the example pointer)
        new = "\n".join(ln for ln in text.splitlines()
                        if target_wf not in ln)
        if new != text:
            f.write_text(new, encoding="utf-8")
            ws.rewrote.append(str(f.relative_to(dest)))


def _apply_condition(dest: Path, case: dict, condition: dict, ws: Workspace) -> None:
    """Remove scaffold elements the condition withholds."""
    sc = condition.get("scaffold") or {}
    ws.manifest["scaffold"] = sc

    if not sc.get("claude_md", True):
        _rm(dest / "CLAUDE.md")
        ws.manifest.setdefault("removed", []).append("CLAUDE.md")

    if not sc.get("occ_protocols", True):
        cmds = dest / ".claude" / "commands"
        removed = []
        for f in cmds.glob("occ_*.md") if cmds.exists() else []:
            _rm(f)
            removed.append(f.name)
        ws.manifest.setdefault("removed", []).extend(removed)

    if not sc.get("validator", True):
        _rm(dest / "opencellcomms_engine" / "scripts" / "validate_workflow.py")
        ws.manifest.setdefault("removed", []).append("scripts/validate_workflow.py")

    if not sc.get("canonical_examples", True):
        # strip ALL adapter workflows — no examples at all (the naked baseline)
        n = 0
        for wf in (dest / "opencellcomms_adapters").glob("*/workflows/*.json"):
            _rm(wf)
            n += 1
        ws.manifest["stripped_all_example_workflows"] = n
    else:
        # keep only the allowed cross-model examples; strip every other adapter's
        # workflows so the agent can't wander into an unrelated model either.
        allowed = set((case.get("reference_rewrite") or {}).get("allowed_examples") or [])
        allowed_dirs = {str(a) for a in allowed}
        target_dir = Path(case["plugin"]).name
        for wf in (dest / "opencellcomms_adapters").glob("*/workflows/*.json"):
            plugin_name = wf.parent.parent.name
            if plugin_name == target_dir or (allowed and plugin_name not in allowed_dirs):
                _rm(wf)


def _rm(p: Path) -> None:
    if p.exists():
        p.unlink() if p.is_file() else shutil.rmtree(p)
