"""Path bootstrap + shared benchmark locations for the harness tests."""
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ADAPTERS = REPO_ROOT / "opencellcomms_adapters"

CANONICAL = {
    "sugarscape": ADAPTERS / "SUGARSCAPE" / "workflows" / "sugarscape.json",
    "microc": ADAPTERS / "MicroC" / "workflows" / "microc.json",
    "tcell_corral": ADAPTERS / "TCELL_CORRAL" / "workflows" / "tcell_corral.json",
}
PLUGIN_DIRS = {
    "sugarscape": ADAPTERS / "SUGARSCAPE",
    "microc": ADAPTERS / "MicroC",
    "tcell_corral": ADAPTERS / "TCELL_CORRAL",
}


@pytest.fixture(params=sorted(CANONICAL), ids=sorted(CANONICAL))
def canonical_case(request):
    """(name, workflow_path, plugin_dir) for each canonical benchmark."""
    name = request.param
    return name, CANONICAL[name], PLUGIN_DIRS[name]
