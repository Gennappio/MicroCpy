# Chapter 5 — The Simulation Engine: Models, Algorithms, and Where the Science Lives

## 5.1 What “the engine” is responsible for

The Python engine is responsible for turning a workflow into a deterministic execution:

- loading workflow JSON and validating structure
- instantiating simulation objects (domain, population, substances, gene networks)
- running the step loop (macrosteps / iterations / subworkflow calls)
- invoking registered functions in the specified order
- writing outputs (data + plots + checkpoints)

The engine’s job is not to “own the science.” Instead it provides:

- a stable execution model,
- a set of core domain abstractions,
- and extension points where scientific logic can be implemented as workflow nodes.

## 5.2 Core domain objects (conceptual)

While exact class names vary, most multi-scale simulation engines revolve around:

- **Domain / geometry**
  - simulation bounds, discretization, coordinate systems
- **Population**
  - a set of cells with per-cell state
  - spatial positions
  - phenotypes/fates
- **Microenvironment**
  - one or more diffusing substances (oxygen, glucose, lactate, growth factors)
  - boundary conditions and sources/sinks
- **Intracellular state**
  - gene regulatory network state (Boolean / MaBoSS optional)
  - derived phenotypes or decision variables

In OpenCellComms, workflow nodes typically:

- read these objects from the shared context,
- update them in-place,
- and optionally emit outputs.

## 5.3 Multi-scale coupling pattern

The engine supports a common coupling pattern:

1. **Intracellular** updates (per-cell): metabolism, gene network step, phenotype changes
2. **Diffusion** update (environment): solve PDE for each substance for this step
3. **Intercellular** updates (population): migration, division, neighbor interactions
4. **Output** capture: snapshots/plots/checkpoints

This ordering can vary. The important point is that the workflow makes it explicit and repeatable.

## 5.4 Diffusion model (FiPy/PDE layer)

The diffusion subsystem is typically responsible for:

- representing concentration fields on a mesh/grid
- applying sources/sinks (consumption/production)
- solving PDEs over time

In OpenCellComms the docs explicitly cite FiPy usage as the diffusion backend (see top-level `README.md` and engine `README.md`).

For an article audience, you can describe it at the level of:

- “We solve diffusion on a discretized domain using FiPy”
- “Cells interact with the field by consuming/producing substances”

If desired, add a short math box (optional):

- diffusion equation with reaction term:
  - \( \partial_t c = D \nabla^2 c + R(c, \text{cells}) \)

## 5.5 Cell behaviors (ABM layer)

Cells are modeled as agents with local state. Common behaviors supported by node functions include:

- **division**: create a new cell; choose direction / placement; update population
- **migration**: move cells based on local rules (random walk, gradient following, crowding)
- **death/removal**: remove apoptotic or necrotic cells; update outputs
- **metabolism**: update per-cell consumption; change state based on local concentrations

The point of the workflow approach is that these are not hardcoded into a single “Cell.step()” method. They are modular nodes you can reorder, disable, replace, or parameterize.

## 5.6 Gene regulatory networks (Boolean / MaBoSS integration)

The engine supports intracellular decision logic via gene networks:

- boolean network models for cell fate decisions
- optional MaBoSS integration for stochastic simulation (mentioned as optional dependency)

In an article, it’s worth emphasizing:

- “Intracellular logic is decoupled from the environment solver but coupled through context and shared state.”
- “Gene network state can be recorded and exported alongside phenotypes and positions.”

## 5.7 Extending the engine scientifically: add new nodes, not forks

The best way to add new science is through workflow functions:

- implement a new function as a node
- register it so it appears in the GUI palette
- parameterize it so experiments can be run without code edits

This approach avoids “forking the engine” per project and instead encourages:

- a stable core runtime
- and an evolving library of scientific operators.

## 5.8 Performance considerations (honest section)

Multi-scale simulations can become expensive quickly. In this architecture, the hotspots are usually:

- diffusion solves (PDE) per step × substances × grid size
- per-cell updates × number of cells × complexity of intracellular logic
- output writing (especially frequent snapshots)
- observability snapshots/diffs if enabled at high frequency

The repo’s installation docs mention optional performance packages (e.g., numba/cython/joblib/dask). In an article, you can frame this as:

- “The default is research-friendly clarity; optimization is possible when needed.”

## 5.9 Suggested figures (for this chapter)

- **Figure 1 — Multi-scale coupling loop**
  - A single diagram showing Intracellular → Diffusion → Intercellular → Output per step.

- **Figure 2 — Example output from diffusion**
  - Use existing heatmaps:
    - `opencellcomms_gui/results/subworkflows/Generate_final_plots/heatmaps/*.png`

- **Figure 3 — Example cell population visualization**
  - Use existing tools outputs:
    - `opencellcomms_engine/tools/cell_visualizer_results/*.png`
    - or the interactive HTML: `opencellcomms_engine/tools/cell_visualizer_results/*interactive_3d.html`

