"""Compare two workflow JSON files *semantically*, at the slot level.

Why not a byte diff (or ``oracle(a) == oracle(b)``)? Because a regenerated model
is legitimately *different*: function names and file paths are free variables
(the intake fixes biology, not identifiers), and two valid decompositions of the
same model differ textually. ``compare_workflow`` asks the question that actually
matters for the benchmark: **do these two workflows encode the same ABM?**

It answers by extracting a *structural signature* from each workflow's
``metadata.gui`` + ``subworkflows`` and diffing the signatures **by biological
role, not by identifier**. Subworkflow names are turned into roles with the
engine's own strict homing derivation (``derive_homed_kinds``), so a scheduler
that calls ``ccl21_diffuse`` and one that calls ``diffuse_chemokine`` compare as
equal when both are "the resource behavior of kind ``ccl21``".

The signature captures what the paper's Expected Contract cares about:
  * entity set          — which agent kinds, which resource kinds, a world
  * creation structure  — each agent kind has a collective Creation canvas
  * scheduler shape     — the ordered per-tick calls and their ``for_each`` bind
  * init order          — the ordered setup calls
  * homing              — every behavior's owning tab

Two layers of result, deliberately separated:
  * **exact** (checked in code, no LLM): entity names, creation presence, the
    scheduler role-sequence + ``for_each`` bindings, the init role-sequence,
    ownership. These are crisp and are what ``structurally_isomorphic`` reports.
  * **fuzzy** (flagged for an optional LLM judge): whether the *atomic functions*
    inside a canvas are the same biology (``move -> eat -> metabolize`` vs a
    different-but-equivalent decomposition). Never fails the exact check.

CLI:
    python -m evals.harness.compare_workflow REF.json CAND.json [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.harness import _engine as E


# --------------------------------------------------------------------------- signature
def _canvas_functions(subworkflows: dict, name: Optional[str]) -> List[str]:
    """Ordered ``function_name`` list for a canvas, honoring ``execution_order``.

    The engine runs ``execution_order`` when it is non-empty, else definition
    order — so the executable order is what we compare, not array order."""
    if not name:
        return []
    sw = subworkflows.get(name) or {}
    funcs = sw.get("functions") or []
    by_id = {f.get("id"): f.get("function_name") for f in funcs}
    order = sw.get("execution_order") or []
    if order:
        ordered = [by_id[i] for i in order if i in by_id]
        # execution_order may also list call-node ids we don't resolve here;
        # append any functions it omitted so nothing is silently dropped.
        seen = set(order)
        ordered += [f.get("function_name") for f in funcs if f.get("id") not in seen]
        return [f for f in ordered if f]
    return [f.get("function_name") for f in funcs if f.get("function_name")]


def _call_sequence(subworkflows: dict, canvas_name: Optional[str]) -> List[dict]:
    """Ordered enabled subworkflow-calls of an orchestration canvas, as
    ``{target, for_each}``, honoring ``execution_order`` when present. Used for
    both the scheduler and the init sequence — a ``for_each`` binding on *either*
    is semantically load-bearing (a creation call scheduled per-agent is the
    WFV-7 bug, and it must be visible to structural comparison, not only to the
    validator)."""
    if not canvas_name:
        return []
    sw = subworkflows.get(canvas_name) or {}
    calls = sw.get("subworkflow_calls") or []
    by_id = {c.get("id"): c for c in calls}
    order = sw.get("execution_order") or []
    ordered = [by_id[i] for i in order if i in by_id] if order else calls
    out = []
    for c in ordered:
        if not c.get("enabled", True):
            continue
        fe = c.get("for_each")
        out.append(
            {
                "target": c.get("subworkflow_name"),
                "for_each": None
                if not fe
                else {"type": fe.get("type"), "kind": fe.get("kind"), "order": fe.get("order")},
            }
        )
    return out


def signature(doc: dict) -> dict:
    """Extract the biology-level structural signature of a workflow document.

    Names of *subworkflows* are kept only where they are the free variable being
    tolerated; everywhere structural comparison happens they are resolved to
    roles via ``derive_homed_kinds`` at diff time."""
    gui = (doc.get("metadata") or {}).get("gui") or {}
    subs = doc.get("subworkflows") or {}

    world = gui.get("world") or {}
    agent_kinds = {}
    for ak in gui.get("agent_kinds") or []:
        create = ak.get("create_subworkflow")
        steps = list(ak.get("behavior_subworkflows") or [])
        agent_kinds[ak.get("name")] = {
            "has_create": bool(create),
            "create_functions": _canvas_functions(subs, create),
            "n_steps": len(steps),
            "steps": [
                {"canvas": s, "functions": _canvas_functions(subs, s)} for s in steps
            ],
            "leftover_init": ak.get("init_subworkflow"),  # WFV-6 anti-pattern if set
        }

    resource_kinds = {}
    for rk in gui.get("resource_kinds") or []:
        init = rk.get("init_subworkflow")
        behs = list(rk.get("behavior_subworkflows") or [])
        resource_kinds[rk.get("name")] = {
            "has_init": bool(init),
            "init_functions": _canvas_functions(subs, init),
            "behaviors": [
                {"canvas": b, "functions": _canvas_functions(subs, b)} for b in behs
            ],
        }

    return {
        "agent_kinds": agent_kinds,
        "resource_kinds": resource_kinds,
        "world": {
            "subworkflow": world.get("subworkflow"),
            "functions": _canvas_functions(subs, world.get("subworkflow")),
            "behaviors": [
                {"canvas": b, "functions": _canvas_functions(subs, b)}
                for b in (world.get("behavior_subworkflows") or [])
            ],
        },
        "processing": [
            {"canvas": b, "functions": _canvas_functions(subs, b)}
            for b in ((gui.get("processing") or {}).get("behavior_subworkflows") or [])
        ],
        "scheduler": _call_sequence(subs, (gui.get("scheduler") or {}).get("subworkflow")),
        "init_sequence": _call_sequence(subs, (gui.get("init_sequence") or {}).get("subworkflow")),
        "_homed": E.derive_homed_kinds(gui, subs),
    }


# --------------------------------------------------------------------------- role view
def _role_of(name: Optional[str], homed: dict, gui_lookup: dict) -> str:
    """Resolve a subworkflow name to an identifier-independent role token.

    ``forager_step`` and ``forager_behavior`` both become
    ``agent_behavior:forager`` so the two schedulers compare equal. The kind
    suffix keeps ``tumor_step`` distinct from ``macrophage_step``."""
    if not name:
        return "none"
    role = homed.get(name)
    if role is None:
        return f"orphan:{name}"
    # attach the owning entity kind so per-kind bindings stay distinguishable
    owner = gui_lookup.get(name)
    return f"{role}:{owner}" if owner else role


def _gui_owner_lookup(doc: dict) -> Dict[str, str]:
    """subworkflow name -> owning entity kind name (for agent/resource behaviors)."""
    gui = (doc.get("metadata") or {}).get("gui") or {}
    out: Dict[str, str] = {}
    for ak in gui.get("agent_kinds") or []:
        k = ak.get("name")
        if ak.get("create_subworkflow"):
            out[ak["create_subworkflow"]] = k
        for b in ak.get("behavior_subworkflows") or []:
            out[b] = k
    for rk in gui.get("resource_kinds") or []:
        k = rk.get("name")
        if rk.get("init_subworkflow"):
            out[rk["init_subworkflow"]] = k
        for b in rk.get("behavior_subworkflows") or []:
            out[b] = k
    return out


def _scheduler_role_seq(doc: dict, sig: dict) -> List[dict]:
    homed = sig["_homed"]
    owners = _gui_owner_lookup(doc)
    seq = []
    for call in sig["scheduler"]:
        seq.append(
            {
                "role": _role_of(call["target"], homed, owners),
                "for_each": call["for_each"],
            }
        )
    return seq


def _init_role_seq(doc: dict, sig: dict) -> List[dict]:
    homed = sig["_homed"]
    owners = _gui_owner_lookup(doc)
    return [
        {"role": _role_of(c["target"], homed, owners), "for_each": c["for_each"]}
        for c in sig["init_sequence"]
    ]


# --------------------------------------------------------------------------- diff
@dataclass
class WorkflowDiff:
    same_entities: bool = True
    structurally_isomorphic: bool = True
    fidelity: float = 1.0
    differences: List[str] = field(default_factory=list)
    fuzzy: List[dict] = field(default_factory=list)  # for the optional LLM judge
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "same_entities": self.same_entities,
            "structurally_isomorphic": self.structurally_isomorphic,
            "fidelity": round(self.fidelity, 3),
            "differences": self.differences,
            "fuzzy": self.fuzzy,
            "detail": self.detail,
        }


def compare_workflows(ref_doc: dict, cand_doc: dict) -> WorkflowDiff:
    """Structural, identifier-tolerant comparison of two workflow documents.

    ``ref`` is the benchmark; ``cand`` the regenerated candidate. The report says
    whether they encode the same ABM and, when not, exactly which slot diverged."""
    ref, cand = signature(ref_doc), signature(cand_doc)
    d = WorkflowDiff()

    # --- entity sets (biology; names should match) ---
    for label in ("agent_kinds", "resource_kinds"):
        r, c = set(ref[label]), set(cand[label])
        if r != c:
            d.same_entities = False
            d.structurally_isomorphic = False
            if r - c:
                d.differences.append(f"{label}: missing in candidate: {sorted(r - c)}")
            if c - r:
                d.differences.append(f"{label}: extra in candidate: {sorted(c - r)}")

    # --- per agent-kind creation + step count (matched kinds only) ---
    for k in sorted(set(ref["agent_kinds"]) & set(cand["agent_kinds"])):
        rk, ck = ref["agent_kinds"][k], cand["agent_kinds"][k]
        if rk["has_create"] != ck["has_create"]:
            d.structurally_isomorphic = False
            d.differences.append(
                f"agent '{k}': creation canvas "
                f"{'present' if rk['has_create'] else 'absent'} in benchmark but "
                f"{'present' if ck['has_create'] else 'absent'} in candidate"
            )
        if ck["leftover_init"]:
            d.structurally_isomorphic = False
            d.differences.append(
                f"agent '{k}': candidate declares a leftover per-agent init "
                f"'{ck['leftover_init']}' (WFV-6: that phase was removed)"
            )
        if rk["n_steps"] != ck["n_steps"]:
            d.differences.append(
                f"agent '{k}': {rk['n_steps']} step behavior(s) in benchmark vs "
                f"{ck['n_steps']} in candidate (decomposition may differ; flagged fuzzy)"
            )
            d.fuzzy.append(
                {
                    "slot": f"agent_kinds.{k}.steps",
                    "benchmark": rk["steps"],
                    "candidate": ck["steps"],
                    "question": f"Do the candidate's per-agent Step behaviors for "
                    f"'{k}' cover the same biology as the benchmark's, in the same "
                    f"effective order?",
                }
            )

    # --- per resource-kind init presence ---
    for k in sorted(set(ref["resource_kinds"]) & set(cand["resource_kinds"])):
        rk, ck = ref["resource_kinds"][k], cand["resource_kinds"][k]
        if rk["has_init"] != ck["has_init"]:
            d.structurally_isomorphic = False
            d.differences.append(
                f"resource '{k}': init canvas presence differs "
                f"(benchmark={rk['has_init']} candidate={ck['has_init']})"
            )

    # --- scheduler role-sequence + for_each bindings (order-sensitive, exact) ---
    ref_sched = _scheduler_role_seq(ref_doc, ref)
    cand_sched = _scheduler_role_seq(cand_doc, cand)
    d.detail["scheduler_benchmark"] = ref_sched
    d.detail["scheduler_candidate"] = cand_sched
    if ref_sched != cand_sched:
        # Distinguish "same roles, wrong order/binding" from "different roles".
        ref_roles = [s["role"] for s in ref_sched]
        cand_roles = [s["role"] for s in cand_sched]
        if sorted(ref_roles) == sorted(cand_roles):
            d.structurally_isomorphic = False
            d.differences.append(
                f"scheduler: same behaviors, but order or for_each binding differs.\n"
                f"    benchmark: {ref_roles}\n    candidate: {cand_roles}"
            )
        else:
            d.structurally_isomorphic = False
            d.differences.append(
                f"scheduler: different behavior set/order.\n"
                f"    benchmark: {ref_roles}\n    candidate: {cand_roles}"
            )
        # explicit for_each mismatches on shared roles (the double-iteration bug shows here)
        for rs in ref_sched:
            match = next((cs for cs in cand_sched if cs["role"] == rs["role"]), None)
            if match and match["for_each"] != rs["for_each"]:
                d.differences.append(
                    f"scheduler: '{rs['role']}' for_each differs "
                    f"(benchmark={rs['for_each']} candidate={match['for_each']})"
                )

    # --- init sequence role-sequence + bindings (order-sensitive) ---
    ref_init = _init_role_seq(ref_doc, ref)
    cand_init = _init_role_seq(cand_doc, cand)
    d.detail["init_benchmark"] = ref_init
    d.detail["init_candidate"] = cand_init
    if ref_init != cand_init:
        d.structurally_isomorphic = False
        ref_roles = [c["role"] for c in ref_init]
        cand_roles = [c["role"] for c in cand_init]
        if sorted(ref_roles) == sorted(cand_roles):
            # same steps: either reordered, or a binding changed (for_each on a
            # creation/resource-init call — the WFV-7 shape) — say which.
            binding = [
                r["role"]
                for r, c in zip(ref_init, cand_init)
                if r["role"] == c["role"] and r["for_each"] != c["for_each"]
            ]
            if ref_roles == cand_roles and binding:
                d.differences.append(
                    f"init_sequence: same order, but for_each binding changed on "
                    f"{binding} (a creation/init call scheduled per-agent is the "
                    f"WFV-7 shape)."
                )
            else:
                d.differences.append(
                    f"init_sequence: same steps, different order.\n"
                    f"    benchmark: {ref_roles}\n    candidate: {cand_roles}"
                )
        else:
            d.differences.append(
                f"init_sequence differs.\n"
                f"    benchmark: {ref_roles}\n    candidate: {cand_roles}"
            )

    d.fidelity = _fidelity_score(d, ref, cand)
    return d


def _fidelity_score(d: WorkflowDiff, ref: dict, cand: dict) -> float:
    """A blunt 0..1 summary for aggregate tables. The structured ``differences``
    list is the real output; this is only for cross-run trends."""
    checks = [
        set(ref["agent_kinds"]) == set(cand["agent_kinds"]),
        set(ref["resource_kinds"]) == set(cand["resource_kinds"]),
        d.structurally_isomorphic,
    ]
    for k in set(ref["agent_kinds"]) & set(cand["agent_kinds"]):
        checks.append(ref["agent_kinds"][k]["has_create"] == cand["agent_kinds"][k]["has_create"])
    return sum(1 for c in checks if c) / len(checks) if checks else 0.0


# --------------------------------------------------------------------------- CLI
def compare_files(ref_path: str, cand_path: str) -> WorkflowDiff:
    return compare_workflows(E.load_workflow_json(ref_path), E.load_workflow_json(cand_path))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Semantically compare two workflow JSON files.")
    ap.add_argument("ref", help="benchmark workflow JSON")
    ap.add_argument("cand", help="candidate (regenerated) workflow JSON")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = ap.parse_args(argv)

    diff = compare_files(args.ref, args.cand)
    if args.json:
        print(json.dumps(diff.to_dict(), indent=2))
        return 0 if diff.structurally_isomorphic else 1

    print(f"benchmark: {Path(args.ref).name}")
    print(f"candidate: {Path(args.cand).name}")
    print(f"\nsame entities          : {diff.same_entities}")
    print(f"structurally isomorphic: {diff.structurally_isomorphic}")
    print(f"fidelity score         : {diff.fidelity:.2f}")
    if diff.differences:
        print("\nDifferences:")
        for x in diff.differences:
            print(f"  - {x}")
    if diff.fuzzy:
        print(f"\nFuzzy (needs an LLM judge to rule on biology equivalence): {len(diff.fuzzy)}")
        for f in diff.fuzzy:
            print(f"  - {f['slot']}: {f['question']}")
    if diff.structurally_isomorphic and not diff.differences:
        print("\n=> identical model structure.")
    return 0 if diff.structurally_isomorphic else 1


if __name__ == "__main__":
    sys.exit(main())
