"""PhysiCell-kernel codegen-only nodes.

These functions are NOT executed at sim time. They exist so the GUI
palette shows them and so workflow JSONs can carry the
substrate / cell-type / Hill-rule definitions that
``opencellcomms.codegen.physicell.scaffold.generate_project`` reads at
build time.

See ``docs/Physicell_Facade_plan.md`` and the Phase 3 section of
``docs/Physicell_Facade_progress.md``.
"""

from .define_substrate import define_substrate
from .define_cell_type import define_cell_type
from .define_hill_rule import define_hill_rule
from .define_custom_code import define_custom_code
from .set_physicell_config import set_physicell_config
from .run_physicell_simulation import run_physicell_simulation
from .select_project_template import select_project_template
from .summarize_physicell_events import summarize_physicell_events

__all__ = [
    "define_substrate",
    "define_cell_type",
    "define_hill_rule",
    "define_custom_code",
    "set_physicell_config",
    "run_physicell_simulation",
    "select_project_template",
    "summarize_physicell_events",
]
