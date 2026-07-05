"""TCELL_CORRAL adapter — the Corral T-helper differentiation model.

A Python re-expression of the PhysiCell / PhysiBoSS `FOXP3_2` differentiation
experiment (``config/differentiation/*.xml`` in the PhysiCell tree). One
endothelial cell secretes CCL21; dendritic cells chemotax up that gradient and,
on contact, switch on a naive T0 cell's ~90-node MaBoSS network, which settles
into a Treg / Th1 / Th17 attractor and commits the cell's fate.

The intracellular layer runs the real ``tcell_corral`` MaBoSS network through
the engine's continuous-time stochastic mode (``BooleanNetwork.step_maboss``),
which is validated against the reference engine (cmaboss) in
``opencellcomms_engine/tests/biology/test_maboss_crosscheck.py``. The spatial
layer (CCL21 diffusion, DC chemotaxis, contact-triggered differentiation,
fate-specific motility) is built on the ABM class layer.

See ``README.md`` for the build status and the remaining node functions.
"""

# --- Initialization -------------------------------------------------------
import opencellcomms_adapters.TCELL_CORRAL.functions.initialization.place_cells_from_csv  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.initialization.build_tcell_networks  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.initialization.build_tcell_abm_population  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.initialization.setup_ccl21_field  # noqa: F401

# --- Intracellular (per-cell MaBoSS) --------------------------------------
import opencellcomms_adapters.TCELL_CORRAL.functions.intracellular.activate_all_tcells  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.intracellular.sense_dc_contact  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.intracellular.step_tcell_network  # noqa: F401

# --- Intercellular (spatial / diffusion) ----------------------------------
import opencellcomms_adapters.TCELL_CORRAL.functions.intercellular.diffuse_ccl21  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.intercellular.chemotax_ccl21  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.intercellular.commit_tcell_fate  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.intercellular.differentiated_motility  # noqa: F401

# --- Reporting ------------------------------------------------------------
import opencellcomms_adapters.TCELL_CORRAL.functions.reporting.record_fate_counts  # noqa: F401
import opencellcomms_adapters.TCELL_CORRAL.functions.reporting.report_dc_progress  # noqa: F401
