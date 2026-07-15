"""End-to-end runtime checks (slow): a benchmark actually runs and reproduces.

These exercise the generalized runner + snapshot + compare on a live model, and
double as a proof that the determinism discipline (seed the globals, fresh
process per run, position-keyed cells, varied PYTHONHASHSEED) holds. SUGARSCAPE
is discrete (no FiPy), so it is the cheap smoke model."""
import pytest

from evals.harness import compare_results as R
from evals.tests import conftest as cf


@pytest.mark.slow
def test_sugarscape_is_deterministic():
    """Two fresh runs, same seed, different hash seeds -> identical snapshot."""
    rc = R.main(["determinism", "--workflow", str(cf.CANONICAL["sugarscape"]),
                 "--seed", "123", "--steps", "3"])
    assert rc == 0, "SUGARSCAPE run is non-deterministic or the runner is broken"


@pytest.mark.slow
def test_sugarscape_snapshot_is_nonempty(tmp_path):
    """A run must capture agents and the sugar field — an empty snapshot means the
    snapshot extractor missed this model's representation (the ABM domain bug)."""
    rc = R.main(["run", "--workflow", str(cf.CANONICAL["sugarscape"]),
                 "--seed", "7", "--steps", "3", "--out", str(tmp_path / "snap")])
    assert rc == 0
    snap = R.load_snapshot(tmp_path / "snap")
    assert snap["meta"]["n_cells"] > 0, "no agents captured"
    assert snap["meta"]["n_substances"] > 0, "no resource field captured"
