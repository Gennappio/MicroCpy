"""compare_results' pure core (snapshot diff, persistence, observables) is tested
on synthetic snapshots — no simulator needed. The actual run + determinism proof
is a separate slow test (test_smoke_runs.py) since it needs the engine runtime."""
import numpy as np

from evals.harness import compare_results as R


def _snap(cells=None, subs=None, records=None, pheno=None):
    return {
        "substances": subs or {},
        "cells": cells or {},
        "records": records or {},
        "population_stats": {"phenotype_counts": pheno} if pheno else {},
        "substance_stats": {},
        "meta": {"n_cells": len(cells or {}), "n_substances": len(subs or {})},
    }


def test_identical_snapshots_match():
    s = _snap(
        cells={"1,2": {"phenotype": "alive", "metabolic_state": {"sugar": 3.0}}},
        subs={"sugar": np.ones((4, 4))},
        records={"pop": [{"step": 0, "value": 10}, {"step": 1, "value": 9}]},
        pheno={"alive": 1},
    )
    rep = R.compare(s, s)
    assert rep["ok"] is True


def test_field_divergence_caught():
    a = _snap(subs={"sugar": np.ones((4, 4))})
    b = _snap(subs={"sugar": np.ones((4, 4)) * 2})
    assert R.compare(a, b)["ok"] is False
    # within tolerance it matches
    assert R.compare(a, b, field_rtol=0.0, field_atol=5.0)["ok"] is True


def test_cell_state_divergence_caught_by_position():
    a = _snap(cells={"1,1": {"phenotype": "alive", "metabolic_state": {"sugar": 3.0}}})
    b = _snap(cells={"1,1": {"phenotype": "dead", "metabolic_state": {"sugar": 3.0}}})
    rep = R.compare(a, b)
    assert rep["ok"] is False
    assert rep["cells"]["state_diffs"] == 1


def test_sugarscape_style_metabolic_state_diffed():
    """SUGARSCAPE has no phenotype/gene_states; its trait diffs must still count."""
    a = _snap(cells={"2,2": {"metabolic_state": {"sugar": 5.0, "vision": 3}}})
    b = _snap(cells={"2,2": {"metabolic_state": {"sugar": 1.0, "vision": 3}}})
    assert R.compare(a, b)["ok"] is False


def test_missing_cell_caught():
    a = _snap(cells={"1,1": {"phenotype": "x"}, "2,2": {"phenotype": "y"}})
    b = _snap(cells={"1,1": {"phenotype": "x"}})
    rep = R.compare(a, b)
    assert rep["ok"] is False
    assert rep["cells"]["only_in_ref"] == 1


def test_record_final_value_diff():
    a = _snap(records={"tnf": [{"step": 0, "value": 1.0}, {"step": 1, "value": 2.0}]})
    b = _snap(records={"tnf": [{"step": 0, "value": 1.0}, {"step": 1, "value": 9.0}]})
    assert R.compare(a, b)["ok"] is False


def test_save_load_roundtrip(tmp_path):
    s = _snap(
        cells={"1,2": {"phenotype": "alive", "metabolic_state": {"sugar": 3.0}}},
        subs={"sugar": np.arange(16, dtype=float).reshape(4, 4)},
        records={"pop": [{"step": 0, "value": 10.0}]},
        pheno={"alive": 1},
    )
    R.save_snapshot(s, tmp_path)
    loaded = R.load_snapshot(tmp_path)
    assert R.compare(s, loaded)["ok"] is True


def test_scalar_only_drops_private_and_objects():
    cleaned = R._scalar_only({"sugar": 3.0, "_kind": "forager", "_dead": False, "obj": object()})
    assert cleaned == {"sugar": 3.0}


# --- observables ---
def test_observable_population_survives():
    snap = _snap(cells={"1,1": {"phenotype": "x"}})
    res = R.check_observables(snap, [{"text": "cells survive", "check": "population_survives"}])
    assert res[0]["verdict"] == "pass"


def test_observable_population_extinct_fails_when_alive():
    snap = _snap(cells={"1,1": {"phenotype": "x"}})
    res = R.check_observables(snap, [{"text": "all die", "check": "population_extinct"}])
    assert res[0]["verdict"] == "fail"


def test_observable_field_nontrivial():
    snap = _snap(subs={"ccl21": np.array([[0.0, 1.0], [2.0, 3.0]])})
    res = R.check_observables(snap, [{"text": "gradient forms", "check": "field_nontrivial", "target": "ccl21"}])
    assert res[0]["verdict"] == "pass"


def test_observable_steady_state_pass():
    series = [{"step": i, "value": v} for i, v in enumerate([0, 5, 9, 10, 10, 10, 10])]
    snap = _snap(records={"ccl21_mean": series})
    res = R.check_observables(snap, [{"text": "ccl21 steady", "check": "record_steady_state", "target": "ccl21_mean"}])
    assert res[0]["verdict"] == "pass"


def test_observable_unknown_check_defers_to_llm():
    snap = _snap()
    res = R.check_observables(snap, [{"text": "Treg fraction rises then plateaus"}])
    assert res[0]["verdict"] == "needs_llm"
