"""Conformance axis: does an artifact satisfy the repo's *own* rules?

This is the benchmark-free, objective, cheapest axis and the most defensible
number in the paper: every rule here exists in the repo *because a coding agent
got it wrong*, so measuring rule-conformance directly tests the thesis.

Three layers, in increasing specificity:

  1. **Validator** — run the shipped ``validate_workflow.check_workflow`` (the same
     oracle every /occ_* skill is told to satisfy): orphan behaviors, forbidden
     ``environment.behavior_subworkflows``, inlined dict/list params, leftover
     per-agent init, ``for_each`` on creation, execution_order omissions.

  2. **Expected Contract** — the 10-point contract from
     ``docs/AGENT_ASSISTED_ABM_AUTHORING.md:374-387``, checked structurally where
     a static check can see it (creation collective, per-agent uses ``for_each``,
     resources homed, scheduler/init wired, zero hard errors).

  3. **Code anti-patterns (AST)** — the named failures the *workflow* validator
     cannot see because they live in Python bodies, cross-referenced against the
     canvas each function sits on:
       * ``double-iteration``       — ``for x in env.cells`` inside a per-agent Step
                                      (the ARTICLE/7.3 failure)
       * ``env.agent-on-collective``— ``env.agent`` used on a collective Creation
       * ``raw_context-over-typed`` — reaching past ``env`` for something with a
                                      typed accessor (CLAUDE.md "the tell")

Every finding carries a ``root_cause`` token from the repo's own failure taxonomy
so the trace analyzer can line defects up with the reasoning that produced them.
"""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from evals.harness import _engine as E

# Typed-env accessors that make a raw_context reach a smell (CLAUDE.md "the tell").
_TYPED_ACCESSORS = {
    "config": "env.config",
    "cells": "env.cells",
    "agents": "env.agents",
    "population": "env.population",
    "world": "env.world",
    "domain": "env.domain",
    "simulator": "env.resource(...)/env.concentration(...)",
    "gene_networks": "get_gene_network(...)",
}


