#!/usr/bin/env python3
"""
Validate ABM workflow JSON for the GUI-readability rules the schema validator
does not cover. These are the rules from CLAUDE.md that decide whether a
scientist can actually find and edit a behaviour in the GUI:

  1. Orphan behaviours (ERROR)
     A subworkflow run by __scheduler__ / __init_sequence__ / main but homed
     under no navigable GUI tab (agent_kinds / resource_kinds / world /
     processing). It is callable but editable nowhere - the failure mode
     described in CLAUDE.md, "Every behavior must belong to a navigable
     category". The homing derivation is the *strict* one (mirrors the engine's
     WorkflowDefinition._derive_subworkflow_kinds and the GUI's
     computeSubworkflowKinds) - deliberately WITHOUT the GUI's transitive
     "reachable from main => generic subworkflow" fallback, which would mask
     exactly these orphans.

  2. environment.behavior_subworkflows non-empty (ERROR)
     There is no Environment tab; a behaviour parked there is orphaned.

  3. Inlined dict/list parameters (ERROR when the registry types the parameter
     DICT/LIST; WARN when the function is not registered so the type is unknown)
     A complex value inlined in a node's `parameters` renders as an unreadable
     flat string in the GUI; use a dictParameterNode / listParameterNode wired
     via `parameter_nodes` instead.

  4. custom_functions_module set at all (ERROR)
     The legacy custom-functions hook file mechanism was removed from workflow
     authoring: model-specific behavior belongs in registered plugin functions
     (visible and editable in the GUI), never in a hidden module loaded by
     path. Workflows must not set `custom_functions_module` on any node.
     Archived pre-migration workflows that still carry it are skip-flagged
     (`metadata.validation.skip`), not fixed.

Usage:
    python scripts/validate_workflow.py <workflow.json> [<workflow.json> ...]
    python scripts/validate_workflow.py --all   # scan opencellcomms_adapters/*/workflows/*.json

Exit codes:
    0: no errors (warnings are allowed)
    1: one or more errors, or a file could not be read
"""

import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

# Mirror validate_functions.py: engine dir on path (for `src`), repo root on
# path (for `opencellcomms_adapters`).
ENGINE_DIR = Path(__file__).parent.parent
REPO_ROOT = ENGINE_DIR.parent
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(REPO_ROOT))


def load_registry():
    """Load the function registry quietly. Returns None if it can't be built
    (the inline-parameter check then degrades from ERROR to WARN)."""
    try:
        captured = io.StringIO()
        with redirect_stdout(captured):
            from src.workflow.registry import get_default_registry

            return get_default_registry()
    except Exception:
        return None


def _param_type(param) -> str:
    """Uppercased type string for a registered parameter (handles enum or str)."""
    t = getattr(param, "type", None)
    v = getattr(t, "value", t)
    return str(v).upper()


def registered_param_types(registry, function_name):
    """{param_name: 'DICT'|'FLOAT'|...} for a registered function, or None if
    the function is not in the registry (e.g. a skeleton not yet written)."""
    if registry is None:
        return None
    meta = getattr(registry, "functions", {}).get(function_name)
    if meta is None:
        return None
    return {p.name: _param_type(p) for p in getattr(meta, "parameters", [])}


