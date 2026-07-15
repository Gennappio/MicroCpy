"""Drive one generation run: quarantine -> place MODEL.md -> prompt -> run the
coding agent (``claude -p``, full trace tee'd) -> locate the regenerated model.

The plumbing (workspace build, MODEL.md placement, biology-brief extraction, prompt
and command assembly, candidate location) is pure and unit-tested. The single
side-effecting step — spawning the coding agent — is one ``subprocess`` call whose
stdout (``--output-format stream-json --verbose``) is the ``trace.jsonl`` the whole
reasoning analysis runs on.

``--dry-run`` performs everything except the spawn and prints the exact command, so a
run can be inspected (and the quarantine audited) before any tokens are spent.

Gate handling by condition:
  * ``naked`` / ``no_protocol`` (entry: freeform)  -> single-shot: one agent call.
  * ``full`` / ``no_validator`` (entry: occ_new-model) -> gated: the simulated
    biologist answers the ``❓ NEEDS`` round and the preview gate via ``--resume``;
    each preview round-trip is one correction round. The gated loop needs a live run
    to validate end-to-end; start the smoke with ``naked`` to prove the pipeline
    cheaply, then enable gates for ``full``.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from evals.harness import _engine as E
from evals.harness import config as CFG
from evals.harness import workspace as WS
from evals.harness.biologist import Biologist


# --------------------------------------------------------------------------- MODEL.md
def biology_brief(model_md: str) -> str:
    """The Tier-2 input: the Provenance + Biology + Observables sections only — the
    agent must derive World/Resources/Agents/Scheduler/Init from these."""
    keep = ("## Provenance", "## Biology", "## Observables")
    out, emit = [], False
    for ln in model_md.splitlines():
        # the explicit divider between the brief and the Tier-1-only slots
        if "Everything below is Tier-1" in ln:
            break
        h = ln.strip()
        if h.startswith("## "):
            emit = any(h.startswith(k) for k in keep)
        # keep the model title (h1) and any line under an emitted biology section
        if (ln.startswith("# ") and not ln.startswith("## ")) or emit:
            out.append(ln)
    return "\n".join(out).strip()


def place_model_md(ws: WS.Workspace, case: dict, tier: str, source_md: str) -> Path:
    """Write the MODEL.md the agent will read into the quarantined plugin. Tier 1
    gets the whole spec; Tier 2 gets only the biology brief (and the agent must
    (re)produce the full MODEL.md itself)."""
    plugin = ws.root / case["plugin"]
    plugin.mkdir(parents=True, exist_ok=True)
    content = source_md if tier == "spec2code" else biology_brief(source_md)
    dest = plugin / "MODEL.md"
    dest.write_text(content, encoding="utf-8")
    return dest


def _source_model_md(case: dict) -> str:
    """The ground-truth MODEL.md: the plugin's if placed, else the staged draft."""
    placed = E.REPO_ROOT / case["model_md"]
    if placed.exists():
        return placed.read_text(encoding="utf-8")
    draft = E.REPO_ROOT / "evals" / "model_drafts" / f"{case['name'].upper()}.MODEL.md"
    if draft.exists():
        return draft.read_text(encoding="utf-8")
    raise FileNotFoundError(
        f"no MODEL.md for case '{case['name']}' (looked at {case['model_md']} and the "
        f"staged draft). Author it (Phase 0) and sign it off before generating.")


# --------------------------------------------------------------------------- prompt
def assemble_prompt(case: dict, condition: dict, tier: str, model_md_rel: str) -> str:
    """The coding agent's opening instruction, framed by the condition's entry mode."""
    plugin = case["plugin"]
    entry = condition.get("entry", "freeform")
    tier_note = (
        "The MODEL.md is the full structured spec (world, resources, agents, scheduler, "
        "initialization). Implement it."
        if tier == "spec2code" else
        "The MODEL.md gives ONLY the biology and the observables — you must derive the "
        "world, resources, agent kinds, creation, per-agent steps, scheduler order, and "
        "initialization yourself, then implement them."
    )
    if entry == "occ_new-model":
        return (
            f"Build the `{Path(plugin).name}` model in this OpenCellComms repo, following the "
            f"`/occ_new-model` authoring protocol. Its specification is at `{model_md_rel}`. "
            f"{tier_note}\n\n"
            f"Produce the workflow JSON under `{plugin}/workflows/` and the atomic node "
            f"functions under `{plugin}/functions/`, wire and register them, and validate. "
            f"I (the biologist) will answer your consequential questions and approve the "
            f"structure before you write code."
        )
    # freeform (no protocol): a generic coding-agent task
    return (
        f"Build a runnable OpenCellComms ABM for the `{Path(plugin).name}` model described in "
        f"`{model_md_rel}`. {tier_note}\n\n"
        f"Create the workflow JSON under `{plugin}/workflows/` and the Python functions under "
        f"`{plugin}/functions/`, register them, and make it runnable with "
        f"`python opencellcomms_engine/run_workflow.py --workflow <the json>`."
    )


