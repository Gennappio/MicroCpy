"""Regression guard for the MicroC ABM migration (Stage 0 safety net).

A fresh MicroC run must still match the frozen golden reference
(``tools/migration/golden/``). Run in a subprocess with a PYTHONHASHSEED that
differs from the capture, so a pass also re-proves that MicroC is
order-independent (see the de-ordering fix in
``opencellcomms_adapters/MicroC/.../propagate_gene_networks_netlogo.py`` and
``docs/MICROC_ABM_MIGRATION_PLAN.md``).

Slow (~75s, needs FiPy) — excluded from the fast pre-commit gate.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE = Path(__file__).resolve().parents[2]
HARNESS = ENGINE / "tools" / "migration" / "microc_golden.py"
GOLDEN = ENGINE / "tools" / "migration" / "golden"


@pytest.mark.slow
def test_microc_matches_golden(tmp_path):
    pytest.importorskip("fipy")
    assert GOLDEN.exists(), f"golden reference missing at {GOLDEN}"

    out = tmp_path / "run"
    # Different hash seed than capture: a match also proves order-independence.
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "7"}

    subprocess.run(
        [sys.executable, str(HARNESS), "run", "--seed", "123", "--steps", "3",
         "--out", str(out)],
        check=True, env=env,
    )
    result = subprocess.run(
        [sys.executable, str(HARNESS), "compare", str(GOLDEN), str(out)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        "MicroC drifted from the golden reference (or order-dependence "
        "regressed):\n" + result.stdout + result.stderr
    )