def derive_homed_kinds(gui, subworkflows):
    """Strict name -> kind homing map from metadata.gui. Only explicit ownership
    counts (no transitive fallback), so an un-homed behaviour is absent here."""
    kinds = {}

    def claim(name, kind):
        if name:
            kinds[name] = kind

    claim((gui.get("scheduler") or {}).get("subworkflow"), "scheduler")
    claim((gui.get("init_sequence") or {}).get("subworkflow"), "init_sequence")

    world = gui.get("world") or {}
    claim(world.get("subworkflow"), "world")
    for n in world.get("behavior_subworkflows") or []:
        claim(n, "world_behavior")

    for ak in gui.get("agent_kinds") or []:
        claim(ak.get("create_subworkflow"), "agent_create")  # collective creation, runs once
        for n in ak.get("behavior_subworkflows") or []:
            claim(n, "agent_behavior")

    for rk in gui.get("resource_kinds") or []:
        claim(rk.get("init_subworkflow"), "resource_init")
        for n in rk.get("behavior_subworkflows") or []:
            claim(n, "resource_behavior")

    for n in (gui.get("processing") or {}).get("behavior_subworkflows") or []:
        claim(n, "processing_behavior")

    # Legacy world-setup scaffolds that the strict engine derivation doesn't
    # cover but which are legitimate (not orphans): the old `space` block and
    # `environment.init_subworkflow`. NOTE: environment.behavior_subworkflows is
    # deliberately NOT claimed - that is the forbidden case checked separately.
    claim((gui.get("space") or {}).get("subworkflow"), "space")
    claim((gui.get("environment") or {}).get("init_subworkflow"), "environment_init")

    if "main" in subworkflows:
        claim("main", "composer")

    return kinds


def called_targets(subworkflows, orchestrator_name):
    """subworkflow_name values called directly by an orchestrator canvas."""
    sw = subworkflows.get(orchestrator_name) if orchestrator_name else None
    if not sw:
        return []
    return [
        c.get("subworkflow_name")
        for c in (sw.get("subworkflow_calls") or [])
        if c.get("subworkflow_name")
    ]


def check_orphans(gui, subworkflows, errors):
    """Flag behaviours that run but are homed to no tab. Only applies to ABM
    models (those with a scheduler) - a bare composer workflow has no in-loop
    behaviours to orphan."""
    scheduler_name = (gui.get("scheduler") or {}).get("subworkflow")
    if not scheduler_name:
        return  # not an ABM model; nothing to home

    homed = derive_homed_kinds(gui, subworkflows)
    init_name = (gui.get("init_sequence") or {}).get("subworkflow")

    run_names = set()
    for orchestrator in ("main", init_name, scheduler_name):
        run_names.update(called_targets(subworkflows, orchestrator))

    for name in sorted(run_names):
        if name not in homed:
            errors.append(
                f"orphan behaviour '{name}': it runs (called by the scheduler / "
                f"init sequence / main) but is homed under no GUI tab. Add it to "
                f"agent_kinds[k].behavior_subworkflows, "
                f"resource_kinds[k].behavior_subworkflows, "
                f"world.behavior_subworkflows, or processing.behavior_subworkflows "
                f"in metadata.gui."
            )

    env_behaviors = (gui.get("environment") or {}).get("behavior_subworkflows") or []
    if env_behaviors:
        errors.append(
            f"environment.behavior_subworkflows must be empty (there is no "
            f"Environment tab - anything here is orphaned): {env_behaviors}. "
            f"Re-home these under an agent/resource/world/processing category."
        )


def check_inlined_params(subworkflows, registry, errors, warnings):
    """Flag non-empty dict/list values inlined in a node's `parameters`."""
    for sw_name, sw in subworkflows.items():
        for fn in sw.get("functions") or []:
            fname = fn.get("function_name")
            node_id = fn.get("id", "?")
            params = fn.get("parameters") or {}
            types = registered_param_types(registry, fname)
            for pname, pval in params.items():
                if not isinstance(pval, (dict, list)) or len(pval) == 0:
                    continue
                kind = "dict" if isinstance(pval, dict) else "list"
                where = f"node '{node_id}' ({fname}) in subworkflow '{sw_name}'"
                if types is not None and types.get(pname) in ("DICT", "LIST"):
                    errors.append(
                        f"inlined {kind} for parameter '{pname}' on {where}: this "
                        f"parameter is {types[pname]}-typed; use a "
                        f"{kind}ParameterNode in the subworkflow's `parameters` "
                        f"array (linked via `parameter_nodes`) instead of inlining "
                        f"it - inlined complex values render as unreadable flat "
                        f"strings in the GUI."
                    )
                elif types is None:
                    warnings.append(
                        f"inlined {kind} for parameter '{pname}' on {where}: "
                        f"'{fname}' is not registered, so its type can't be "
                        f"confirmed. If '{pname}' is DICT/LIST-typed, use a "
                        f"{kind}ParameterNode instead of inlining it."
                    )


