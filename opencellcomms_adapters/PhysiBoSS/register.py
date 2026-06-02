"""
PhysiBoSS / PhysiCell adapter — registers the codegen-only node functions.

This adapter drives PhysiCell/PhysiBoSS as a black box: workflows declaring
``kernel: physicell`` carry substrate / cell-type / Hill-rule definitions as
codegen-only nodes (``define_substrate`` / ``define_cell_type`` /
``define_hill_rule`` / ``run_physicell_simulation`` / ``select_project_template``
/ ``summarize_physicell_events``). At run time the engine's executor hands the
workflow to ``opencellcomms_adapters.PhysiBoSS.backend.physicell_backend.run``,
which generates a PhysiCell project tree (via ``.codegen``), compiles it against
an unmodified ``PhysiBoSS-master/`` tree, and streams observability events back.

Importing this module registers all node functions via ``@register_function``.
"""

# Importing the package triggers registration of all six node functions
# (see functions/__init__.py).
import opencellcomms_adapters.PhysiBoSS.functions  # noqa: F401
