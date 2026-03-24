# Microenvironment Step — Implementation Reference

## Overview

The microenvironment step solves a diffusion-reaction PDE for every substance
(Oxygen, Glucose, Lactate, …) in the domain. The spatial distribution of
concentrations is the physical link between cell behaviour and the field — cells
consume/produce substances, the field evolves, and updated concentrations feed
back into gene networks and metabolism.

Three workflow functions implement the step, from simple to physically rigorous:

| Function node | File | When to use |
|---|---|---|
| **Run Diffusion Solver** | `run_diffusion_solver.py` | Pure diffusion, or when metabolism is pre-computed and stable |
| **Run Diffusion Solver (Clamped)** | `run_diffusion_solver_clamped.py` | Same as above, adds a post-solve floor on concentrations |
| **Run Diffusion Solver (Coupled)** | `run_diffusion_solver_coupled.py` | Tight metabolism–diffusion coupling via Picard iteration — recommended for realistic metabolic simulations |

All three read from and write to `context['simulator']`. None of them modify
the workflow graph, the gene network, or the population structure; they only
update substance concentration arrays inside the simulator's state.

---

## The PDE and Its Discretisation

### Equation

For each substance $s$ the steady-state diffusion-reaction problem is:

$$\nabla \cdot (D_s \nabla c_s) = -R_s(\mathbf{x})$$

where:
- $c_s$ — concentration field (mM), the unknown
- $D_s$ — diffusion coefficient (m²/s), constant, substance-specific
- $R_s(\mathbf{x})$ — volumetric reaction term (mM/s), positive = production,
  negative = consumption

Boundary conditions are per-substance and can be:
- **fixed** — constant Dirichlet value on all faces (e.g. `O₂ = 0.2 mM` at
  boundary)
- **linear\_gradient** — 0 on the left face, 1 on the right face, interpolated
  on top/bottom
- **gradient** — fully custom face-by-face values

### Solver backend — FiPy