def check_no_agent_init(gui, errors):
    """Per-agent agent init was removed from the model: an agent kind has a collective
    Creation canvas (create_subworkflow, runs once) and per-agent Steps, nothing in
    between. A leftover init_subworkflow is a hard error -- do the per-cell setup
    collectively in the creation canvas (for cell in env.cells)."""
    for ak in gui.get("agent_kinds") or []:
        init_sw = ak.get("init_subworkflow")
        if init_sw:
            errors.append(
                f"agent kind '{ak.get('name')}' declares a per-agent init '{init_sw}', "
                f"which is no longer supported. Fold its per-cell setup into the "
                f"create_subworkflow (collective, runs once over env.cells)."
            )


def check_agent_creation_structure(gui, subworkflows, errors, warnings):
    """Structural checks on how agent kinds are brought into existence.

    Creation is collective: it runs ONCE (no for_each). A model that declares agent
    kinds but schedules no creation makes no agents. Gated on scheduler-present (like
    check_orphans) so composer / legacy files with no ABM loop are untouched.

    - INV2 (ERROR): a create_subworkflow scheduled WITH for_each -- creation is
      collective; for_each would re-create the whole population once per agent.
    - INV1 (WARN, model-level): agent kinds exist but no create_subworkflow is
      scheduled anywhere -- no agents will be created. Model-level (not per-kind)
      because a kind can legitimately be created inside another kind's collective
      creation canvas (e.g. one CSV loader placing several kinds), which a static
      check cannot see."""
    scheduler_name = (gui.get("scheduler") or {}).get("subworkflow")
    if not scheduler_name:
        return  # not an ABM model; nothing to create

    agent_kinds = gui.get("agent_kinds") or []
    if not agent_kinds:
        return

    init_seq = (gui.get("init_sequence") or {}).get("subworkflow")

    # name -> first scheduled call (across main + init sequence).
    scheduled = {}
    for orch in ("main", init_seq):
        sw = subworkflows.get(orch) if orch else None
        if not sw:
            continue
        for c in sw.get("subworkflow_calls") or []:
            name = c.get("subworkflow_name")
            if name:
                scheduled.setdefault(name, c)

    any_creation_scheduled = False
    for ak in agent_kinds:
        create = ak.get("create_subworkflow")
        if create and create in scheduled:
            any_creation_scheduled = True
            if scheduled[create].get("for_each"):
                errors.append(
                    f"agent kind '{ak.get('name')}' creation canvas '{create}' is "
                    f"scheduled with for_each: creation is collective and runs once. "
                    f"Remove the for_each from its init-sequence call."
                )

    if not any_creation_scheduled:
        warnings.append(
            "agent kinds are defined but no create_subworkflow is scheduled in the "
            "init sequence: no agents will be created. Add a Creation canvas (under the "
            "agent kind) and schedule it in Initialization -- unless these kinds are "
            "created collectively inside another kind's creation canvas."
        )


def check_no_custom_functions_module(subworkflows, errors):
    """The legacy custom-functions hook-file mechanism was removed from
    workflow authoring: a hidden Python module loaded by path is invisible in
    the GUI and couples the model to files outside its canvases. Any node
    setting `custom_functions_module` is an error - port the behavior into
    registered plugin functions (e.g. an explicit AutoPlotter cell_color_fn,
    a plugin division/metabolism function) instead."""
    for sw_name, sw in subworkflows.items():
        for fn in sw.get("functions") or []:
            value = (fn.get("parameters") or {}).get("custom_functions_module")
            if isinstance(value, str) and value:
                errors.append(
                    f"node '{fn.get('id', '?')}' ({fn.get('function_name')}) in "
                    f"subworkflow '{sw_name}' sets custom_functions_module "
                    f"('{value}'). The hook-file mechanism was removed: move the "
                    f"behavior into registered plugin functions "
                    f"(opencellcomms_adapters/<plugin>/functions/...) and delete "
                    f"this parameter."
                )


