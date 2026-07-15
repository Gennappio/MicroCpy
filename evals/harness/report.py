"""Assemble a per-run **failure dossier** — the harness's headline deliverable.

For one regenerated model it composes the four axes into a single narrative that
answers the user's actual question: *where did the coding agent's reasoning break,
and why?* Each defect (from conformance + fidelity) is tied, through the transcript,
to the ``Write`` that introduced it and the ``thinking`` block(s) just before —
then classified against the repo's own failure taxonomy and matched to the
constraint that *should* have caught it.

    defect  ->  introducing Write  ->  quoted reasoning  ->  root cause  ->
                which rule should have caught it (and, if it didn't, why)

Works with or without a transcript: no transcript degrades gracefully to a
static conformance + fidelity report. Emits both a JSON object (for aggregation
across the run matrix) and a human-readable Markdown dossier.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.harness import _engine as E
from evals.harness import trace as T
from evals.harness.compare_workflow import compare_workflows
from evals.harness.conformance import conformance_report

# Which constraint is designed to catch each root cause — for the "why didn't it
# fire?" column. Ties every defect back to a specific line of defense.
_GUARD = {
    "orphan-behavior": "validator WFV-2 (orphan behaviour)",
    "mis-homed-resource": "authoring protocol (home fields under Resources) — not statically enforced",
    "for_each-on-creation": "validator WFV-7 (creation scheduled with for_each)",
    "double-iteration": "role-aware scaffold (per-agent Step uses env.agent) — AST check",
    "env.agent-on-collective": "role-aware scaffold (Creation is collective) — AST check",
    "node-not-in-execution_order": "validator WFV-9 (execution_order omission)",
    "copied-skip-marked-workflow": "protocol: never copy metadata.validation.skip workflows",
    "raw_context-over-typed-env": "CLAUDE.md typed-env rule — warning only",
    "inlined-dict-param": "validator WFV-4 (inlined dict/list parameter)",
    "agent-never-created": "validator WFV-8 (no creation scheduled)",
    "mega-node": "one-file-one-node convention — not statically enforced",
}

# Map a compare_workflow difference string to a taxonomy token (best-effort).
_DIFF_TAXONOMY = [
    ("creation canvas", "agent-never-created"),
    ("no create", "agent-never-created"),
    ("leftover per-agent init", "for_each-on-creation"),
    ("for_each", "for_each-on-creation"),
    ("scheduler:", "node-not-in-execution_order"),
    ("init_sequence", "node-not-in-execution_order"),
]

# Map a validate_workflow.py error/warning string to a taxonomy token.
_VALIDATOR_TAXONOMY = [
    ("orphan behaviour", "orphan-behavior"),
    ("environment.behavior_subworkflows", "orphan-behavior"),
    ("for_each", "for_each-on-creation"),
    ("no longer supported", "for_each-on-creation"),   # leftover per-agent init (WFV-6)
    ("inlined", "inlined-dict-param"),
    ("execution_order", "node-not-in-execution_order"),
    ("no create_subworkflow", "agent-never-created"),
    ("no agents will be created", "agent-never-created"),
]


def _classify(text: str, table) -> Optional[str]:
    low = text.lower()
    for needle, token in table:
        if needle.lower() in low:
            return token
    return None


def _classify_diff(text: str) -> Optional[str]:
    return _classify(text, _DIFF_TAXONOMY)


def _classify_validator(text: str) -> str:
    return _classify(text, _VALIDATOR_TAXONOMY) or "validator-error"


@dataclass
class Defect:
    source: str                 # "conformance" | "fidelity"
    root_cause: str
    severity: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    reasoning: List[dict] = field(default_factory=list)   # attributed thinking
    guard: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, [], "")}


@dataclass
class Dossier:
    case: str
    condition: str
    tier: str
    conformant: bool
    structurally_isomorphic: bool
    fidelity: float
    contaminated: bool
    defects: List[Defect] = field(default_factory=list)
    process: Dict[str, Any] = field(default_factory=dict)
    fuzzy: List[dict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "case": self.case, "condition": self.condition, "tier": self.tier,
            "conformant": self.conformant,
            "structurally_isomorphic": self.structurally_isomorphic,
            "fidelity": round(self.fidelity, 3),
            "contaminated": self.contaminated,
            "n_defects": len(self.defects),
            "defects": [d.to_dict() for d in self.defects],
            "process": self.process,
            "fuzzy": self.fuzzy,
            "notes": self.notes,
        }


def build_dossier(
    *,
    case: str,
    condition: str,
    tier: str,
    candidate_workflow: str,
    benchmark_workflow: str,
    plugin_dir: Optional[str] = None,
    transcript: Optional[str] = None,
    quarantined_paths: Optional[List[str]] = None,
    identifiers: Optional[List[str]] = None,
) -> Dossier:
    """Compose conformance + fidelity + (optional) reasoning attribution + leak
    detection into one dossier."""
    conf = conformance_report(candidate_workflow, plugin_dir)
    diff = compare_workflows(
        E.load_workflow_json(benchmark_workflow),
        E.load_workflow_json(candidate_workflow),
    )

    events = T.parse_transcript(transcript) if transcript else []
    leaks = T.detect_leaks(events, quarantined_paths or [], identifiers or []) if events else []

    dossier = Dossier(
        case=case, condition=condition, tier=tier,
        conformant=conf.conformant,
        structurally_isomorphic=diff.structurally_isomorphic,
        fidelity=diff.fidelity,
        contaminated=bool(leaks),
        process=T.process_metrics(events) if events else {},
        fuzzy=diff.fuzzy,
    )
    if leaks:
        dossier.notes.append(f"RUN INVALID: {len(leaks)} contamination leak(s) — "
                             "the agent read a quarantined benchmark artifact.")

    # validator errors/warnings -> defects (about the workflow JSON), attributed
    # to the reasoning that wrote that JSON when a transcript is present.
    wf_reasoning = T.attribute(events, candidate_workflow).get("reasoning", []) if events else []
    for msg in conf.validator_errors:
        token = _classify_validator(msg)
        dossier.defects.append(Defect(
            source="conformance", root_cause=token, severity="error", message=msg,
            file=candidate_workflow, reasoning=wf_reasoning, guard=_GUARD.get(token),
        ))
    for msg in conf.validator_warnings:
        token = _classify_validator(msg)
        dossier.defects.append(Defect(
            source="conformance", root_cause=token, severity="warning", message=msg,
            file=candidate_workflow, reasoning=wf_reasoning, guard=_GUARD.get(token),
        ))

    # conformance findings (contract + AST anti-patterns) -> defects, attributed to reasoning
    for f in conf.findings:
        if f.severity not in ("error", "warning"):
            continue
        dossier.defects.append(_defect_from_finding(f, events))

    # fidelity differences -> defects (structural divergence from the benchmark)
    for text in diff.differences:
        token = _classify_diff(text) or "structural-divergence"
        dossier.defects.append(Defect(
            source="fidelity", root_cause=token, severity="error", message=text,
            guard=_GUARD.get(token),
        ))

    # rank: errors first, then by whether reasoning was recoverable
    dossier.defects.sort(key=lambda d: (d.severity != "error", not d.reasoning))
    return dossier


def _defect_from_finding(f, events: List[T.Event]) -> Defect:
    reasoning = []
    if events and f.file:
        reasoning = T.attribute(events, f.file, f.line).get("reasoning", [])
    return Defect(
        source="conformance", root_cause=f.root_cause, severity=f.severity,
        message=f.message, file=f.file, line=f.line,
        reasoning=reasoning, guard=_GUARD.get(f.root_cause),
    )


# --------------------------------------------------------------------------- render
def render_markdown(d: Dossier) -> str:
    L = [f"# Failure dossier — {d.case} / {d.condition} / {d.tier}", ""]
    verdict = "PASS" if (d.conformant and d.structurally_isomorphic and not d.contaminated) else "ISSUES"
    L += [f"**Verdict:** {verdict}", ""]
    L += ["| axis | result |", "|---|---|",
          f"| conformant | {d.conformant} |",
          f"| structurally isomorphic | {d.structurally_isomorphic} |",
          f"| fidelity | {d.fidelity:.2f} |",
          f"| contaminated | {d.contaminated} |", ""]
    if d.notes:
        L += ["> " + n for n in d.notes] + [""]
    if d.process:
        p = d.process
        L += ["## Process (from the trace)", "",
              f"- wrote JSON before PY (protocol order): **{p.get('wrote_json_before_py')}**",
              f"- ran the validator unprompted: **{p.get('ran_validator')}** ({p.get('n_validator_runs', 0)}x)",
              f"- docs read before first write: {list(p.get('read_docs_before_first_write', {}))}",
              f"- writes: {p.get('n_writes')} / tool calls: {p.get('n_tool_uses')}", ""]
    if not d.defects:
        L += ["## Defects", "", "None.", ""]
    else:
        L += [f"## Defects ({len(d.defects)})", ""]
        for i, df in enumerate(d.defects, 1):
            L += [f"### {i}. [{df.severity}] {df.root_cause}", "",
                  f"{df.message}"]
            if df.file:
                loc = f"{df.file}" + (f":{df.line}" if df.line else "")
                L.append(f"- **where:** `{loc}`")
            if df.guard:
                L.append(f"- **should have been caught by:** {df.guard}")
            if df.reasoning:
                L += ["- **reasoning that produced it:**"]
                for r in df.reasoning:
                    for th in r.get("thinking", []):
                        snippet = th if len(th) < 500 else th[:500] + " …"
                        L.append(f"  > {snippet}")
            elif df.source == "conformance":
                L.append("- _reasoning: no transcript, or no Write matched this artifact_")
            L.append("")
    if d.fuzzy:
        L += [f"## Needs an LLM judge ({len(d.fuzzy)})", ""]
        for fz in d.fuzzy:
            L.append(f"- `{fz['slot']}`: {fz['question']}")
        L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Build a failure dossier for one regenerated model.")
    ap.add_argument("--case", required=True)
    ap.add_argument("--condition", default="full")
    ap.add_argument("--tier", default="spec2code")
    ap.add_argument("--candidate", required=True, help="regenerated workflow JSON")
    ap.add_argument("--benchmark", required=True, help="benchmark workflow JSON")
    ap.add_argument("--plugin-dir")
    ap.add_argument("--transcript")
    ap.add_argument("--quarantined", nargs="*", default=[])
    ap.add_argument("--identifiers", nargs="*", default=[])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    d = build_dossier(
        case=args.case, condition=args.condition, tier=args.tier,
        candidate_workflow=args.candidate, benchmark_workflow=args.benchmark,
        plugin_dir=args.plugin_dir, transcript=args.transcript,
        quarantined_paths=args.quarantined, identifiers=args.identifiers,
    )
    if args.json:
        print(json.dumps(d.to_dict(), indent=2))
    else:
        print(render_markdown(d))
    return 1 if (d.contaminated or not d.conformant) else 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
