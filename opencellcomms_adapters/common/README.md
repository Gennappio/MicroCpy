# common adapter — shared biology / ABM primitives

The OpenCellComms engine is **kernel + spatial + IO only** (substrate setup,
diffusion solvers, CSV/VTK export, checkpoints). Everything that creates or
evolves **cells, populations and gene networks** is biology and lives here, in a
single shared adapter that the experiment adapters depend on.

Dependency rule: experiment adapters (MicroC, jayatilake, PhysiBoSS) **may**
import from `common`; they must **not** import each other.

## Contents (`functions/`)

- **`gene_network/`** — gene-network creation, propagation, substance→input
  association, state inspection (the generic, parameterized machinery; NetLogo /
  hierarchical specializations stay in the experiment adapters).
- **`initialization/`** — `setup_population`, `generate_initial_cells`,
  `setup_gene_network`, `setup_associations`, `setup_maboss`,
  `initialize_gene_states`, `load_cells_from_csv`, `load_cells_from_vtk`.
- **`intracellular/`** — `update_metabolism`.
- **`intercellular/`** — `update_cell_division`, `update_cell_migration`,
  `remove_apoptotic_cells`, `track_population_changes`.
- **`orchestrators.py`** — legacy high-level workflow orchestrators lifted out of
  the engine's `standard_functions.py` (used only by legacy workflows).

These functions register automatically: the engine's `registry.py` imports
`opencellcomms_adapters.common.register`. Function resolution in workflows is by
name, so this relocation does not change any workflow JSON.