@dataclass
class Finding:
    rule: str              # e.g. "WFV-2", "contract-2", "double-iteration"
    severity: str          # "error" | "warning"
    root_cause: str        # taxonomy token, for trace attribution
    message: str
    file: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class ConformanceReport:
    workflow: str
    validator_errors: List[str] = field(default_factory=list)
    validator_warnings: List[str] = field(default_factory=list)
    skip_reason: Optional[str] = None
    findings: List[Finding] = field(default_factory=list)

    @property
    def conformant(self) -> bool:
        """Zero hard errors from any layer (Expected Contract point 8)."""
        if self.validator_errors:
            return False
        return not any(f.severity == "error" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "workflow": self.workflow,
            "conformant": self.conformant,
            "validator_errors": self.validator_errors,
            "validator_warnings": self.validator_warnings,
            "skip_reason": self.skip_reason,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------- code (AST) scan
class _BodyVisitor(ast.NodeVisitor):
    """Collect the tells from one function body.

    The ``env.agent`` signal is guard-aware: ``env.agent`` *with* a ``None`` guard
    (``agent = env.agent; if agent is None: return``, or the inline
    ``[env.cell] if env.cell is not None else env.cells``) is the CORRECT
    per-agent shape and is safe on any canvas. Only an **unguarded** dereference
    is the ``env.agent-on-collective`` bug. Detecting the guard is what stops the
    canonical benchmark (which guards correctly) from being flagged."""

    def __init__(self) -> None:
        self.collective_iter: List[int] = []   # line nos of `for x in env.cells`-style loops
        self.uses_env_agent: List[int] = []     # line nos of env.agent / env.cell reads
        self.populate: List[int] = []           # line nos of env.population.populate(...)
        self.raw_context_keys: Dict[str, int] = {}  # key -> line no
        self.agent_aliases: set = set()         # locals bound from env.agent / env.cell
        self.none_compared: set = set()         # names compared against None
        self.agent_none_guarded = False         # env.agent/env.cell compared to None directly

    @property
    def agent_guarded(self) -> bool:
        return self.agent_none_guarded or bool(self.agent_aliases & self.none_compared)

    def visit_For(self, node: ast.For) -> None:
        if _iter_is_collection(node.iter):
            self.collective_iter.append(node.lineno)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # agent = env.agent  ->  remember `agent` as an alias to guard-check later
        if _is_env_agent(node.value):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    self.agent_aliases.add(t.id)
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        # `<x> is/is not/==/!= None` where <x> is env.agent/env.cell or an alias
        operands = [node.left, *node.comparators]
        has_none = any(isinstance(o, ast.Constant) and o.value is None for o in operands)
        if has_none:
            for o in operands:
                if _is_env_agent(o):
                    self.agent_none_guarded = True
                elif isinstance(o, ast.Name):
                    self.none_compared.add(o.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # env.agent / env.cell  (a bound single agent)
        if node.attr in ("agent", "cell") and _is_env(node.value):
            self.uses_env_agent.append(node.lineno)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # env.raw_context["config"]  /  ctx["config"] after ctx = env.raw_context
        key = _const_str(node.slice)
        if key is not None and _is_raw_context(node.value):
            self.raw_context_keys.setdefault(key, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "populate":
            self.populate.append(node.lineno)
        self.generic_visit(node)


def _is_env(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "env"


def _is_env_agent(node: ast.AST) -> bool:
    """env.agent / env.cell attribute access."""
    return isinstance(node, ast.Attribute) and node.attr in ("agent", "cell") and _is_env(node.value)


def _is_raw_context(node: ast.AST) -> bool:
    # env.raw_context[...]  OR a bare name that was assigned env.raw_context
    if isinstance(node, ast.Attribute) and node.attr == "raw_context" and _is_env(node.value):
        return True
    return isinstance(node, ast.Name) and node.id in ("ctx", "raw_context", "context")


def _iter_is_collection(node: ast.AST) -> Optional[str]:
    """True-ish when a for-loop iterates the whole population collectively."""
    # env.cells / env.agents / env.population...
    if isinstance(node, ast.Attribute) and node.attr in ("cells", "agents"):
        if _is_env(node.value) or _attr_root_is_env(node.value):
            return node.attr
    # context['population'].cells  /  env.population.cells
    if isinstance(node, ast.Attribute) and node.attr == "cells":
        return "cells"
    return None


def _attr_root_is_env(node: ast.AST) -> bool:
    while isinstance(node, ast.Attribute):
        node = node.value
    return _is_env(node)


def _const_str(node: ast.AST) -> Optional[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    # py3.8 Index wrapper
    if isinstance(node, ast.Index):  # pragma: no cover
        return _const_str(node.value)
    return None


def scan_plugin_functions(plugin_dir: Path) -> Dict[str, dict]:
    """{function_name: {file, lineno, visitor}} for every @register_function in a
    plugin's ``functions/`` tree. The registered name is the decorator's ``name=``
    kwarg when present, else the def name."""
    out: Dict[str, dict] = {}
    fdir = Path(plugin_dir) / "functions"
    if not fdir.exists():
        return out
    for py in sorted(fdir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            reg = _registered_name(fn)
            if reg is None:
                continue
            v = _BodyVisitor()
            v.visit(fn)
            out[reg] = {"file": str(py), "lineno": fn.lineno, "visitor": v}
    return out


def _registered_name(fn: ast.AST) -> Optional[str]:
    """The name a function is registered under, or None if not @register_function."""
    for dec in getattr(fn, "decorator_list", []):
        call = dec if isinstance(dec, ast.Call) else None
        target = call.func if call else dec
        name = target.attr if isinstance(target, ast.Attribute) else getattr(target, "id", None)
        if name != "register_function":
            continue
        if call:
            for kw in call.keywords:
                if kw.arg == "name":
                    s = _const_str(kw.value) or (kw.value.value if isinstance(kw.value, ast.Constant) else None)
                    if s:
                        return s
        return fn.name
    return None


def code_findings(workflow_doc: dict, plugin_dir: Path) -> List[Finding]:
    """AST anti-patterns cross-referenced against the canvas each function sits on."""
    gui = (workflow_doc.get("metadata") or {}).get("gui") or {}
    subs = workflow_doc.get("subworkflows") or {}
    scanned = scan_plugin_functions(plugin_dir)

    # function_name -> canvas role, via the homing map + which canvas lists it
    creation_funcs = _funcs_in_canvases(gui, subs, _creation_canvas_names(gui))
    step_funcs = _funcs_in_canvases(gui, subs, _step_canvas_names(gui))

    findings: List[Finding] = []
    for fname, info in scanned.items():
        v: _BodyVisitor = info["visitor"]
        # double-iteration: collective loop inside a per-agent Step
        if fname in step_funcs and (v.collective_iter or v.populate):
            findings.append(Finding(
                rule="double-iteration", severity="error", root_cause="double-iteration",
                message=(f"'{fname}' runs once per agent (it is on a per-agent Step canvas) "
                         f"but its body iterates the whole population — the O(N^2) "
                         f"double-iteration bug (ARTICLE/7.3). Use env.agent."),
                file=info["file"], line=(v.collective_iter or v.populate)[0]))
        # env.agent on a collective Creation canvas, WITHOUT a None-guard.
        # A guarded env.agent (`if env.agent is None: ...`) is the correct shape and
        # is safe on any canvas — only an unguarded dereference is the bug.
        if fname in creation_funcs and v.uses_env_agent and not v.agent_guarded:
            findings.append(Finding(
                rule="env.agent-on-collective", severity="error", root_cause="env.agent-on-collective",
                message=(f"'{fname}' is on a collective Creation canvas where env.agent is None, "
                         f"but its body dereferences env.agent/env.cell without a None-guard. "
                         f"Do per-cell setup with `for cell in env.cells:`."),
                file=info["file"], line=v.uses_env_agent[0]))
        # raw_context reach where a typed accessor exists
        for key, line in v.raw_context_keys.items():
            if key in _TYPED_ACCESSORS:
                findings.append(Finding(
                    rule="raw_context-over-typed", severity="warning",
                    root_cause="raw_context-over-typed-env",
                    message=(f"'{fname}' reaches env.raw_context['{key}'] but a typed accessor "
                             f"exists ({_TYPED_ACCESSORS[key]}). CLAUDE.md 'the tell'."),
                    file=info["file"], line=line))
    return findings


def _creation_canvas_names(gui: dict) -> List[str]:
    return [ak.get("create_subworkflow") for ak in (gui.get("agent_kinds") or []) if ak.get("create_subworkflow")]


def _step_canvas_names(gui: dict) -> List[str]:
    names = []
    for ak in gui.get("agent_kinds") or []:
        names += list(ak.get("behavior_subworkflows") or [])
    return names


def _funcs_in_canvases(gui: dict, subs: dict, canvas_names: List[str]) -> set:
    out = set()
    for name in canvas_names:
        sw = subs.get(name) or {}
        for f in sw.get("functions") or []:
            if f.get("function_name"):
                out.add(f["function_name"])
    return out


# ---------------------------------------------------------------- contract checks
def contract_findings(workflow_doc: dict) -> List[Finding]:
    """Structural subset of the 10-point Expected Contract that a static check can see."""
    gui = (workflow_doc.get("metadata") or {}).get("gui") or {}
    subs = workflow_doc.get("subworkflows") or {}
    findings: List[Finding] = []

    agent_kinds = gui.get("agent_kinds") or []
    if agent_kinds:
        # Point 1/2: every agent kind that needs agents has a collective creation path.
        for ak in agent_kinds:
            if not ak.get("create_subworkflow"):
                findings.append(Finding(
                    rule="contract-1", severity="warning", root_cause="agent-never-created",
                    message=f"agent kind '{ak.get('name')}' has no create_subworkflow (may be "
                            f"created inside another kind's canvas — verify)."))
    return findings


# ---------------------------------------------------------------- top level
def conformance_report(workflow_path: str, plugin_dir: Optional[str] = None) -> ConformanceReport:
    """Full conformance of one workflow (+ its plugin code, if given)."""
    registry = E.load_registry()
    errs, warns, skip = E.check_workflow(workflow_path, registry)
    rep = ConformanceReport(
        workflow=str(workflow_path),
        validator_errors=list(errs),
        validator_warnings=list(warns),
        skip_reason=skip,
    )
    if skip:
        return rep
    doc = E.load_workflow_json(workflow_path)
    rep.findings += contract_findings(doc)
    if plugin_dir:
        rep.findings += code_findings(doc, Path(plugin_dir))
    return rep


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Conformance of a workflow against the repo's own rules.")
    ap.add_argument("workflow")
    ap.add_argument("--plugin-dir", help="plugin root, to enable AST anti-pattern checks")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rep = conformance_report(args.workflow, args.plugin_dir)
    if args.json:
        print(json.dumps(rep.to_dict(), indent=2))
        return 0 if rep.conformant else 1

    print(f"workflow : {Path(args.workflow).name}")
    if rep.skip_reason:
        print(f"SKIPPED: {rep.skip_reason}")
        return 0
    print(f"conformant: {rep.conformant}")
    for e in rep.validator_errors:
        print(f"  [validator ERROR] {e}")
    for w in rep.validator_warnings:
        print(f"  [validator WARN ] {w}")
    for f in rep.findings:
        loc = f" ({Path(f.file).name}:{f.line})" if f.file else ""
        print(f"  [{f.severity.upper()} {f.rule}]{loc} {f.message}")
    return 0 if rep.conformant else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
