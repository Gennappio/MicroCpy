# Phenotype Marking and Cell Action Refactor

## Date
2026-02-15

## Summary
Refactored the cell phenotype marking workflow to separate marking from actions. This ensures that:
1. Gene network propagation only updates gene states (not phenotypes)
2. Marking functions set cell phenotypes based on gene states
3. Mark Proliferating Cells overwrites Growth Arrest and Apoptosis phenotypes
4. Action functions (division, removal) handle the actual cell state changes

## Changes Made

### 1. Modified Files

#### `propagate_gene_networks_netlogo.py` **[CRITICAL FIX]**
- **Before**: Updated both `gene_states` AND `phenotype` (automatic phenotype setting)
- **After**: Only updates `gene_states` (phenotype set by marking functions)
- **Why**: This was causing all cells to show as 'Quiescent' because the marking functions were conflicting with automatic phenotype setting

#### `mark_apoptotic_cells.py`
- **Before**: Marked AND removed apoptotic cells
- **After**: Only marks cells as 'Apoptosis' phenotype
- Function name changed from "Mark and Remove Apoptotic Cells" to "Mark Apoptotic Cells"
- Cells remain in population until `remove_apoptotic_cells` is called

#### `mark_proliferating_cells.py`
- **Before**: Skipped cells in Growth_Arrest and Apoptosis states
- **After**: Overwrites ALL previous phenotypes when Proliferation gene is ON
- **Important**: If Proliferation gene is OFF, phenotype is left UNCHANGED (preserves Apoptosis/Growth_Arrest)
- Implements hierarchical phenotype logic: Proliferation > Growth_Arrest/Apoptosis
- Logs when phenotypes are overwritten for debugging

#### `mark_growth_arrest_cells.py`
- **Before**: Only tracked cells already in Growth_Arrest state
- **After**: Marks cells as 'Growth_Arrest' based on gene network and tracks them
- Sets phenotype when Growth_Arrest gene is ON
- Maintains counter tracking functionality

### 2. New Files

#### `remove_apoptotic_cells.py`
- New function to remove cells marked with 'Apoptosis' phenotype
- Should be called AFTER `update_cell_division`
- Removes cells from population (programmed cell death with clearance)
- Logs removed cell IDs and population changes

### 3. Updated Files

#### `__init__.py`
- Added import and export for `remove_apoptotic_cells`

#### `v7_proliferation.json` (workflow)
- Updated execution order in 'loop' subworkflow:
  1. `update_gene_networks_netlogo` - Update gene states (NOT phenotypes)
  2. `mark_apoptotic_cells` - Mark cells for apoptosis
  3. `mark_growth_arrest_cells` - Mark cells in growth arrest
  4. `mark_proliferating_cells` - Mark proliferating cells (overwrites previous marks)
  5. `update_cell_division` - Handle cell division
  6. `remove_apoptotic_cells` - Remove marked apoptotic cells

## Phenotype Hierarchy

The new system implements a clear phenotype hierarchy:

```
Proliferation (highest priority - overwrites all)
    ↓
Growth_Arrest, Apoptosis (marked but can be overwritten by Proliferation)
    ↓
Quiescence (default state - no fate genes ON)
```

## Workflow Logic

1. **Gene Network Update**: Updates all gene states (gene_states dict), does NOT set phenotypes. Writes `_fate` back into `gene_states` so marking functions can read it.
2. **Mark Apoptosis** (first marker): **Resets ALL phenotypes to Quiescent** to clear stale state. Then sets phenotype='Apoptosis' if Apoptosis gene is ON.
3. **Mark Growth Arrest**: Sets phenotype='Growth_Arrest' if Growth_Arrest gene is ON (may overwrite Apoptosis).
4. **Mark Proliferation** (last marker): Sets phenotype='Proliferation' if Proliferation gene is ON (overwrites all); if OFF and cell is not Apoptosis/Growth_Arrest, ensures Quiescent.
5. **Update Division**: Divides cells with phenotype='Proliferation' that meet criteria.
6. **Remove Apoptosis**: Removes cells with phenotype='Apoptosis' from population.

**Key Point**: Phenotypes are determined **fresh each iteration** based on the current gene network state. No stale phenotypes carry over.

## Bug Fix (2026-02-15 17:00) — All cells Quiescent

### Issue
All cells were showing as 'Quiescent' (0% for all fate genes) in the visualization and logs.

### Root Cause
`propagate_gene_networks_netlogo` was setting `phenotype=final_fate` based on its internal NetLogo hierarchy logic, which used a "last overwrite wins" approach. This conflicted with the new manual marking functions, causing all phenotypes to be overwritten back to 'Quiescence'.

### Solution
Removed phenotype setting from `propagate_gene_networks_netlogo.py` (line 172-175). Now it ONLY updates `gene_states`, and the marking functions handle ALL phenotype logic.

## Bug Fix (2026-02-15) — Stale phenotypes persisting across iterations

### Issue
Cells that had their fate determined in iteration N kept the same phenotype in iteration N+1 even when the gene network no longer supported it.  This caused runaway proliferation (cells kept dividing every iteration once marked Proliferating) and/or runaway apoptosis.

