"""Hypothesis Rules grammar validator.

Validates a Hill-rule dict against the CBHG v3.0 grammar that
PhysiBoSS-master's ``parse_rules_from_pugixml`` accepts. Rejecting at
workflow-save time (with a clear message) is better than failing the
build / sim later — biologists in the GUI get instant feedback.

The set of recognised signals and behaviors mirrors the registrations
performed by upstream ``setup_signal_behavior_dictionaries()`` in
``PhysiBoSS-master/core/PhysiCell_signal_behavior.cpp``. We resolve them
statically (from the spec's substrate and cell-type names) instead of
introspecting a live PhysiCell process.

Anything the validator rejects is, by definition, out of grammar — the
error message tells the user to use Phase 5 (fragment library) instead.
"""
from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

PHASE5_HINT = (
    "This rule is not expressible in the Hypothesis Rules grammar. "
    "Phase 5 (fragment library) is required."
)

# Behaviors that exist regardless of the substrate/cell-type set.
_FIXED_BEHAVIORS = {
    "cycle entry",
    "apoptosis",
    "necrosis",
    "migration speed",
    "migration bias",
    "migration persistence time",
    "cell-cell adhesion",
    "cell-cell adhesion elastic constant",
    "relative maximum adhesion distance",
    "cell-cell repulsion",
    "cell-BM adhesion",
    "cell-BM repulsion",
    "phagocytose apoptotic cell",
    "phagocytose necrotic cell",
    "phagocytose other dead cell",
    "attack damage rate",
    "attack duration",
    "damage rate",
    "damage repair rate",
    "is_movable",
}
# Phase-by-phase exit rates: "exit from cycle phase 0" .. "exit from cycle phase 5"
_FIXED_BEHAVIORS |= {f"exit from cycle phase {i}" for i in range(6)}

# Signals that exist regardless of the substrate/cell-type set.
_FIXED_SIGNALS = {
    "pressure", "volume", "damage", "dead", "time", "total attack time",
    "apoptotic", "necrotic", "current phase", "is_movable",
    "contact with live cell", "contact with dead cell",
    "contact with apoptotic cell", "contact with necrotic cell",
    "contact with basement membrane",
}

# Templates instantiated per substrate / per cell-type.
_SUBSTRATE_BEHAVIOR_TEMPLATES = (
    "{name} secretion",
    "{name} secretion target",
    "{name} uptake",
    "{name} export",
    "chemotactic response to {name}",
)
_SUBSTRATE_SIGNAL_TEMPLATES = (
    "{name}",
    "intracellular {name}",
    "{name} gradient",
    "{name} near",
)
_CELLTYPE_BEHAVIOR_TEMPLATES = (
    "phagocytose {name}",
    "attack {name}",
    "fuse to {name}",
    "transform to {name}",
    "cell adhesion affinity to {name}",
)
_CELLTYPE_SIGNAL_TEMPLATES = (
    "contact with {name}",
)


def _known_behaviors(substrate_names: Iterable[str], cell_type_names: Iterable[str]) -> set:
    out = set(_FIXED_BEHAVIORS)
    # PhysiCell auto-generates a "<substrate> secretion" behavior named after
    # the apoptotic/necrotic debris substrates too — that's how rules_sample's
    # "apoptotic debris secretion" rule works.
    for s in substrate_names:
        for tpl in _SUBSTRATE_BEHAVIOR_TEMPLATES:
            out.add(tpl.format(name=s))
    for ct in cell_type_names:
        for tpl in _CELLTYPE_BEHAVIOR_TEMPLATES:
            out.add(tpl.format(name=ct))
    return out


def _known_signals(substrate_names: Iterable[str], cell_type_names: Iterable[str]) -> set:
    out = set(_FIXED_SIGNALS)
    for s in substrate_names:
        for tpl in _SUBSTRATE_SIGNAL_TEMPLATES:
            out.add(tpl.format(name=s))
    for ct in cell_type_names:
        for tpl in _CELLTYPE_SIGNAL_TEMPLATES:
            out.add(tpl.format(name=ct))
    return out


def _coerce_use_on_dead(v) -> Optional[int]:
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v if v in (0, 1) else None
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("0", "false", "no"): return 0
        if s in ("1", "true", "yes"): return 1
    return None


def validate_rule(
    rule: dict,
    substrate_names: Sequence[str],
    cell_type_names: Sequence[str],
) -> Optional[str]:
    """Return None if valid, otherwise a one-line error message."""
    required = ("cell_type", "signal", "direction", "behavior",
                "max_response", "half_max", "hill_power")
    for k in required:
        if k not in rule:
            return f"Hill rule missing required field '{k}': {rule!r}"

    ct = rule["cell_type"]
    if ct not in cell_type_names:
        return (
            f"Hill rule cell_type {ct!r} is not declared in spec.cell_types "
            f"(known: {sorted(cell_type_names)})."
        )

    direction = rule["direction"]
    if direction not in ("increases", "decreases"):
        return (
            f"Hill rule direction must be 'increases' or 'decreases', got {direction!r}. "
            + PHASE5_HINT
        )

    for f in ("max_response", "half_max", "hill_power"):
        try:
            float(rule[f])
        except (TypeError, ValueError):
            return f"Hill rule field {f!r} must be numeric, got {rule[f]!r}"

    use_on_dead = _coerce_use_on_dead(rule.get("use_on_dead", 0))
    if use_on_dead is None:
        return (
            f"Hill rule use_on_dead must be 0/1 or true/false, got {rule.get('use_on_dead')!r}"
        )

    behaviors = _known_behaviors(substrate_names, cell_type_names)
    if rule["behavior"] not in behaviors:
        return (
            f"Hill rule behavior {rule['behavior']!r} is not expressible in the "
            f"CBHG grammar for this spec. " + PHASE5_HINT
        )

    signals = _known_signals(substrate_names, cell_type_names)
    if rule["signal"] not in signals:
        return (
            f"Hill rule signal {rule['signal']!r} is not expressible in the "
            f"CBHG grammar for this spec. " + PHASE5_HINT
        )

    return None


def validate_rules(
    rules: Sequence[dict],
    substrate_names: Sequence[str],
    cell_type_names: Sequence[str],
) -> List[str]:
    """Return the list of error messages — empty if all rules are valid."""
    errors: List[str] = []
    for i, rule in enumerate(rules):
        err = validate_rule(rule, substrate_names, cell_type_names)
        if err:
            errors.append(f"hill_rules[{i}]: {err}")
    return errors


def normalize_rule(rule: dict) -> dict:
    """Coerce a validated rule into the upstream CSV column shape.

    Field names mirror the upstream parse_csv_rule_v3 in PhysiCell_rules.cpp:
    ``max_response`` = column 4 (NOT the same as a "saturation" of 1).
    """
    return {
        "cell_type": str(rule["cell_type"]),
        "signal": str(rule["signal"]),
        "direction": str(rule["direction"]),
        "behavior": str(rule["behavior"]),
        "max_response": float(rule["max_response"]),
        "half_max": float(rule["half_max"]),
        "hill_power": float(rule["hill_power"]),
        "use_on_dead": _coerce_use_on_dead(rule.get("use_on_dead", 0)) or 0,
    }


__all__ = [
    "PHASE5_HINT",
    "validate_rule",
    "validate_rules",
    "normalize_rule",
]