The PDE is discretised using
[FiPy](https://www.ctcms.nist.gov/fipy/) on the domain's structured grid
(`Grid2D` or `Grid3D`). For each substance `s`:

```python
source_var = CellVariable(mesh=fipy_mesh, value=source_field)   # R_s
equation   = DiffusionTerm(coeff=D_s) == -source_var            # ∇·(D∇c) = -R
equation.solve(var=c_var, solver=LinearGMRESSolver(...))
```

The sign flip (`-source_var`) is because FiPy writes the equation as
`∇·(D∇c) + S = 0`, so passing `-R` gives `∇·(D∇c) - R = 0`, i.e. `∇·(D∇c) = R`.

After solving, the result is stored back into `substance_state.concentrations`
and into the FiPy `CellVariable` (so the next solve uses the current solution as
its initial guess, which accelerates convergence):

```python
substance_state.concentrations = np.array(var.value).reshape((ny, nx), order='F')
simulator.fipy_variables[name].setValue(substance_state.concentrations.flatten(order='F'))
```

### Unit conversion — from mol/s/cell to mM/s

Cell reactions are expressed in **mol/s per cell**. FiPy expects a **volumetric
rate in mM/s**. The conversion inside `_create_source_field_from_reactions` is:

```
volumetric_rate [mol/(m³·s)] = reaction_rate [mol/s] / mesh_cell_volume [m³ or m²]
                              × twodimensional_adjustment_coefficient

final_rate [mM/s] = volumetric_rate × 1000
```

For **2-D domains** `mesh_cell_volume = dx × dy` (area only — no z thickness).
The `twodimensional_adjustment_coefficient` in `config.diffusion` compensates for
the missing z dimension; set it to `1 / cell_height_m` to recover the correct
volumetric rate.

For **3-D domains** `mesh_cell_volume = dx × dy × dz`.

### Position mapping — biological grid → FiPy index

Cell positions are stored in biological grid units (integer voxel indices). The
source field mapping converts them to the FiPy flattened index:

```
scale_x = nx_fipy / nx_bio          # e.g. 50/75 = 0.667
x_fipy  = int(x_bio * scale_x)

# 2D: fipy_idx = x_fipy * ny + y_fipy
# 3D: fipy_idx = x_fipy * ny * nz + y_fipy * nz + z_fipy
```

A heuristic detects whether positions are in biological grid units, micrometres,
or metres, and converts accordingly.

---

## Solver Variants

### 1. Run Diffusion Solver (`run_diffusion_solver`)

The base solver. Executes in three phases:

**Phase 1 — configure substances (first call only)**
If `context['substances']` or `kwargs` carries substance definitions that are not
yet in `config.substances`, they are registered and
`simulator.initialize_substances()` is called to create the FiPy `CellVariable`
objects. After the first call this phase is skipped.

**Phase 2 — collect reaction terms**
If a population is present, each cell's pre-computed `metabolic_state` is read:

```python
reactions['Oxygen']  = -metabolic_state['oxygen_consumption']   # mol/s
reactions['Glucose'] = -metabolic_state['glucose_consumption']
reactions['Lactate'] = metabolic_state['lactate_production'] - metabolic_state['lactate_consumption']
```

Dynamic keys (`{Substance}_consumption`, `{Substance}_production`) are also
detected for user-defined substances. Reactions from cells sharing a voxel are
summed.

**Phase 3 — solve**
`simulator.update(position_reactions)` is called. Inside `MultiSubstanceSimulator.update`
the source field is assembled and FiPy solves the equation for each substance
independently. The previous solution is used as the initial guess.

**Parameters**

| Parameter | Default | Description |
|---|---|---|
| `max_iterations` | 1000 | FiPy GMRES maximum iterations |
| `tolerance` | 1e-6 | FiPy residual tolerance |
| `solver_type` | `steady_state` | `steady_state` or `transient` |

---

### 2. Run Diffusion Solver (Clamped) (`run_diffusion_solver_clamped`)

Identical to the base solver, with one post-processing step: after
`simulator.update()` returns, every cell in every substance concentration field
that is below `min_concentration` is set to `min_concentration`:

```python
substance_state.concentrations = np.maximum(concentrations, min_concentration)
simulator.fipy_variables[name].setValue(...)   # sync FiPy variable
```

The function reports how many cells were clamped and the total mass correction.

Use this as a lightweight safeguard when you know consumption can locally exceed
supply but you want to avoid the overhead of full iterative coupling.
As noted in the file docstring: *"clamping is a numerical safeguard, not a
physics fix."* The coupled solver below is the correct physical approach.

**Additional parameter**

| Parameter | Default | Description |
|---|---|---|
| `min_concentration` | 0.0 | Floor applied after solve |

---

### 3. Run Diffusion Solver (Coupled) — Picard Iteration

This is the physically rigorous solver. It iterates between metabolism
recalculation and diffusion solving until the concentration field converges.

---

## Picard Iteration — Detailed Description

### Why iteration is necessary

Cell oxygen consumption follows Michaelis-Menten kinetics:

$$R_\text{O_2}^\text{cell} = V_\text{max} \cdot \frac{c_\text{O_2}}{K_m + c_\text{O_2}}$$

The consumption rate depends on the local concentration, but the concentration
depends on the consumption rate. This circular dependency creates a nonlinear
coupled system. If metabolism is computed only once with the concentrations from
the *previous* macrostep, the solver can produce regions where predicted
consumption exceeds the physically available oxygen — leading to negative
concentrations.

The Picard iteration resolves this by re-evaluating the nonlinear term after each
solve and repeating until the solution is self-consistent.

### Algorithm

The outer loop in `run_diffusion_solver_coupled` (simplified):

```
old_reactions ← None

for k in range(max_coupling_iterations):

    C_old ← snapshot(simulator)           # current concentrations

    recalculate_metabolism(C_old)          # update cell.metabolic_state using C_old
    R_new ← collect_reactions(population) # read updated metabolic_state

    if old_reactions is not None and α < 1.0:
        R_blended ← α · R_new + (1 - α) · R_old    # under-relax source terms
    else:
        R_blended ← R_new

    old_reactions ← R_new                 # store unblended for next iteration

    simulator.update(R_blended)            # FiPy solve: ∇·(D∇c) = -R_blended
    clamp_negatives()                      # safety floor

    C_new ← snapshot(simulator)
    Δ ← max |C_new - C_old|               # convergence metric

    if Δ < coupling_tolerance:
        break                              # converged

    if α < 1.0:
        C_next ← α · C_new + (1 - α) · C_old   # under-relax concentrations too
        write C_next to simulator

clamp_negatives()                          # final safety pass
```

### Step-by-step breakdown

**Step 1 — snapshot old concentrations**

```python
old_concentrations = _get_concentration_snapshot(simulator)
# { 'Oxygen': np.ndarray(ny, nx), 'Glucose': ..., ... }
```

**Step 2 — recalculate metabolism** (`_recalculate_metabolism`)

For each active cell (not Necrosis / Growth\_Arrest):

1. Look up local concentrations at the cell's grid position.
2. Compute Michaelis-Menten terms:
   ```python
   O2_mm  = c_O2  / (Km_O2  + c_O2)
   Glu_mm = c_Glu / (Km_Glu + c_Glu)
   Lac_mm = c_Lac / (Km_Lac + c_Lac)
   ```
3. Compute consumption/production from gene states (`mitoATP`, `glycoATP`):

   | Gene active | Pathway | O₂ consumed | Glucose consumed | Lactate |
   |---|---|---|---|---|
   | `mitoATP` | OXPHOS | `Vmax × α_O2 × O2_mm` | `(Vmax/6) × Glu_mm × O2_mm` | consumed: `(2Vmax/6) × Lac_mm × O2_mm` |
   | `glycoATP` | Glycolysis | `Vmax × 0.5 × O2_mm` | `(Vmax/6) × (ATP_max/2) × Glu_mm` | produced: `3 × Glu_consumed` |

4. Apply conversion factors (`oxygen_conversion_factor`, etc.).
5. Write back to `cell.state.metabolic_state` and update `population.state.cells`.

**Step 3 — collect reaction terms** (`_collect_reactions_from_cells`)

Iterate all cells, read `metabolic_state`, accumulate into
`{ position: { 'Oxygen': rate_mol_s, 'Glucose': …, 'Lactate': … } }`.
Multiple cells at the same voxel are summed.

**Step 4 — blend reaction terms** (`_blend_reactions`)

Applied when `old_reactions` is available and `relaxation_factor < 1.0`:

```python
R_blended[pos][sub] = α * R_new[pos][sub] + (1 - α) * R_old[pos][sub]
```

Positions present in `R_new` but not in `R_old` (newly appeared cells) take
`R_new` directly. Positions present only in `R_old` (removed cells) are dropped.

**Step 5 — solve** (`simulator.update(R_blended)`)

FiPy solves `∇·(D∇c) = -R_blended` for each substance. The GMRES solver uses
the current `CellVariable` value as its initial guess, so later iterations (which
start from a good guess) converge faster.

**Step 5b — safety clamp** (`_clamp_negative_concentrations`)

Before checking convergence, any remaining negative values are set to zero and
the FiPy variable is updated to match. This prevents numerical garbage from
propagating into the next iteration's Michaelis-Menten lookups.

**Step 6 — convergence check** (`_compute_max_change`)

```python
Δ = max over all substances of max |C_new - C_old|
if Δ < coupling_tolerance: break
```

**Step 7 — concentration under-relaxation** (`_apply_relaxation`)

If not yet converged, the concentration field itself is also blended:

```python
C_next = α * max(C_new, 0) + (1 - α) * max(C_old, 0)
C_next = max(C_next, 0)     # clamp again
```

Both operands are clamped before blending to prevent negative values from
dominating the mixture. This is described in the code as *"belt and
suspenders"* — under-relaxation is applied to both the source terms (step 4)
and the concentrations (step 7), providing two independent damping mechanisms.

### Under-relaxation — why it matters

Without under-relaxation (`α = 1`), a high-consumption region can oscillate:
- Iteration k: high consumption → very low C → very low consumption next
- Iteration k+1: low consumption → high C → high consumption again

Under-relaxation (`α = 0.7`) smooths this by mixing the new reaction estimate
with the old one, so the source term changes gradually between iterations.

The default `α = 0.7` is a conservative choice that trades speed for stability.
For well-behaved setups `α = 0.9` converges faster; for pathological cases
(very sparse populations, extreme gradients) `α = 0.5` may be needed.

### Convergence and maximum iterations

The loop exits when `Δ < coupling_tolerance` (default 1e-4 mM). If the loop
reaches `max_coupling_iterations` without converging, a warning is printed:

```
[COUPLED] WARNING: Did not converge after 10 iterations (final max_change=X.XXe-XX)
```

The simulation continues regardless. A final `_clamp_negative_concentrations`
pass is always applied after the loop.

### Parameters summary

| Parameter | Default | Role |
|---|---|---|
| `max_iterations` | 1000 | FiPy GMRES iterations per solve (inner loop) |
| `tolerance` | 1e-6 | FiPy residual tolerance (inner loop) |
| `solver_type` | `steady_state` | FiPy equation type |
| `max_coupling_iterations` | 10 | Picard outer loop limit |
| `coupling_tolerance` | 1e-4 | Convergence criterion: max concentration change (mM) |
| `relaxation_factor` α | 0.7 | Under-relaxation on both source terms and concentrations |
| `oxygen_conversion_factor` | 1.0 | Scale O₂ consumption after Michaelis-Menten |
| `glucose_conversion_factor` | 1.0 | Scale glucose consumption |
| `lactate_conversion_factor` | 1.0 | Scale lactate production |
| `oxygen_consumption_multiplier` | 1.0 | Extra scale on mitoATP O₂ term (replaces a hardcoded ×50) |

---

## Data Flow Through the Microenvironment Step

```
context['population']
  └─ cell.state.gene_states (mitoATP, glycoATP)
  └─ cell.state.position

context['simulator']
  └─ simulator.state.substances
       └─ SubstanceState.concentrations   ←──────────────────────────┐
       └─ simulator.fipy_variables                                    │
                                                                      │
Step 1:  _recalculate_metabolism                                      │
         reads concentrations → computes Michaelis-Menten             │
         writes cell.state.metabolic_state                            │
                                                                      │
Step 2:  _collect_reactions_from_cells                                │
         reads metabolic_state → builds position_reactions (mol/s)   │
                                                                      │
Step 3:  _blend_reactions (if α < 1)                                  │
         R_blended = α·R_new + (1-α)·R_old                           │
                                                                      │
Step 4:  simulator.update(R_blended)                                  │
         _create_source_field  mol/s → mM/s (unit conversion)        │
         FiPy solve: ∇·(D∇c) = -R                                    │
         substance_state.concentrations ← new field ───────────────────┘
         fipy_variables updated (warm start for next iteration)

Step 5:  _clamp_negative_concentrations  (safety)
Step 6:  convergence check  max|ΔC| < tol?
Step 7:  _apply_relaxation on concentrations (if not converged)

repeat from Step 1
```

---

## Relationship to `update_metabolism`

There are two places where metabolism is computed:

1. **`update_metabolism`** (intracellular stage) — runs once per macrostep,
   updates `cell.state.metabolic_state` from the concentrations at the *start*
   of the macrostep. Used by the base and clamped solvers, which do not iterate.

2. **`_recalculate_metabolism` inside `run_diffusion_solver_coupled`** — runs
   once per Picard iteration, using the *current* (just-solved) concentrations.
   When using the coupled solver, `update_metabolism` in the intracellular stage
   provides the initial metabolic estimate; the coupled solver then refines it
   iteratively until self-consistent.

If `update_metabolism` has not been called before `run_diffusion_solver_coupled`,
the cells' `metabolic_state` will be empty and the first Picard iteration will
see zero reactions (which is harmless — the solver will then compute the correct
rates from the initial concentrations and subsequent iterations will converge
normally).

---

## Which Solver to Choose

| Scenario | Recommended solver |
|---|---|
| No cells, pure substance diffusion | `run_diffusion_solver` |
| Cells present, slow metabolism relative to diffusion, no risk of negatives | `run_diffusion_solver` |
| Cells present, occasional negative values appearing | `run_diffusion_solver_clamped` |
| Cells present, Michaelis-Menten kinetics, realistic metabolism | `run_diffusion_solver_coupled` |
| Debug / fast prototyping | `run_diffusion_solver` |

---

## Source files

```
src/
  simulation/
    multi_substance_simulator.py   — MultiSubstanceSimulator, FiPy wrapper,
                                     unit conversion, position mapping
  workflow/functions/diffusion/
    run_diffusion_solver.py        — base solver workflow function
    run_diffusion_solver_clamped.py — base + clamping post-process
    run_diffusion_solver_coupled.py — Picard iteration + under-relaxation
```