### Root Cause
The marking functions only set phenotypes when their respective gene was ON but did **nothing** when it was OFF.  Since `CellState` is immutable-via-copy, the old phenotype carried over from the previous iteration.

### Solution
1. `mark_apoptotic_cells.py` (first in chain) now **resets ALL phenotypes to Quiescent** at the start of the marking cycle, clearing stale state.
2. `mark_proliferating_cells.py` (last in chain) has a secondary safety: cells whose Proliferation gene is OFF and whose phenotype is not in `{Apoptosis, Growth_Arrest}` are explicitly set to Quiescent.

## Bug Fix (2026-02-15) — Daughter cells inheriting parent fate (runaway proliferation)

### Issue
After fixing the stale-phenotype bug, the population in the workflow (~929 cells after 7 iterations) was still far higher than the benchmark (~605 cells). Apoptosis in the benchmark overwhelmed proliferation, but the workflow had too many surviving/dividing cells.

### Root Cause
When a cell divided, `update_cell_division.py` created the daughter's gene network using `parent_gn.copy()`. This gave the daughter the **parent's entire state**: `_fate`, gene node values, `_cell_ran1`/`_cell_ran2`, etc. In the benchmark (`gene_network_population_simulator.py`), daughter cells are created with `reset(random_init=True)` + `set_input_states()`, meaning they start **fresh** with `fate=None`, random gene states, and new random thresholds.

The consequence: daughters inherited `_fate == "Proliferation"` and would immediately proliferate again at the next check, creating exponential growth instead of the benchmark's slow-growing/declining population.

### Solution
1. **`update_cell_division.py`**: Replaced `parent_gn.copy()` with `_create_fresh_daughter_network(context)` — a new helper that creates a daughter gene network from scratch, exactly matching the benchmark's reset behaviour.
2. **`initialize_netlogo_gene_networks.py`**: Now stores `MCT1I_concentration` and `GLUT1I_concentration` in `context['gene_network_init_params']` so the division function can reuse them when initializing daughters.
3. Daughter cells now start with `phenotype='Quiescent'` and `fate=None` instead of inheriting the parent's phenotype.

## NetLogo Alignment Fixes (2026-02-15)

### Fix: Reversible mode OFF (matching NetLogo default)
- **`v7_proliferation.json`**: Changed `"reversible": true` → `"reversible": false`
- In NetLogo, `the-reversible?` defaults to 0 (false), meaning any fate stops
  gene network updates. Only cells with `my-fate = nobody` continue walking.

### Fix: Parent cell reset after division (matching NetLogo's -RESET-FATE-145)
- **`update_cell_division.py`**: After successful division, the parent cell now:
  - Sets `phenotype = 'Quiescent'` (was keeping 'Proliferation')
  - Sets `_fate = None` on gene network (was keeping previous fate)
  - Re-randomises `_cell_ran1` and `_cell_ran2` (new Hill function thresholds)
  - Resets `age = 0`

### Fix: No-space → Growth_Arrest (matching NetLogo's -TURN-QUIESCENCE-3)
- **`update_cell_division.py`**: When no empty neighbour is found:
  - Sets `phenotype = 'Growth_Arrest'`
  - Sets `_fate = "Growth_Arrest"` on gene network
  - Initialises growth-arrest cycle counter = 3
  - (In NetLogo, these cells exit arrest after 3 intercellular steps)

## Benefits

1. **Clear Separation of Concerns**: Gene network propagation vs Phenotype marking vs Actions
2. **Hierarchical Phenotypes**: Proliferation can override death/arrest signals
3. **Better Debugging**: Each step is logged independently
4. **Extensibility**: Easy to add new phenotypes or actions
5. **Testability**: Each function can be tested independently
6. **Manual Control**: Phenotypes are set explicitly by marking functions, not automatically

## Testing Notes

- Run workflow with: `python opencellcomms_engine/run_workflow.py --workflow opencellcomms_engine/tests/jayatilake_experiment/v7_proliferation.json`
- Watch for log messages showing phenotype overwrites
- Verify that proliferating cells can override apoptosis/growth arrest signals
- Check population counts at each step
- Verify that fate gene percentages are non-zero in logs

## Files Modified

- `opencellcomms_engine/src/workflow/functions/gene_network/propagate_gene_networks_netlogo.py` **[KEY FIX]**
- `opencellcomms_engine/src/workflow/functions/intercellular/mark_apoptotic_cells.py`
- `opencellcomms_engine/src/workflow/functions/intercellular/mark_proliferating_cells.py`
- `opencellcomms_engine/src/workflow/functions/intercellular/mark_growth_arrest_cells.py`
- `opencellcomms_engine/src/workflow/functions/intercellular/__init__.py`
- `opencellcomms_engine/tests/jayatilake_experiment/v7_proliferation.json`

## Files Created

- `opencellcomms_engine/src/workflow/functions/intercellular/remove_apoptotic_cells.py`
- `opencellcomms_engine/docs/phenotype_marking_refactor.md` (this file)