def build_command(prompt: str, workspace: Path, model: str, effort: str = "high") -> List[str]:
    """The ``claude -p`` argv: headless, full stream (thinking + tools) for the trace,
    scoped to the workspace, permissions bypassed (isolated throwaway tree)."""
    return [
        "claude", "-p", prompt,
        "--output-format", "stream-json", "--verbose",
        "--model", model,
        "--effort", effort,
        "--dangerously-skip-permissions",
        "--add-dir", str(workspace),
    ]


# --------------------------------------------------------------------------- candidate
def locate_candidate_workflow(ws: WS.Workspace, case: dict) -> Optional[str]:
    """Find the regenerated workflow JSON in the quarantined plugin (the agent chose
    its own filename, so glob rather than assume)."""
    wf_dir = ws.root / case["plugin"] / "workflows"
    if not wf_dir.exists():
        return None
    jsons = sorted(wf_dir.glob("*.json"))
    return str(jsons[0]) if jsons else None


# --------------------------------------------------------------------------- run
@dataclass
class RunResult:
    case: str
    condition: str
    tier: str
    workspace: str
    prompt: str
    command: List[str]
    transcript: Optional[str] = None
    candidate_workflow: Optional[str] = None
    correction_rounds: int = 0
    spawned: bool = False
    quarantined_paths: List[str] = field(default_factory=list)
    identifiers: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def run(case_name: str, condition_name: str, tier: str, out_dir: Path,
        dry_run: bool = True) -> RunResult:
    """Prepare (and, unless ``dry_run``, execute) one generation run."""
    case = CFG.load_case(case_name)
    condition = CFG.load_condition(condition_name)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ws = WS.build_workspace(case, condition, out_dir / "workspace")
    source_md = _source_model_md(case)
    model_md = place_model_md(ws, case, tier, source_md)
    model_md_rel = str(Path(model_md).relative_to(ws.root))

    prompt = assemble_prompt(case, condition, tier, model_md_rel)
    gen = condition.get("generation") or {}
    command = build_command(prompt, ws.root, gen.get("model", "claude-fable-5"),
                            gen.get("effort", "high"))

    result = RunResult(
        case=case_name, condition=condition_name, tier=tier,
        workspace=str(ws.root), prompt=prompt, command=command,
        quarantined_paths=ws.quarantined_paths, identifiers=ws.identifiers,
    )
    if dry_run:
        return result

    transcript = out_dir / "trace.jsonl"
    _spawn(command, ws.root, transcript)
    result.spawned = True
    result.transcript = str(transcript)
    result.candidate_workflow = locate_candidate_workflow(ws, case)
    (out_dir / "run.json").write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    return result


def _spawn(command: List[str], cwd: Path, transcript: Path) -> None:
    """Run the coding agent, teeing its stream-json stdout to ``transcript``."""
    with open(transcript, "w", encoding="utf-8") as tf:
        subprocess.run(command, cwd=str(cwd), stdout=tf,
                       stderr=subprocess.STDOUT, text=True, check=False)


def _session_id_from_stream(transcript: Path) -> Optional[str]:
    """The session id emitted in the stream, for --resume in the gated loop."""
    for line in Path(transcript).read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        sid = rec.get("session_id") or rec.get("sessionId")
        if sid:
            return sid
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Prepare/execute one generation run.")
    ap.add_argument("--case", required=True)
    ap.add_argument("--condition", default="full")
    ap.add_argument("--tier", default="spec2code", choices=["spec2code", "bio2code"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--execute", action="store_true",
                    help="actually spawn the coding agent (spends tokens); default is dry-run")
    args = ap.parse_args(argv)

    result = run(args.case, args.condition, args.tier, Path(args.out), dry_run=not args.execute)
    print(f"case/condition/tier : {result.case}/{result.condition}/{result.tier}")
    print(f"workspace           : {result.workspace}")
    print(f"quarantined paths   : {len(result.quarantined_paths)}")
    print(f"leak identifiers    : {len(result.identifiers)}")
    print(f"\nprompt:\n{result.prompt}\n")
    print(f"command:\n  {' '.join(result.command[:2])} <prompt> " + " ".join(result.command[3:]))
    if result.spawned:
        print(f"\ntranscript          : {result.transcript}")
        print(f"candidate workflow  : {result.candidate_workflow}")
    else:
        print("\n[dry-run] not spawned. Re-run with --execute to generate (spends tokens).")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