def check_execution_order_complete(subworkflows, warnings):
    """Warn when a sub-workflow's execution_order is non-empty but omits an enabled
    node that exists in it. The executor runs ONLY execution_order when it is present
    (a fully empty order falls back to definition/array order), so an omitted call or
    function is **silently never run**. Schema validation already rejects unknown ids
    (schema.py); this covers the reverse -- missing ids -- which is exactly the symptom
    of a GUI export that failed to wire an edge for a call node."""
    for name, sw in subworkflows.items():
        order = sw.get("execution_order") or []
        if not order:
            continue  # empty order uses the engine's definition-order fallback
        ordered = set(order)
        missing = []
        for node in (sw.get("functions") or []) + (sw.get("subworkflow_calls") or []):
            nid = node.get("id")
            if nid and node.get("enabled", True) and nid not in ordered:
                missing.append(nid)
        if missing:
            warnings.append(
                f"sub-workflow '{name}': execution_order omits node(s) {sorted(missing)} "
                f"that exist in it -- they will NOT run (the engine executes only "
                f"execution_order when it is non-empty). Wire them into the execution "
                f"chain, or clear execution_order to fall back to definition order."
            )


def check_workflow(path, registry):
    """Returns (errors, warnings, skip_reason) for one workflow file.

    A file carrying `metadata.validation.skip: true` is a deliberately archived
    fixture (a pre-migration checkpoint or a generated stress test whose canonical
    successor is validated separately). It is reported as SKIPPED and excluded from
    the tallies, so `--all` stays green-or-explained instead of accumulating stale
    warnings that train people to ignore the validator."""
    errors, warnings = [], []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read/parse {path}: {exc}"], [], None

    validation = (data.get("metadata") or {}).get("validation") or {}
    if validation.get("skip"):
        return [], [], validation.get("reason") or "archived fixture"

    gui = (data.get("metadata") or {}).get("gui") or {}
    subworkflows = data.get("subworkflows") or {}

    check_orphans(gui, subworkflows, errors)
    check_inlined_params(subworkflows, registry, errors, warnings)
    check_no_agent_init(gui, errors)
    check_agent_creation_structure(gui, subworkflows, errors, warnings)
    check_no_custom_functions_module(subworkflows, errors)
    check_execution_order_complete(subworkflows, warnings)
    return errors, warnings, None


def resolve_paths(argv):
    if argv == ["--all"]:
        return sorted(
            str(p)
            for p in (REPO_ROOT / "opencellcomms_adapters").glob("*/workflows/*.json")
        )
    return argv


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1

    paths = resolve_paths(argv)
    if not paths:
        print("No workflow files to check.")
        return 0

    registry = load_registry()

    total_errors = 0
    total_warnings = 0
    for path in paths:
        errors, warnings, skip_reason = check_workflow(path, registry)
        if skip_reason:
            print(f"{path}: SKIPPED ({skip_reason})")
            continue
        total_errors += len(errors)
        total_warnings += len(warnings)
        if errors or warnings:
            print(f"\n{path}")
            for e in errors:
                print(f"  ERROR: {e}")
            for w in warnings:
                print(f"  WARN:  {w}")
        else:
            print(f"{path}: OK")

    print()
    if total_errors:
        print(f"FAILED - {total_errors} error(s), {total_warnings} warning(s).")
        return 1
    print(f"Passed - 0 errors, {total_warnings} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
