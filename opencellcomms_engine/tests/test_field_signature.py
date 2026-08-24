"""Signature/skip logic of the ON-CHANGE steady solves.

The contract: describe_change() returns None exactly when the previous
converged fields are still the fixed point; any membership, position,
phenotype, watched-gene, or parameter change returns a truthful trigger
string, and flips of unwatched genes change nothing.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from src.workflow.functions.diffusion._field_signature import (  # noqa: E402
    collect_field_signature,
    describe_change,
)

WATCHED = ["mitoATP", "glycoATP"]


def _population(cells):
    """cells: {id: (position, phenotype, gene_states)} -> population duck."""
    wrapped = {
        cid: SimpleNamespace(state=SimpleNamespace(
            position=pos, phenotype=ph, gene_states=genes))
        for cid, (pos, ph, genes) in cells.items()
    }
    return SimpleNamespace(state=SimpleNamespace(cells=wrapped))


BASE = {
    "c1": ((3, 4), "Quiescent", {"mitoATP": True, "glycoATP": False, "ERK": True}),
    "c2": ((5, 6), "Quiescent", {"mitoATP": False, "glycoATP": True, "ERK": False}),
}


def _sig(cells, params=("p",)):
    return collect_field_signature(_population(cells), WATCHED, params)


def test_first_call_always_solves():
    assert describe_change(None, _sig(BASE)) == "first solve of the run"


def test_identical_state_skips():
    assert describe_change(_sig(BASE), _sig(BASE)) is None


def test_unwatched_gene_flip_skips():
    changed = dict(BASE)
    changed["c1"] = ((3, 4), "Quiescent",
                     {"mitoATP": True, "glycoATP": False, "ERK": False})
    assert describe_change(_sig(BASE), _sig(changed)) is None


def test_watched_gene_flip_triggers():
    changed = dict(BASE)
    changed["c1"] = ((3, 4), "Quiescent",
                     {"mitoATP": False, "glycoATP": False, "ERK": True})
    reason = describe_change(_sig(BASE), _sig(changed))
    assert reason == "1 watched-gene flip(s)"


def test_phenotype_change_triggers():
    changed = dict(BASE)
    changed["c2"] = ((5, 6), "Necrosis", BASE["c2"][2])
    assert "1 phenotype change(s)" in describe_change(_sig(BASE), _sig(changed))


def test_membership_and_move_trigger():
    changed = dict(BASE)
    changed["c3"] = ((7, 7), "Quiescent", {"mitoATP": False, "glycoATP": False})
    del changed["c2"]
    changed["c1"] = ((3, 5), *BASE["c1"][1:])
    reason = describe_change(_sig(BASE), _sig(changed))
    assert "+1 cell(s)" in reason and "-1 cell(s)" in reason
    assert "1 cell(s) moved" in reason


def test_params_change_triggers():
    assert describe_change(_sig(BASE, params=("a",)), _sig(BASE, params=("b",))) \
        == "solver/model parameters changed"


def test_missing_watched_gene_reads_false():
    no_genes = {"c1": ((3, 4), "Quiescent", {}),
                "c2": ((5, 6), "Quiescent", None)}
    sig = _sig(no_genes)
    assert all(entry[2] == (False, False) for entry in sig["cells"].values())
